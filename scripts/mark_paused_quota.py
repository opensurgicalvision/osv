#!/usr/bin/env python3
"""
Mark the in-flight hypothesis as PAUSED_QUOTA when the weekly budget runs out (R-24).

Exhausting the quota is a normal end to the week, not a crash - but only if the state
survives it. Without this marker the next cycle cannot tell "three seeds finished, the
fourth was cut short" from "somebody started this and abandoned it", and the safe
reading of an ambiguous parent run is to start the hypothesis over, which spends the
new week's budget on work that was already paid for.

The marker is a tag, not a run status: MLflow's own statuses (RUNNING / FINISHED /
FAILED / KILLED) have fixed meanings, and overloading KILLED to mean "paused on
purpose" would make a deliberate stop indistinguishable from an OOM.

Exit codes match check_compute_quota.py: 0 when the state is recorded (or when there
was nothing in flight to record), 2 when it could not be recorded - losing the state
silently is worse than a red pipeline.
"""

import argparse
import os
import sys
from datetime import datetime, timezone

EXIT_OK = 0
EXIT_UNDETERMINED = 2

STATUS_TAG = "osv.status"
PAUSED_AT_TAG = "osv.paused_at"
PAUSED_REASON_TAG = "osv.paused_reason"
PAUSED_STATUS = "PAUSED_QUOTA"


class MarkFailed(Exception):
    """The pause could not be recorded."""


def build_client():
    """Return an MlflowClient. Raises MarkFailed if mlflow is absent."""
    try:
        from mlflow.tracking import MlflowClient
    except ImportError as exc:  # pragma: no cover - exercised through main()
        raise MarkFailed(
            "the mlflow package is required to record the pause; install it or run "
            "inside the project container"
        ) from exc
    return MlflowClient()


def mark_paused(client, run_id: str, reason: str, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    client.set_tag(run_id, STATUS_TAG, PAUSED_STATUS)
    client.set_tag(run_id, PAUSED_AT_TAG, now.isoformat(timespec="seconds"))
    client.set_tag(run_id, PAUSED_REASON_TAG, reason)


def main(argv: list[str] | None = None, client_factory=build_client) -> int:
    parser = argparse.ArgumentParser(description="Mark a hypothesis PAUSED_QUOTA (R-24)")
    parser.add_argument(
        "--run-id",
        default=os.environ.get("OSV_PARENT_RUN_ID"),
        help="Parent MLflow run of the hypothesis (default: OSV_PARENT_RUN_ID)",
    )
    parser.add_argument(
        "--reason",
        default="weekly GPU quota exhausted",
        help="Recorded verbatim on the run so the next cycle can read why it stopped",
    )
    args = parser.parse_args(argv)

    if not args.run_id:
        # Nothing was in flight: the gate refused before a hypothesis was started.
        # That is the common case on a Friday and is not a problem to report.
        print("[osv.quota] No hypothesis in flight (OSV_PARENT_RUN_ID unset); nothing to pause.")
        return EXIT_OK

    try:
        client = client_factory()
        mark_paused(client, args.run_id, args.reason)
    except MarkFailed as exc:
        print(f"[osv.quota] ERROR: {exc}", file=sys.stderr)
        print("ARCH: PAUSE NOT RECORDED", file=sys.stderr)
        return EXIT_UNDETERMINED
    except Exception as exc:  # noqa: BLE001 - any failure here loses run state
        print(f"[osv.quota] ERROR: could not tag run {args.run_id}: {exc}", file=sys.stderr)
        print("ARCH: PAUSE NOT RECORDED", file=sys.stderr)
        return EXIT_UNDETERMINED

    print(f"[osv.quota] Run {args.run_id} marked {PAUSED_STATUS}: {args.reason}")
    print("[osv.quota] It resumes next cycle from the first seed that is not FINISHED.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
