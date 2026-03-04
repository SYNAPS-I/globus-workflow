#!/usr/bin/env python3
"""Resolve current epoch from a Weights & Biases run."""

from __future__ import annotations

import argparse
import math
import os
import sys
from typing import Any

try:
    import wandb  # type: ignore
except Exception as exc:
    print(f"ERROR: wandb is required to run this script: {exc}", file=sys.stderr)
    raise SystemExit(1)


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
    wandb_entity: str = "SYNAPS-I",
    project: str = "OnlineLearning",
    wandb_run_id: str | None = None,
    wandb_api_key: str | None = None,
    verbose: bool = False,
) -> int:
    """Return current epoch number inferred from count of valid train_loss logs."""
    resolved_api_key = wandb_api_key or os.environ.get("WANDB_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("WANDB_API_KEY is not set in the environment")
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
    if verbose:
        print(f"[get_current_epoch] valid_train_loss_count={epoch} epoch={epoch}")
    return epoch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Get current epoch for a W&B run from valid train_loss logs.",
    )
    parser.add_argument(
        "--wandb-entity",
        default="SYNAPS-I",
        help="W&B entity/user/team (default: SYNAPS-I)",
    )
    parser.add_argument(
        "--project",
        default="OnlineLearning",
        help="W&B project name (default: OnlineLearning)",
    )
    parser.add_argument(
        "--wandb-run-id",
        default=None,
        help="Optional W&B run ID. If omitted, uses the latest run in the project.",
    )
    parser.add_argument(
        "--wandb-api-key",
        default=None,
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
        epoch = get_current_epoch(
            wandb_entity=args.wandb_entity,
            project=args.project,
            wandb_run_id=args.wandb_run_id,
            wandb_api_key=args.wandb_api_key,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
 
