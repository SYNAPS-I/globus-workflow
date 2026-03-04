"""Shared utilities for the Globus workflow scripts.

Centralises helpers that are used across multiple scripts so they are
defined once and imported everywhere.
"""

import os
import subprocess

import yaml


def load_config(config_filename: str = "flow_config.yaml") -> dict:
    """Load and return the unified YAML configuration.

    Parameters
    ----------
    config_filename:
        Name of the YAML file located alongside the calling script.
        Resolved relative to the ``flows/`` directory.
    """
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), config_filename
    )
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_local_terminal_command(command: str) -> str:
    """Execute a shell command locally and return its stdout or stderr.

    This is only used for *local* execution.  Remote Globus Compute
    endpoints use self-contained functions defined in ``deploy.py``.

    Parameters
    ----------
    command:
        The shell command string to execute.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)
