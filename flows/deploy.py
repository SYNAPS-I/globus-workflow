"""Deploy Globus Flow and Compute functions.

Registers the flow definition and compute functions with Globus, then
writes the resulting IDs back into flow_config.yaml so that the
execution scripts can use them without re-deploying.

Usage:
    python deploy.py [--config flow_config.yaml] [--flow] [--funcs] [--all]
"""

import argparse
import json
from pathlib import Path

import yaml
from globus_sdk import FlowsClient
from globus_compute_sdk import Client

from globus_auth import get_user_app


# ---------------------------------------------------------------------------
# Compute functions to register
# ---------------------------------------------------------------------------

def run_terminal_command(command: str) -> str:
    """Execute a shell command and return its stdout or stderr.

    NOTE: This is a standalone copy for Globus Compute registration.
    It must NOT import from local modules (e.g. utils) because the remote
    endpoint does not have them installed.
    """
    import subprocess

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)


def process_file(input_path):
    """Count lines in a transferred file."""
    with open(input_path, "r") as f:
        return f"Line count: {len(f.readlines())}"


def pi_calc(num_points=10**8):
    """Monte-Carlo estimate of pi."""
    from random import random

    inside = 0
    for _ in range(num_points):
        x, y = random(), random()
        if x**2 + y**2 < 1:
            inside += 1
    return inside * 4 / num_points


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_config(config: dict, config_path: Path) -> None:
    """Write the config dict back to YAML, preserving key order."""
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"Configuration saved to {config_path}")


# ---------------------------------------------------------------------------
# Deployment actions
# ---------------------------------------------------------------------------

def deploy_flow(config: dict, config_path: Path) -> str:
    """Deploy (or re-deploy) the Globus Flow and persist the new flow_id."""
    app = get_user_app(config)
    flows_client = FlowsClient(app=app)

    flow_def_file = Path(__file__).parent / config["flow"]["definition_file"]
    with open(flow_def_file, "r") as f:
        flow_definition = json.load(f)

    flow = flows_client.create_flow(
        title=config["flow"]["title"],
        definition=flow_definition,
        input_schema={},
    )
    flow_id = flow["id"]
    print(f"Flow deployed! ID: {flow_id}")

    config["globus"]["flow_id"] = flow_id
    _save_config(config, config_path)
    return flow_id


def deploy_funcs(config: dict, config_path: Path) -> dict:
    """Register Globus Compute functions and persist IDs to config."""
    gc = Client()

    func_ids = {
        "func_id_run_terminal_command": gc.register_function(run_terminal_command),
        "func_id_file_process": gc.register_function(process_file),
        "func_id_pi_calc": gc.register_function(pi_calc),
    }

    for key, fid in func_ids.items():
        print(f"Registered {key}: {fid}")

    config.setdefault("deployment", {}).update(func_ids)
    _save_config(config, config_path)
    return func_ids


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Globus Flow and/or Compute functions."
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=Path(__file__).parent / "flow_config.yaml",
        help="Path to flow_config.yaml (default: ./flow_config.yaml)",
    )
    parser.add_argument(
        "--flow",
        action="store_true",
        help="Deploy the Globus Flow definition.",
    )
    parser.add_argument(
        "--funcs",
        action="store_true",
        help="Register Globus Compute functions.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Deploy both the flow and compute functions.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not (args.flow or args.funcs or args.all):
        parser.error("Specify --flow, --funcs, or --all.")

    if args.flow or args.all:
        deploy_flow(config, config_path)

    if args.funcs or args.all:
        deploy_funcs(config, config_path)

    print("Deployment complete.")


if __name__ == "__main__":
    main()
