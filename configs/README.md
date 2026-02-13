# Configs

Configuration files for Globus endpoints, collections, and workflow parameters.

## Structure

- `endpoints.yaml` — Endpoint and collection mappings
- `flow_inputs/` — Input schema templates for flow runs
- `local/` — Local overrides (gitignored)

## Notes

- Copy `.env.example` to `.env` and fill in credentials before running workflows.
- Do **not** commit secrets or tokens to this directory.
- Compute folder includes the compute end-point configuration file. This is a simple configuration since the compute workers simply submit job scripts to a local Slurm/PBS cluster.

