"""Test the wall-clock cap and GPU accounting that make R-24 enforceable.

The quota gate is pre-flight: it decides whether a run may start, not how long it may
last. These two pieces close that gap - the cap the run obeys, and the GPU count the
quota charges by - so a single long run cannot overshoot the week the gate just
measured.
"""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from osv.train.budget import (  # noqa: E402
    BudgetExhausted,
    WallClockBudget,
    detect_gpu_count,
    log_gpu_count,
)


class FakeClock:
    """A monotonic clock the test drives by hand, in seconds."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance_hours(self, hours):
        self.now += hours * 3600.0


class FakeMlflow:
    def __init__(self):
        self.params = {}

    def log_param(self, key, value):
        self.params[key] = value


# --- the GPU count the quota charges by ------------------------------------


def test_world_size_wins_for_a_distributed_run(monkeypatch):
    monkeypatch.setenv("WORLD_SIZE", "4")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    assert detect_gpu_count() == 4


def test_visible_devices_are_counted_for_a_single_process(monkeypatch):
    monkeypatch.delenv("WORLD_SIZE", raising=False)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1,2")
    assert detect_gpu_count() == 3


def test_cpu_only_run_reports_zero(monkeypatch):
    # Charged the quota's one-GPU floor: under-charging on a guess is the one direction
    # a budget must never err in.
    monkeypatch.delenv("WORLD_SIZE", raising=False)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    assert detect_gpu_count() == 0


def test_disabled_device_marker_is_not_a_gpu(monkeypatch):
    monkeypatch.delenv("WORLD_SIZE", raising=False)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    assert detect_gpu_count() == 0


def test_unparsable_world_size_falls_through(monkeypatch):
    monkeypatch.setenv("WORLD_SIZE", "many")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    assert detect_gpu_count() == 2


def test_gpu_count_is_logged_as_a_run_param(monkeypatch):
    # This is the param check_compute_quota.py multiplies hours by.
    monkeypatch.setenv("WORLD_SIZE", "8")
    tracker = FakeMlflow()
    assert log_gpu_count(mlflow_module=tracker) == 8
    assert tracker.params == {"gpu_count": 8}


def test_explicit_gpu_count_overrides_detection(monkeypatch):
    monkeypatch.setenv("WORLD_SIZE", "8")
    tracker = FakeMlflow()
    assert log_gpu_count(mlflow_module=tracker, gpu_count=2) == 2
    assert tracker.params == {"gpu_count": 2}


# --- the cap ---------------------------------------------------------------


def test_budget_does_not_stop_before_the_cap():
    clock = FakeClock()
    budget = WallClockBudget(max_hours=4.0, reserve_minutes=10.0, clock=clock)
    clock.advance_hours(3.0)
    assert budget.should_stop() is False
    assert budget.remaining_hours() == pytest.approx(1.0)


def test_budget_stops_early_enough_to_checkpoint():
    # Stopping exactly at the cap would cut the checkpoint write in half, which turns a
    # planned pause into the lost work it exists to prevent.
    clock = FakeClock()
    budget = WallClockBudget(max_hours=4.0, reserve_minutes=10.0, clock=clock)
    clock.advance_hours(3.9)
    assert budget.should_stop() is True


def test_check_raises_once_the_budget_is_gone():
    clock = FakeClock()
    budget = WallClockBudget(max_hours=1.0, reserve_minutes=0.0, clock=clock)
    clock.advance_hours(1.0)
    with pytest.raises(BudgetExhausted) as exc:
        budget.check()
    assert "R-24" in str(exc.value)


def test_zero_reserve_uses_the_whole_cap():
    clock = FakeClock()
    budget = WallClockBudget(max_hours=2.0, reserve_minutes=0.0, clock=clock)
    clock.advance_hours(1.99)
    assert budget.should_stop() is False


# --- the hand-off from the quota gate --------------------------------------


def test_from_env_reads_the_dotenv_the_gate_publishes(monkeypatch):
    monkeypatch.setenv("OSV_GPU_HOURS_REMAINING", "1.5")
    budget = WallClockBudget.from_env(clock=FakeClock())
    assert budget.max_hours == pytest.approx(1.5)
    assert budget.uncapped is False


def test_missing_remaining_budget_means_uncapped_not_exhausted(monkeypatch):
    # A limiter, not a gate: refusing to start belongs to check_compute_quota.py, and
    # duplicating it here would make an unset variable look like a spent budget on
    # every developer laptop.
    monkeypatch.delenv("OSV_GPU_HOURS_REMAINING", raising=False)
    budget = WallClockBudget.from_env(clock=FakeClock())
    assert budget.uncapped is True
    assert budget.should_stop() is False
    assert budget.remaining_hours() is None


def test_unparsable_remaining_budget_is_uncapped(monkeypatch):
    monkeypatch.setenv("OSV_GPU_HOURS_REMAINING", "")
    assert WallClockBudget.from_env(clock=FakeClock()).uncapped is True
    monkeypatch.setenv("OSV_GPU_HOURS_REMAINING", "soon")
    assert WallClockBudget.from_env(clock=FakeClock()).uncapped is True


def test_uncapped_budget_never_stops_a_run():
    clock = FakeClock()
    budget = WallClockBudget(max_hours=None, clock=clock)
    clock.advance_hours(100.0)
    assert budget.should_stop() is False
    budget.check()
