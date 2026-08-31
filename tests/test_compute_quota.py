"""Test the weekly GPU-hour quota gate (R-24).

Same shape as test_demo_guard.py, and the same reason: a spend guard is only
mechanical if it errs towards refusing. Every test below the arithmetic section
pins one way the first version handed out unlimited GPU without anyone noticing -
a missing experiment read as zero usage, soft-deleted runs vanishing from the
sum, a truncated first page, wall-clock counted as GPU-hours.

No mlflow here: the module imports it lazily and main() takes a client factory,
so the whole gate is exercised against a stub.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

import check_compute_quota as quota  # noqa: E402

VIEW_ALL = "VIEW_TYPE_ALL"
MONDAY = datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc)


def ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def make_run(run_id, start, end=None, parent=None, params=None, tags=None):
    tags = dict(tags or {})
    if parent:
        tags["mlflow.parentRunId"] = parent
    return SimpleNamespace(
        info=SimpleNamespace(
            run_id=run_id, start_time=ms(start), end_time=ms(end) if end else None
        ),
        data=SimpleNamespace(params=dict(params or {}), tags=tags),
    )


class Page(list):
    """A search_runs result page: a list that may carry a continuation token."""

    def __init__(self, runs, token=None):
        super().__init__(runs)
        self.token = token


class FakeClient:
    def __init__(self, pages=None, experiment_id="1"):
        self.pages = pages if pages is not None else [Page([])]
        self.experiment_id = experiment_id
        self.calls = []

    def get_experiment_by_name(self, name):
        if self.experiment_id is None:
            return None
        return SimpleNamespace(experiment_id=self.experiment_id, name=name)

    def search_runs(self, experiment_ids, filter_string, run_view_type, max_results, page_token):
        self.calls.append(
            {
                "experiment_ids": experiment_ids,
                "filter_string": filter_string,
                "run_view_type": run_view_type,
                "max_results": max_results,
                "page_token": page_token,
            }
        )
        index = 0 if page_token is None else int(page_token)
        return self.pages[index]


def factory_for(client):
    return lambda: (client, VIEW_ALL)


def run_main(argv, client, monkeypatch, tracking_uri="http://mlflow.osv.internal"):
    if tracking_uri is None:
        monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    else:
        monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)
    monkeypatch.delenv("OSV_GPU_QUOTA_HOURS", raising=False)
    return quota.main(argv, client_factory=factory_for(client))


def freeze_now(monkeypatch, moment):
    """Pin the clock `main()` reads.

    `used_gpu_hours` deliberately clamps a run's end to now, so an unclosed
    crash-loop cannot over-charge the week. That makes any main()-level test
    that asserts on a *quantity* of GPU-hours depend on how far into the real
    week the suite happens to run: on a Monday morning a 50-hour run counts as
    only the hours elapsed since Monday 00:00 and never trips a 40-hour quota.
    Freezing the clock is what makes those assertions about the code instead of
    about the calendar.
    """

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(quota, "datetime", _FrozenDatetime)


# --- the week window -------------------------------------------------------


def test_week_starts_on_monday_utc():
    wednesday = datetime(2026, 8, 26, 15, 30, tzinfo=timezone.utc)
    assert quota.get_week_start_time(wednesday) == MONDAY


def test_monday_itself_is_the_start_of_its_own_week():
    monday_noon = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    assert quota.get_week_start_time(monday_noon) == MONDAY


# --- what counts as spent --------------------------------------------------


def test_finished_run_counts_its_duration():
    runs = [make_run("a", MONDAY + timedelta(hours=1), MONDAY + timedelta(hours=4))]
    hours, _ = quota.used_gpu_hours(runs, MONDAY, MONDAY + timedelta(hours=10))
    assert hours == pytest.approx(3.0)


def test_active_run_counts_up_to_now():
    # A crash loop that never closes its runs must not be a way to spend for free.
    runs = [make_run("a", MONDAY + timedelta(hours=1))]
    hours, _ = quota.used_gpu_hours(runs, MONDAY, MONDAY + timedelta(hours=6))
    assert hours == pytest.approx(5.0)


def test_run_crossing_the_week_boundary_counts_only_this_weeks_share():
    # Started Sunday 22:00, still going at Monday 03:00 -> 3 hours belong to this week.
    runs = [make_run("a", MONDAY - timedelta(hours=2))]
    hours, _ = quota.used_gpu_hours(runs, MONDAY, MONDAY + timedelta(hours=3))
    assert hours == pytest.approx(3.0)


def test_run_finished_before_the_week_started_counts_zero():
    runs = [make_run("a", MONDAY - timedelta(hours=5), MONDAY - timedelta(hours=1))]
    hours, _ = quota.used_gpu_hours(runs, MONDAY, MONDAY + timedelta(hours=3))
    assert hours == pytest.approx(0.0)


def test_gpu_count_multiplies_the_hours():
    # Grants are denominated in GPU-hours: four GPUs for two hours is eight.
    runs = [
        make_run(
            "a", MONDAY, MONDAY + timedelta(hours=2), params={"gpu_count": "4"}
        )
    ]
    hours, untagged = quota.used_gpu_hours(runs, MONDAY, MONDAY + timedelta(hours=3))
    assert hours == pytest.approx(8.0)
    assert untagged == []


def test_run_without_a_gpu_count_is_charged_one_gpu_and_reported():
    runs = [make_run("a", MONDAY, MONDAY + timedelta(hours=2))]
    hours, untagged = quota.used_gpu_hours(runs, MONDAY, MONDAY + timedelta(hours=3))
    assert hours == pytest.approx(2.0)
    assert untagged == ["a"]


def test_parent_run_is_not_counted_on_top_of_its_seeds():
    # arch-runner nests one child per seed under a parent per hypothesis; the parent's
    # span covers all of them, so summing both charges every hour twice.
    parent = make_run("parent", MONDAY, MONDAY + timedelta(hours=6))
    seeds = [
        make_run("seed-1", MONDAY, MONDAY + timedelta(hours=2), parent="parent"),
        make_run(
            "seed-2", MONDAY + timedelta(hours=2), MONDAY + timedelta(hours=4), parent="parent"
        ),
        make_run(
            "seed-3", MONDAY + timedelta(hours=4), MONDAY + timedelta(hours=6), parent="parent"
        ),
    ]
    leaves = quota.drop_parent_runs([parent, *seeds])
    assert [run.info.run_id for run in leaves] == ["seed-1", "seed-2", "seed-3"]

    hours, _ = quota.used_gpu_hours(leaves, MONDAY, MONDAY + timedelta(hours=8))
    assert hours == pytest.approx(6.0)


def test_standalone_run_survives_the_parent_filter():
    solo = make_run("solo", MONDAY, MONDAY + timedelta(hours=1))
    assert quota.drop_parent_runs([solo]) == [solo]


# --- how the runs are fetched ----------------------------------------------


def test_query_asks_for_all_runs_including_deleted_ones():
    # Soft-deleting a run in the UI would otherwise erase its hours from the week.
    client = FakeClient(pages=[Page([])])
    list(quota.iter_runs(client, "1", MONDAY, VIEW_ALL))
    assert client.calls[0]["run_view_type"] == VIEW_ALL


def test_pagination_is_followed_to_the_end():
    # A truncated sum always under-counts, which errs towards overspending.
    first = Page([make_run("a", MONDAY, MONDAY + timedelta(hours=1))], token="1")
    second = Page([make_run("b", MONDAY, MONDAY + timedelta(hours=1))])
    client = FakeClient(pages=[first, second])
    runs = list(quota.iter_runs(client, "1", MONDAY, VIEW_ALL))
    assert [run.info.run_id for run in runs] == ["a", "b"]
    assert len(client.calls) == 2


def test_repeated_page_is_neither_an_infinite_loop_nor_a_double_charge():
    # A backend that keeps handing back the same token must not invent hours that were
    # never spent, and must not spin forever either.
    looping = Page([make_run("a", MONDAY, MONDAY + timedelta(hours=1))], token="0")
    client = FakeClient(pages=[looping])
    runs = list(quota.iter_runs(client, "1", MONDAY, VIEW_ALL))
    assert [run.info.run_id for run in runs] == ["a"]


# --- fail closed -----------------------------------------------------------


def test_missing_tracking_uri_is_undetermined_not_zero(monkeypatch, capsys):
    client = FakeClient()
    code = run_main(["--quota", "40"], client, monkeypatch, tracking_uri=None)
    assert code == quota.EXIT_UNDETERMINED
    assert "MLFLOW_TRACKING_URI" in capsys.readouterr().err


def test_local_store_is_allowed_when_asked_for_explicitly(monkeypatch):
    client = FakeClient()
    code = run_main(
        ["--quota", "40", "--allow-local-store"], client, monkeypatch, tracking_uri=None
    )
    assert code == quota.EXIT_OK


def test_missing_experiment_is_undetermined_not_zero(monkeypatch, capsys):
    # A typo in --experiment and a wrong tracking server look identical to "nothing spent".
    client = FakeClient(experiment_id=None)
    code = run_main(["--quota", "40"], client, monkeypatch)
    assert code == quota.EXIT_UNDETERMINED
    assert "QUOTA UNDETERMINED" in capsys.readouterr().err


def test_missing_experiment_may_be_waved_through_explicitly(monkeypatch):
    client = FakeClient(experiment_id=None)
    code = run_main(["--quota", "40", "--allow-missing-experiment"], client, monkeypatch)
    assert code == quota.EXIT_OK


def test_tracking_server_failure_is_undetermined(monkeypatch, capsys):
    class BrokenClient(FakeClient):
        def get_experiment_by_name(self, name):
            raise ConnectionError("tracking server unreachable")

    code = run_main(["--quota", "40"], BrokenClient(), monkeypatch)
    assert code == quota.EXIT_UNDETERMINED
    assert "QUOTA UNDETERMINED" in capsys.readouterr().err


def test_absent_mlflow_is_undetermined(monkeypatch, capsys):
    def no_mlflow():
        raise quota.QuotaUndetermined("the mlflow package is required")

    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.osv.internal")
    code = quota.main(["--quota", "40"], client_factory=no_mlflow)
    assert code == quota.EXIT_UNDETERMINED
    err = capsys.readouterr().err
    assert "QUOTA UNDETERMINED" in err
    assert "QUOTA EXCEEDED" not in err


def test_malformed_quota_env_var_is_undetermined(monkeypatch, capsys):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.osv.internal")
    monkeypatch.setenv("OSV_GPU_QUOTA_HOURS", "forty")
    code = quota.main([], client_factory=factory_for(FakeClient()))
    assert code == quota.EXIT_UNDETERMINED
    assert "OSV_GPU_QUOTA_HOURS" in capsys.readouterr().err


# --- the verdict the agent reads -------------------------------------------


def test_within_budget_exits_zero(monkeypatch, capsys):
    # Freezing matters here too: against the real clock MONDAY falls in an
    # earlier week, the run is filtered out, and this passes on an empty sum
    # rather than on "1 hour is under 40".
    freeze_now(monkeypatch, MONDAY + timedelta(hours=60))
    pages = [Page([make_run("a", MONDAY, MONDAY + timedelta(hours=1))])]
    code = run_main(["--quota", "40"], FakeClient(pages=pages), monkeypatch)
    assert code == quota.EXIT_OK
    assert "STATUS: OK" in capsys.readouterr().out


def test_spent_budget_reports_the_line_the_agent_waits_for(monkeypatch, capsys):
    freeze_now(monkeypatch, MONDAY + timedelta(hours=60))
    pages = [Page([make_run("a", MONDAY, MONDAY + timedelta(hours=50))])]
    code = run_main(["--quota", "40"], FakeClient(pages=pages), monkeypatch)
    assert code == quota.EXIT_QUOTA_EXCEEDED
    assert "ARCH: QUOTA EXCEEDED" in capsys.readouterr().err


def test_exhaustion_can_be_reported_without_failing_the_pipeline(monkeypatch, capsys):
    # R-24 calls a spent budget a normal outcome; a scheduled job should not go red.
    freeze_now(monkeypatch, MONDAY + timedelta(hours=60))
    pages = [Page([make_run("a", MONDAY, MONDAY + timedelta(hours=50))])]
    code = run_main(
        ["--quota", "40", "--exit-zero-on-exhausted"], FakeClient(pages=pages), monkeypatch
    )
    assert code == quota.EXIT_OK
    assert "ARCH: QUOTA EXCEEDED" in capsys.readouterr().err


def test_exhausted_and_undetermined_do_not_share_an_exit_code():
    assert quota.EXIT_QUOTA_EXCEEDED != quota.EXIT_UNDETERMINED
