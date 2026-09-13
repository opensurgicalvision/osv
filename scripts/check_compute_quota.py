#!/usr/bin/env python3
"""
Enforce the weekly GPU compute quota for OpenSurgicalVision arch-runner (R-24).

Queries MLflow for the runs of the current calendar week and sums their GPU-hours.
Exits 1 with 'ARCH: QUOTA EXCEEDED' when the budget is spent, 2 when the usage
cannot be determined at all.

Two properties matter more than the arithmetic:

* **It fails closed.** A quota check that cannot see the tracking server reports
  "cannot determine", never "zero used". The cheapest way to get unlimited GPU is a
  fresh CI container with no MLFLOW_TRACKING_URI, where a naive check finds no
  experiment and waves the run through.
* **It counts GPU-hours, not wall-clock.** Grants are denominated in GPU-hours, and a
  run on four GPUs spends four times what its duration suggests.

The import of mlflow is deliberately lazy so the module can be imported - and tested -
without the package installed.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

# Distinct codes: the caller has to tell a spent budget (a normal end to the week,
# R-24) apart from broken accounting (a human problem). Sharing exit 1 for both means
# an MLflow outage looks exactly like a quiet, well-behaved agent.
EXIT_OK = 0
EXIT_QUOTA_EXCEEDED = 1
EXIT_UNDETERMINED = 2

DEFAULT_QUOTA_HOURS = 40.0
DEFAULT_EXPERIMENT = "osv-arch-sandbox"
DEFAULT_LOOKBACK_DAYS = 14
PAGE_SIZE = 1000

# Where a run records how many GPUs it held. First match wins.
GPU_COUNT_KEYS = ("gpu_count", "gpus", "world_size", "num_gpus")

MS_PER_HOUR = 1000.0 * 60.0 * 60.0


class QuotaUndetermined(Exception):
    """Usage could not be established. Never treated as zero usage."""


def write_dotenv(path: str | None, state: str, quota: float, used: float | None) -> None:
    """Hand the verdict to the rest of the pipeline as a dotenv report.

    The remaining budget is not decoration: it is the wall-clock cap the training job
    is started with, which is what turns "how much is left" into "this much and no
    more". Written on every outcome, including the undetermined one, so a downstream
    job never inherits a stale value from an earlier pipeline.
    """
    if not path:
        return
    remaining = "" if used is None else f"{max(quota - used, 0.0):.4f}"
    lines = [
        f"OSV_QUOTA_STATE={state}",
        f"OSV_GPU_HOURS_QUOTA={quota:.4f}",
        f"OSV_GPU_HOURS_USED={'' if used is None else f'{used:.4f}'}",
        f"OSV_GPU_HOURS_REMAINING={remaining}",
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def get_week_start_time(now: datetime | None = None) -> datetime:
    """Monday 00:00:00 UTC of the current calendar week."""
    now = now or datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def build_client():
    """Return (client, view_type_all). Raises QuotaUndetermined if mlflow is absent."""
    try:
        from mlflow.entities import ViewType
        from mlflow.tracking import MlflowClient
    except ImportError as exc:  # pragma: no cover - exercised through main()
        raise QuotaUndetermined(
            "the mlflow package is required to read compute usage; install it or run "
            "inside the project container"
        ) from exc
    return MlflowClient(), ViewType.ALL


def iter_runs(client, experiment_id: str, since: datetime, view_type, page_size: int = PAGE_SIZE):
    """All runs started since `since`, following pagination to the end.

    Both defaults of MLflowClient.search_runs are wrong for a budget query:
    max_results caps at 1000 (a truncated sum always under-counts, i.e. errs towards
    overspending) and run_view_type is ACTIVE_ONLY (soft-deleting a run in the UI would
    erase its hours from the week).
    """
    start_ts = int(since.timestamp() * 1000)
    filter_string = f"attributes.start_time >= {start_ts}"
    page_token = None
    seen_tokens = set()
    emitted = set()
    while True:
        page = client.search_runs(
            experiment_ids=[experiment_id],
            filter_string=filter_string,
            run_view_type=view_type,
            max_results=page_size,
            page_token=page_token,
        )
        for run in page:
            # Overlapping or repeated pages must not be charged twice: this sum is a
            # budget, and a backend hiccup should never invent hours that were not spent.
            if run.info.run_id in emitted:
                continue
            emitted.add(run.info.run_id)
            yield run
        page_token = getattr(page, "token", None)
        if not page_token or page_token in seen_tokens:
            break
        seen_tokens.add(page_token)


def drop_parent_runs(runs: list) -> list:
    """Keep leaf runs only.

    arch-runner nests one child run per seed under a parent run per hypothesis, and the
    parent's duration spans all of its children. Summing both double-counts every hour,
    which would silence the agent at half its budget.
    """
    runs = list(runs)
    parent_ids = {run.data.tags.get("mlflow.parentRunId") for run in runs}
    parent_ids.discard(None)
    return [run for run in runs if run.info.run_id not in parent_ids]


def gpu_count_for(run) -> tuple[int, bool]:
    """(gpus held by the run, whether it was actually recorded)."""
    for source in (run.data.params, run.data.tags):
        for key in GPU_COUNT_KEYS:
            raw = source.get(key)
            if raw is None:
                continue
            try:
                value = int(float(raw))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value, True
    return 1, False


def used_gpu_hours(runs, week_start: datetime, now: datetime) -> tuple[float, list[str]]:
    """Sum GPU-hours spent inside the current week. Returns (hours, untagged run ids).

    A run is clamped to the week, so one that started on Sunday and is still going
    contributes only its Monday-onwards share instead of nothing at all. A run without
    an end_time is counted up to now: a crash loop that never closes its runs must not
    be a way to spend for free.
    """
    week_start_ms = int(week_start.timestamp() * 1000)
    now_ms = int(now.timestamp() * 1000)

    total_ms = 0.0
    untagged = []
    for run in runs:
        start = run.info.start_time
        if not start:
            continue
        end = run.info.end_time or now_ms
        start = max(start, week_start_ms)
        end = min(end, now_ms)
        if end <= start:
            continue

        gpus, recorded = gpu_count_for(run)
        if not recorded:
            untagged.append(run.info.run_id)
        total_ms += (end - start) * gpus

    return total_ms / MS_PER_HOUR, untagged


def resolve_experiment(client, name: str, allow_missing: bool) -> str | None:
    experiment = client.get_experiment_by_name(name)
    if experiment is not None:
        return experiment.experiment_id
    if allow_missing:
        return None
    raise QuotaUndetermined(
        f"experiment '{name}' does not exist on this tracking server. That is either a "
        "typo or the wrong server - both look identical to 'nothing has been spent'. "
        "Pass --allow-missing-experiment for the very first run of the sandbox."
    )


def main(argv: list[str] | None = None, client_factory=build_client) -> int:
    parser = argparse.ArgumentParser(description="Enforce weekly GPU compute quota (R-24)")
    parser.add_argument(
        "--quota",
        type=float,
        default=None,
        help=f"Max GPU-hours per week (default: OSV_GPU_QUOTA_HOURS or {DEFAULT_QUOTA_HOURS})",
    )
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT, help="MLflow experiment name")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help="How far back to query so runs crossing the week boundary are seen (default: 14)",
    )
    parser.add_argument(
        "--allow-missing-experiment",
        action="store_true",
        help="Treat a missing experiment as zero usage. For the first run of the sandbox only.",
    )
    parser.add_argument(
        "--allow-local-store",
        action="store_true",
        help="Permit the default local ./mlruns store instead of requiring MLFLOW_TRACKING_URI.",
    )
    parser.add_argument(
        "--emit-dotenv",
        default=None,
        help="Write OSV_QUOTA_STATE / OSV_GPU_HOURS_REMAINING to this file for a GitLab "
        "dotenv report, so the training job can be capped at the remaining budget.",
    )
    parser.add_argument(
        "--exit-zero-on-exhausted",
        action="store_true",
        help="Report an exhausted budget on stderr but exit 0. R-24 calls exhaustion a normal "
        "outcome, so a scheduled pipeline should not go red for it.",
    )
    args = parser.parse_args(argv)

    quota = args.quota
    if quota is None:
        raw = os.environ.get("OSV_GPU_QUOTA_HOURS")
        try:
            quota = float(raw) if raw else DEFAULT_QUOTA_HOURS
        except ValueError:
            print(
                f"[osv.quota] ERROR: OSV_GPU_QUOTA_HOURS is not a number: {raw!r}",
                file=sys.stderr,
            )
            write_dotenv(args.emit_dotenv, "undetermined", 0.0, None)
            return EXIT_UNDETERMINED

    now = datetime.now(timezone.utc)
    week_start = get_week_start_time(now)

    try:
        if not os.environ.get("MLFLOW_TRACKING_URI") and not args.allow_local_store:
            raise QuotaUndetermined(
                "MLFLOW_TRACKING_URI is not set. Without it MLflow falls back to a local "
                "./mlruns store, which in a fresh CI container is empty - and an empty store "
                "reads as an unspent budget. Point at the tracking server, or pass "
                "--allow-local-store if the local store really is the source of truth."
            )

        client, view_type = client_factory()
        experiment_id = resolve_experiment(client, args.experiment, args.allow_missing_experiment)

        if experiment_id is None:
            print(f"[osv.quota] Experiment '{args.experiment}' not found; treating usage as zero.")
            used_hours, untagged = 0.0, []
        else:
            since = week_start - timedelta(days=max(args.lookback_days, 0))
            runs = drop_parent_runs(iter_runs(client, experiment_id, since, view_type))
            used_hours, untagged = used_gpu_hours(runs, week_start, now)
    except QuotaUndetermined as exc:
        print(f"[osv.quota] ERROR: {exc}", file=sys.stderr)
        print("ARCH: QUOTA UNDETERMINED", file=sys.stderr)
        write_dotenv(args.emit_dotenv, "undetermined", quota, None)
        return EXIT_UNDETERMINED
    except Exception as exc:  # noqa: BLE001 - any failure here is "cannot determine"
        print(f"[osv.quota] ERROR: could not read usage from MLflow: {exc}", file=sys.stderr)
        print("ARCH: QUOTA UNDETERMINED", file=sys.stderr)
        write_dotenv(args.emit_dotenv, "undetermined", quota, None)
        return EXIT_UNDETERMINED

    print(f"[osv.quota] Tracking week starting: {week_start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"[osv.quota] Usage: {used_hours:.2f} / {quota:.2f} GPU-hours")
    if untagged:
        print(
            f"[osv.quota] WARNING: {len(untagged)} run(s) record no GPU count "
            f"({', '.join(untagged[:3])}{'...' if len(untagged) > 3 else ''}); counted as 1 GPU "
            "each, so a multi-GPU run among them is under-charged.",
            file=sys.stderr,
        )

    if used_hours >= quota:
        write_dotenv(args.emit_dotenv, "exhausted", quota, used_hours)
        print("ARCH: QUOTA EXCEEDED", file=sys.stderr)
        print(f"Weekly GPU budget of {quota:.2f} GPU-hours is spent.", file=sys.stderr)
        print(
            "Save the current seed and stop. The series resumes next week from the first "
            "seed that is not FINISHED (R-24).",
            file=sys.stderr,
        )
        return EXIT_OK if args.exit_zero_on_exhausted else EXIT_QUOTA_EXCEEDED

    remaining = quota - used_hours
    write_dotenv(args.emit_dotenv, "ok", quota, used_hours)
    print(f"[osv.quota] STATUS: OK. Remaining budget: {remaining:.2f} hrs.")
    print(
        "[osv.quota] NOTE: this is a pre-flight check. Cap the run's wall clock at the "
        f"remaining {remaining:.2f} h, or a single long run overshoots the week.",
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
