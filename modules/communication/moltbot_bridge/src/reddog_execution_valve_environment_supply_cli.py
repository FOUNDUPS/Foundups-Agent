"""CLI for canonical RedDog execution-valve environment supply."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from modules.communication.moltbot_bridge.src.reddog_execution_valve_environment_supply_bootstrap import (
    run_reddog_execution_valve_environment_supply_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import VALVE_CLOSED


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--work-state", required=True)
    parser.add_argument("--authority-profile", required=True)
    parser.add_argument("--permission-snapshots", required=True)
    parser.add_argument("--principal-authority-records", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--requested-valve-state", default=VALVE_CLOSED)
    parser.add_argument("--queue-item-id", default="")
    parser.add_argument("--now-epoch", type=int)
    parser.add_argument("--permission-ttl-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    result = run_reddog_execution_valve_environment_supply_bootstrap(
        repo_root=args.repo_root,
        runtime_allowed_root=args.runtime_root,
        work_state_path=args.work_state,
        authority_profile_path=args.authority_profile,
        permission_snapshots_path=args.permission_snapshots,
        principal_authority_records_path=args.principal_authority_records,
        output_path=args.output,
        requested_valve_state=args.requested_valve_state,
        queue_item_id=args.queue_item_id,
        now_epoch=args.now_epoch,
        permission_ttl_seconds=args.permission_ttl_seconds,
    )
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
