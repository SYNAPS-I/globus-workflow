# globus-workflow

Globus workflow components and scripts for the SYNAPS-I project. This repository
organizes reusable building blocks for data transfer, remote computation, and
automated flow orchestration using the [Globus](https://www.globus.org/) platform.

## Repository Structure

```
globus-workflow/
├── configs/                # Configuration files
│   ├── endpoints.yaml      # Endpoint / collection mappings
│   └── flow_inputs/        # Input templates for flow runs
├── flows/                  # Globus Flows
│   └── definitions/        # Flow definition JSON files
├── compute/                # Globus Compute functions & endpoint configs
│   └── functions/          # Python functions for remote execution
├── scripts/                # Standalone CLI scripts
├── utils/                  # Shared Python helpers (auth, transfer, …)
├── tests/                  # Test suite
├── examples/               # Usage examples & sample pipelines
├── docs/                   # Documentation & architecture notes
├── .env.example            # Environment variable template
├── pyproject.toml          # Python packaging & tool config
└── Makefile                # Common dev commands
```

## Quick Start

1. **Clone the repo**
   ```bash
   git clone https://github.com/SYNAPS-I/globus-workflow.git
   cd globus-workflow
   ```

2. **Install [uv](https://docs.astral.sh/uv/)** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies** (creates a virtualenv automatically)
   ```bash
   uv sync --group dev
   ```

4. **Configure credentials**
   ```bash
   cp .env.example .env
   # Fill in your Globus client ID, secret, and endpoint UUIDs
   ```

5. **Run a transfer**
   ```bash
   uv run python scripts/transfer.py \
       --source <SOURCE_ENDPOINT> \
       --dest <DEST_ENDPOINT> \
       --source-path /data/ \
       --dest-path /output/ \
       --wait
   ```

## Development

```bash
make lint       # check style (ruff check + ruff format --check)
make format     # auto-format  (ruff check --fix + ruff format)
make test       # run tests    (pytest via uv run)
make sync       # lock & sync dependencies
```

All `make` targets use `uv run` so you don't need to activate the virtualenv manually.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `globus-sdk` | Globus Auth, Transfer, Groups APIs |
| `globus-compute-sdk` | Remote function execution |
| `globus-automate-client` | Flows / automation |
| `pyyaml` | Config file parsing |
| `python-dotenv` | `.env` file loading |

## License

See [LICENSE](LICENSE) for details.
