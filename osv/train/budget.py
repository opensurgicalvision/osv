"""GPU accounting and the wall-clock cap for sandbox training runs (R-24).

Two halves of the same rule, and neither works without the other:

* `log_gpu_count` records how many GPUs a run actually held. Without it
  `scripts/check_compute_quota.py` has to assume one GPU per run, which under-charges
  every multi-GPU experiment - the ones that burn the grant fastest.
* `WallClockBudget` turns the remaining budget into a limit the run obeys. The quota
  gate is pre-flight only: with half an hour left, nothing stops a twenty-hour run from
  starting and overshooting the week. Being stopped by the budget is a normal outcome
  that ends in a checkpoint and a PAUSED_QUOTA marker, not a failure.

torch is imported lazily so the budget can be used - and tested - on a machine with no
CUDA and no torch at all.
"""

from __future__ import annotations

import os
import time

GPU_COUNT_PARAM = "gpu_count"
REMAINING_ENV = "OSV_GPU_HOURS_REMAINING"

# Stop this far before the cap so the checkpoint that makes the run resumable is
# actually written. A budget that ends mid-write turns a planned pause into lost work,
# which is the exact failure the pause exists to prevent.
DEFAULT_RESERVE_MINUTES = 10.0


def detect_gpu_count() -> int:
    """How many GPUs this process holds.

    Distributed launchers set WORLD_SIZE, which is the truth for a multi-process run;
    a single process sees its own visible devices. A CPU-only run reports 0 and is
    charged the quota's one-GPU floor, which is deliberately conservative: the quota
    should never under-charge on a guess.
    """
    world_size = os.environ.get("WORLD_SIZE")
    if world_size:
        try:
            value = int(world_size)
        except ValueError:
            value = 0
        if value > 0:
            return value

    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is not None:
        devices = [item for item in visible.split(",") if item.strip() not in ("", "-1")]
        return len(devices)

    try:
        import torch
    except ImportError:
        return 0
    if not torch.cuda.is_available():
        return 0
    return int(torch.cuda.device_count())


def log_gpu_count(mlflow_module=None, gpu_count: int | None = None) -> int:
    """Record the GPU count on the active run so the quota can charge GPU-hours."""
    count = detect_gpu_count() if gpu_count is None else gpu_count
    if mlflow_module is None:
        try:
            import mlflow as mlflow_module  # type: ignore[no-redef]
        except ImportError:
            return count
    mlflow_module.log_param(GPU_COUNT_PARAM, count)
    return count


class BudgetExhausted(Exception):
    """Raised when a run is stopped by its wall-clock cap. A normal outcome, not a bug."""


class WallClockBudget:
    """The remaining weekly budget, expressed as a limit on this run.

    Usage in a training loop:

        budget = WallClockBudget.from_env()
        for epoch in range(epochs):
            train_one_epoch(...)
            if budget.should_stop():
                save_checkpoint(...)
                break
    """

    def __init__(
        self,
        max_hours: float | None,
        reserve_minutes: float = DEFAULT_RESERVE_MINUTES,
        clock=time.monotonic,
    ):
        self.max_hours = max_hours
        self.reserve_minutes = max(reserve_minutes, 0.0)
        self._clock = clock
        self._started = clock()

    @classmethod
    def from_env(cls, reserve_minutes: float = DEFAULT_RESERVE_MINUTES, clock=time.monotonic):
        """Read the cap the quota gate published as OSV_GPU_HOURS_REMAINING.

        An unset or unparsable value means uncapped. That is on purpose: this class is a
        limiter, not the gate. Refusing to start belongs to check_compute_quota.py, and
        duplicating that decision here would make a missing variable look like an
        exhausted budget on every developer laptop.
        """
        raw = os.environ.get(REMAINING_ENV, "").strip()
        try:
            max_hours = float(raw) if raw else None
        except ValueError:
            max_hours = None
        return cls(max_hours, reserve_minutes=reserve_minutes, clock=clock)

    @property
    def uncapped(self) -> bool:
        return self.max_hours is None

    def elapsed_hours(self) -> float:
        return (self._clock() - self._started) / 3600.0

    def remaining_hours(self) -> float | None:
        if self.max_hours is None:
            return None
        return self.max_hours - self.elapsed_hours()

    def should_stop(self) -> bool:
        """True once the run is close enough to the cap that it must checkpoint now."""
        remaining = self.remaining_hours()
        if remaining is None:
            return False
        return remaining <= self.reserve_minutes / 60.0

    def check(self) -> None:
        """Raise BudgetExhausted if the cap is reached. For loops that unwind by exception."""
        if self.should_stop():
            spent = self.elapsed_hours()
            raise BudgetExhausted(
                f"wall-clock cap reached: {spent:.2f} h of {self.max_hours:.2f} h "
                f"(reserving {self.reserve_minutes:.0f} min to checkpoint). "
                "Save state and stop; the series resumes next cycle (R-24)."
            )
