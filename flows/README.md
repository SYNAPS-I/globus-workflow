# Flows

Globus Flows definitions and automation scripts for ptychography fine-tuning.

## Structure

| File | Description |
|---|---|
| `flow_config.yaml` | Unified configuration (endpoints, paths, PBS, W&B, monitoring, deployed IDs) |
| `flow.json` | Globus Flow definition (state machine) |
| `utils.py` | Shared helpers — `load_config()`, `run_terminal_command()` |
| `globus_auth.py` | Globus OAuth token management — `get_authorizer()` |
| `deploy.py` | **Deployment** — registers Flow & Compute functions, writes IDs to config |
| `monitor_folder_flow_init.py` | **Entry point** — watches a directory and triggers the workflow |
| `sample_flow.py` | **Execution** — runs a previously deployed Globus Flow |
| `globus_flow_status.py` | Polls a running Flow and logs status to file |
| `globus_flow_run_cancel.py` | Cancels an active Flow run and kills PBS jobs |
| `pbs_queue_check.py` | Checks PBS queue status via Globus Compute |
| `query_epoch_number_w_total.py` | Queries current epoch from Weights & Biases |

## Workflow

```
monitor_folder_flow_init.py   (watches for trigger file)
  ├── sample_flow.py           (runs the deployed Globus Flow)
  └── globus_flow_status.py    (monitors the running Flow)
        ├── pbs_queue_check.py            (checks PBS job state)
        └── query_epoch_number_w_total.py (queries W&B epoch)
```

## Configuration

All scripts read from a single `flow_config.yaml`. Key sections:

- **`globus`** — client IDs, app name, token file, flow/run IDs
- **`endpoints`** — Globus collection and compute endpoint IDs
- **`paths`** — source/destination transfer paths
- **`flow`** — flow definition file, title, PBS/prune commands
- **`deployment`** — deployed Compute function IDs (written by `deploy.py`)
- **`pbs`** — PBS user, queue, tail lines
- **`monitoring`** — polling, log directories, folder watcher settings
- **`wandb`** — W&B entity, project, API key

## Usage

1. Edit `flow_config.yaml` with your endpoint IDs, paths, and credentials.
2. Deploy the flow and compute functions (one-time, or when definitions change):
   ```bash
   python deploy.py --all
   ```
   This registers the Flow and Compute functions with Globus and writes the
   resulting IDs back into `flow_config.yaml` under `globus.flow_id` and
   `deployment.*`.
3. Start the folder watcher:
   ```bash
   python monitor_folder_flow_init.py
   ```
4. To manually run a flow:
   ```bash
   python sample_flow.py
   ```
5. To cancel an active run:
   ```bash
   python globus_flow_run_cancel.py --run-id <RUN_UUID>
   ```
