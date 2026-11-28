"""Explicit fixed-range lake acceptance. Run inside the controlled data environment."""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from app.services.lake_ingress import IngressProfile
from app.services.lake_replay import ReplayLimits, private_json, run_replay
from app.services.lake_writer import LakeWriter
from app.workers.lake_consumer import LakeConsumerProfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("connection", "ingress", "consumer", "limits", "private-results", "execution-status"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    if args.execution_status.exists() or args.private_results.exists():
        raise FileExistsError("new acceptance batch required")
    passed = False
    try:
        connection = json.loads(args.connection.read_text())
        ingress = IngressProfile.load(args.ingress, database=connection["database"])
        writer = LakeWriter(**connection, ingress_profile=ingress)
        passed = asyncio.run(run_replay(writer, LakeConsumerProfile.load(args.consumer),
                                       ReplayLimits.load(args.limits), args.private_results))
    except (Exception, asyncio.CancelledError):  # noqa: BLE001 - no exception values may leave the data host
        passed = False
    # The only public result: fixed execution/verdict flags, never data counts,
    # IDs, category values, content digests, positions or query snapshots.
    status = {"schema_version": "socai2.lake-replay-execution.v1",
              "execution": "completed" if passed else "incomplete", "validation": "passed" if passed else "not_passed",
              "private_report_saved": (args.private_results / "report.json").is_file()}
    private_json(args.execution_status, status)
    print(json.dumps(status))
    return 0 if passed else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001 - safe launcher failure, no values
        print('{"execution":"incomplete","validation":"not_passed","private_report_saved":false}')
        raise SystemExit(2)
