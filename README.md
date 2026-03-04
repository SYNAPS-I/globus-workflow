# globus-workflow

Globus workflow components and scripts for the [SYNAPS-I](https://github.com/SYNAPS-I) project.
This repository automates a **ptychography fine-tuning pipeline** that transfers
data between facilities, submits PBS training jobs via Globus Compute, and
monitors progress through Weights & Biases — all orchestrated as a
[Globus Flow](https://www.globus.org/globus-flows-service).

## Repository Structure

```
globus-workflow/
├── flows/                  # Core workflow scripts (see below)
│   ├── flow_config.yaml    # Unified configuration
│   ├── flow.json           # Globus Flow state-machine definition
│   ├── globus_auth.py      # OAuth token management
│   ├── deploy.py           # Deploy flow & compute functions
│   ├── sample_flow.py      # Run a deployed flow
│   ├── globus_flow_status.py       # Monitor a running flow
│   ├── globus_flow_run_cancel.py   # Cancel a running flow
│   ├── monitor_folder_flow_init.py # File-watcher entry point
│   ├── pbs_queue_check.py          # Check PBS queue via Globus Compute
│   ├── query_epoch_number_w_total.py # Query W&B training epoch
│   └── utils.py            # Shared helpers
├── compute/                # Globus Compute functions & endpoint configs
│   ├── functions/          # Python functions for remote execution
│   └── endpoints/          # Endpoint configuration files
├── tests/                  # Pytest suite (tokens, endpoints, compute)
├── examples/               # Usage examples & helper scripts
├── docs/                   # Documentation
├── secrets/                # Token & API key files (git-ignored)
├── pyproject.toml          # Python packaging & tool config
└── Makefile                # Common dev commands
```

## Pipeline Overview

The workflow executes a five-step Globus Flow defined in `flows/flow.json`:

```
1. TriggerPruningProcess      – Clean the remote training directory
2. TransferFineTuningData     – Transfer training data (source → HPC)
3. TriggerFineTuningProcess   – Submit a PBS fine-tuning job via Globus Compute
4. TransferFineTunedModel     – Transfer the trained model (HPC → source)
5. PostFinetuningCleanup      – Clean up the remote model directory
```

The flow can be triggered manually or automatically via the directory-watcher
entry point:

```
monitor_folder_flow_init.py   (watches for a trigger file)
  ├── sample_flow.py           (starts the Globus Flow)
  └── globus_flow_status.py    (monitors progress in a detached process)
        ├── pbs_queue_check.py            (queries PBS job state)
        └── query_epoch_number_w_total.py (queries W&B for training epoch)
```

---

## Quick Start

### 1. Prerequisites

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) package manager
- A [Globus](https://www.globus.org/) account with access to the required
  collections and a Globus Compute endpoint

### 2. Install

```bash
git clone https://github.com/SYNAPS-I/globus-workflow.git
cd globus-workflow
uv sync --group dev
```

### 3. Configure

Edit `flows/flow_config.yaml` with your own values (see
[Configuration](#configuration) below), then authenticate:

```bash
cd flows
python sample_flow.py          # triggers browser-based Globus login on first run
```

Tokens are cached automatically under `~/.globus/app/` (UserApp) or the path
specified by `globus.token_file` in the config.

### 4. Deploy

Register the Globus Flow definition and Compute functions (one-time, or
whenever definitions change):

```bash
cd flows
python deploy.py --all         # deploy both flow + compute functions
python deploy.py --flow        # deploy only the flow definition
python deploy.py --funcs       # register only the compute functions
```

`deploy.py` writes the resulting IDs back into `flow_config.yaml` so that
subsequent scripts can reference them automatically.

### 5. Run

```bash
# Manual run
python sample_flow.py

# Or start the file-watcher (automated trigger)
python monitor_folder_flow_init.py
```

---

## Flows Scripts Reference

All scripts live under `flows/` and read from a single `flow_config.yaml`.

### `deploy.py` — Deploy Flow & Compute Functions

Registers the flow definition (`flow.json`) and three Globus Compute functions
(`run_terminal_command`, `process_file`, `pi_calc`) with Globus, then persists
the resulting IDs into `flow_config.yaml`.

```bash
python deploy.py --all                     # deploy everything
python deploy.py --flow                    # deploy only the flow
python deploy.py --funcs                   # register only compute functions
python deploy.py --config /path/to/config  # use a custom config file
```

### `sample_flow.py` — Run a Deployed Flow

Starts a previously deployed Globus Flow with the parameters from the config.
Prints the flow run ID on success.

```bash
python sample_flow.py
python sample_flow.py --config /path/to/config
```

> **Note:** Requires `flow_id` and compute function IDs to be set in
> `flow_config.yaml`. Run `deploy.py` first if they are missing.

### `globus_flow_status.py` — Monitor a Running Flow

Polls the flow run status at a configurable interval. Logs state transitions,
PBS queue status, and W&B training epoch to both a log file and stdout.

```bash
python globus_flow_status.py <RUN_ID>
python globus_flow_status.py                # uses default_run_id from config
```

Log files are written to the directory specified by `monitoring.log_directory`.

### `globus_flow_run_cancel.py` — Cancel a Running Flow

Cancels an active flow run and kills associated PBS jobs on the compute
endpoint.

```bash
python globus_flow_run_cancel.py --run-id <RUN_UUID>
```

### `monitor_folder_flow_init.py` — File-Watcher Entry Point

Watches a directory for a trigger file (configured in `monitoring.target_filename`).
When the file appears, it:

1. Executes `sample_flow.py` to start the flow
2. Captures the run ID from stdout
3. Launches `globus_flow_status.py` as a detached monitoring process
4. Removes the trigger file

```bash
python monitor_folder_flow_init.py
```

Configuration keys used:
- `monitoring.directory_to_watch` — path to watch
- `monitoring.target_filename` — filename that triggers the flow
- `monitoring.script_to_execute` — path to `sample_flow.py`
- `monitoring.monitor_flow_script_path` — path to `globus_flow_status.py`

### `pbs_queue_check.py` — Check PBS Queue Status

Submits a remote `qstat` command to the Globus Compute endpoint and prints
the job status.

```bash
python pbs_queue_check.py
```

### `query_epoch_number_w_total.py` — Query Training Epoch from W&B

Queries Weights & Biases for the current training epoch by counting valid
`train_loss` entries in the run history.

```bash
python query_epoch_number_w_total.py
python query_epoch_number_w_total.py --verbose
python query_epoch_number_w_total.py --wandb-entity SYNAPS-I --project OnlineLearning
```

### `utils.py` — Shared Helpers

- `load_config()` — loads `flow_config.yaml` from the `flows/` directory
- `run_local_terminal_command(command)` — executes a shell command locally

### `globus_auth.py` — Authentication Module

Handles Globus OAuth token management. Provides two authentication patterns:

| Function | Used by | Auth method |
|----------|---------|-------------|
| `get_authorizer()` | `globus_flow_status.py`, `globus_flow_run_cancel.py` | `NativeAppAuthClient` |
| `get_user_app()` | `sample_flow.py`, `deploy.py`, tests | `UserApp` |

Both patterns cache tokens to disk and reuse them across sessions. On first
run, a browser-based login flow is launched.

---

## Configuration

All scripts share a single configuration file: `flows/flow_config.yaml`.

### `globus` — Authentication & App Settings

| Key | Description |
|-----|-------------|
| `client_id` | Globus Auth application (client) ID |
| `native_app_client_id` | Native App client ID for status/cancel scripts |
| `app_name` | Application name registered with Globus |
| `token_file` | Path to cached OAuth tokens (NativeAppAuthClient) |
| `flow_id` | Deployed Globus Flow UUID (written by `deploy.py`) |
| `default_run_id` | Default flow run ID for `globus_flow_status.py` |

### `endpoints` — Globus Collections & Compute

| Key | Description |
|-----|-------------|
| `source_collection_id` | Globus collection UUID for the data source (e.g. APS) |
| `dest_collection_id` | Globus collection UUID for the HPC destination (e.g. ALCF/Eagle) |
| `compute_endpoint_id` | Globus Compute endpoint UUID for remote execution (e.g., ALCF/Polaris) |

### `paths` — Data Transfer Paths

| Key | Description |
|-----|-------------|
| `source_path` | Path on the source collection for training data |
| `dest_path` | Path on the destination collection for training data |
| `model_source_path` | Path on HPC where the fine-tuned model is written |
| `model_dest_path` | Path on source where the model is transferred back |

### `flow` — Flow Execution Settings

| Key | Description |
|-----|-------------|
| `definition_file` | Flow JSON file name (default: `flow.json`) |
| `title` | Display title for the deployed flow |
| `run_label` | Label assigned to each flow run |
| `command_prune_dir_script` | Shell command to clean the training directory |
| `command_pbs_job_script` | Shell command to submit the PBS training job |
| `command_prune_post_finetuning` | Shell command to clean the model directory |

### `deployment` — Deployed Function IDs

Written automatically by `deploy.py`. Contains the UUIDs of registered Globus
Compute functions:

- `func_id_run_terminal_command`
- `func_id_file_process`
- `func_id_pi_calc`

### `pbs` — PBS Queue Settings

| Key | Description |
|-----|-------------|
| `user` | PBS username for `qstat` queries |
| `queue` | PBS queue name |
| `tail_lines` | Number of `qstat` output lines to return |

### `monitoring` — Flow Monitoring & File Watcher

| Key | Description |
|-----|-------------|
| `poll_interval_seconds` | How often to poll flow status |
| `terminal_states` | Flow states that stop polling (`SUCCEEDED`, `FAILED`) |
| `log_directory` | Where to write flow status log files |
| `directory_to_watch` | Path monitored by the file watcher |
| `target_filename` | Filename that triggers a new flow run |
| `python_executable` | Python interpreter for subprocess calls |
| `script_to_execute` | Path to `sample_flow.py` |
| `monitor_flow_script_path` | Path to `globus_flow_status.py` |

### `wandb` — Weights & Biases Integration

| Key | Description |
|-----|-------------|
| `entity` | W&B team or username |
| `project` | W&B project name |
| `run_id` | Specific W&B run ID (optional; uses latest if null) |
| `api_key` | W&B API key (optional) |
| `api_key_path` | Path to a file containing the W&B API key |

---

## Authentication

The project uses two Globus authentication methods depending on the script:

### UserApp (recommended)

Used by `sample_flow.py`, `deploy.py`, and the test suite. Tokens are stored
at `~/.globus/app/<client_id>/<app_name>/tokens.json` and managed
automatically by the Globus SDK.

On first use, a browser window opens for Globus login. Subsequent runs reuse
cached tokens and refresh them automatically.

### NativeAppAuthClient

Used by `globus_flow_status.py` and `globus_flow_run_cancel.py`. Tokens are
stored at the path specified in `globus.token_file` (typically under
`secrets/`). Falls back to `~/.globus/tokens.json` if the configured path
doesn't exist.

On first use, a URL is printed to the terminal. Open it in a browser,
authenticate, and paste the authorization code back into the terminal.

### Required Scopes

The workflow requires tokens with the following scopes:

- **Transfer** — `urn:globus:auth:scope:transfer.api.globus.org:all` with
  `data_access` for both source and destination collections
- **Flows** — manage, run, view, and check status of flows
- **Compute** — `urn:globus:auth:scope:funcx_service:all`

### Token Storage Locations

| Location | Used by | Format |
|----------|---------|--------|
| `~/.globus/app/<client_id>/<app_name>/tokens.json` | UserApp scripts | Globus SDK internal |
| `secrets/.globus_tokens.json` (configurable) | NativeApp scripts | `{resource_server: {access_token, refresh_token, ...}}` |
| `~/.globus/tokens.json` | Fallback for NativeApp | Same as above |

---

## Testing

The test suite validates endpoint connectivity, token health, and compute
function availability:

```bash
uv run pytest -v                           # run all tests
uv run pytest tests/test_globus_tokens.py  # token validation only
uv run pytest tests/test_transfer_endpoints.py  # transfer endpoint checks
uv run pytest tests/test_compute_endpoint.py    # compute endpoint & functions
```

| Test file | What it checks |
|-----------|----------------|
| `test_globus_tokens.py` | Token existence, validity, and expiry across all storage locations |
| `test_transfer_endpoints.py` | Collection accessibility, active status, directory listing |
| `test_compute_endpoint.py` | Endpoint online status, function execution, Python version match |

---

## Development

```bash
make lint          # check style with ruff
make format        # auto-format code
make sync          # lock & sync dependencies
make clean         # remove build artifacts
make dev-install   # install in editable mode with dev deps
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `globus-sdk` >= 3.0 | Globus Auth, Transfer, Flows APIs |
| `globus-compute-sdk` >= 2.0 | Remote function execution on Globus Compute endpoints |
| `pyyaml` >= 6.0 | YAML configuration parsing |
| `watchdog` >= 3.0 | Filesystem monitoring for trigger-file detection |
| `wandb` >= 0.15 | Weights & Biases integration for training progress |

## License

TBD
