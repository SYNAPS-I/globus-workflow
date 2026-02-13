# Scripts

Standalone scripts for common Globus operations.

## Contents

| Script | Description |
|--------|-------------|
| `transfer.py` | Submit a Globus Transfer task |
| `run_flow.py` | Trigger a Globus Flow run |
| `check_status.py` | Check status of a transfer or flow run |
| `list_endpoints.py` | List accessible Globus endpoints |

## Usage

```bash
# Example: submit a transfer
python scripts/transfer.py --source <endpoint_id> --dest <endpoint_id> --path /data/
```
