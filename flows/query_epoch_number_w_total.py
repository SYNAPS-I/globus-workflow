#!/usr/bin/env python3
"""Resolve current epoch from a Weights & Biases run."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

from utils import load_config

try:
    import wandb  # type: ignore
except Exception as exc:
    print(f"ERROR: wandb is required to run this script: {exc}", file=sys.stderr)
    raise SystemExit(1)

# Load configuration from YAML
CONFIG = load_config()


def _is_valid_loss(value: Any) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return not math.isnan(numeric)


def _pick_run(
    api: "wandb.Api",
    *,
    wandb_entity: str,
    project: str,
    wandb_run_id: str | None,
):
    if wandb_run_id:
        return api.run(f"{wandb_entity}/{project}/{wandb_run_id}")

    runs = list(api.runs(f"{wandb_entity}/{project}", order="-created_at"))
    if not runs:
        raise RuntimeError(f"No runs found for {wandb_entity}/{project}")
    return runs[0]


def _count_valid_train_loss(run: Any) -> int:
    count = 0
    try:
        for row in run.scan_history(keys=["train_loss"]):
            if _is_valid_loss(row.get("train_loss")):
                count += 1
    except Exception as exc:
        raise RuntimeError(
            f"Could not determine epoch from train_loss history for run {getattr(run, 'id', 'unknown')}: {exc}"
        ) from exc
    return count


def get_current_epoch(
    wandb_entity: str = CONFIG["wandb"]["entity"],
    project: str = CONFIG["wandb"]["project"],
    wandb_run_id: str | None = CONFIG["wandb"].get("run_id"),
    wandb_api_key: str | None = CONFIG["wandb"].get("api_key"),
    wandb_api_key_path: str | None = CONFIG["wandb"].get("api_key_path"),
    verbose: bool = False,
) -> tuple[int, int]:
    """Return (current_epoch, total_epochs) for a W&B run."""
    resolved_api_key = wandb_api_key
    if not resolved_api_key and wandb_api_key_path:
        try:
            with open(wandb_api_key_path) as f:
                resolved_api_key = f.read().strip()
        except OSError:
            pass
    if not resolved_api_key:
        resolved_api_key = os.environ.get("WANDB_API_KEY")
    if not resolved_api_key:
        raise RuntimeError(
            "WANDB API key not found. Set wandb.api_key or wandb.api_key_path "
            "in flow_config.yaml, or export WANDB_API_KEY."
        )
    os.environ["WANDB_API_KEY"] = resolved_api_key

    api = wandb.Api()
    run = _pick_run(
        api,
        wandb_entity=wandb_entity,
        project=project,
        wandb_run_id=wandb_run_id,
    )
    if verbose:
        print(
            f"[get_current_epoch] entity={wandb_entity} project={project} "
            f"run_id={getattr(run, 'id', 'unknown')} run_name={getattr(run, 'name', 'unknown')}"
        )

    epoch = _count_valid_train_loss(run)
    config = run.config
    if isinstance(config, str):
        total_epochs_raw = json.loads(run.config).get("epochs").get("value")
    else:
        total_epochs_raw = config.get("epochs")#.get("value")
    if total_epochs_raw is None:
        raise RuntimeError(
            f'Run {getattr(run, "id", "unknown")} is missing "epochs" in logged config'
        )
    try:
        total_epochs = int(total_epochs_raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f'Run {getattr(run, "id", "unknown")} has non-integer "epochs" in logged config: {total_epochs_raw!r}'
        ) from exc

    if verbose:
        print(
            f"[get_current_epoch] valid_train_loss_count={epoch} "
            f"epoch={epoch} total_epochs={total_epochs}"
        )
    return epoch, total_epochs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Get current epoch for a W&B run from valid train_loss logs.",
    )
    parser.add_argument(
        "--wandb-entity",
        default=CONFIG["wandb"]["entity"],
        help=f"W&B entity/user/team (default: {CONFIG['wandb']['entity']})",
    )
    parser.add_argument(
        "--project",
        default=CONFIG["wandb"]["project"],
        help=f"W&B project name (default: {CONFIG['wandb']['project']})",
    )
    parser.add_argument(
        "--wandb-run-id",
        default=CONFIG["wandb"].get("run_id"),
        help="Optional W&B run ID. If omitted, uses the latest run in the project.",
    )
    parser.add_argument(
        "--wandb-api-key",
        default=CONFIG["wandb"].get("api_key"),
        help="W&B API key. If omitted, reads WANDB_API_KEY from environment.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug information (selected run ID, valid train_loss count, epoch).",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        epoch, total_epochs = get_current_epoch(
            wandb_entity=args.wandb_entity,
            project=args.project,
            wandb_run_id=args.wandb_run_id,
            wandb_api_key=args.wandb_api_key,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"{epoch}/{total_epochs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
 
