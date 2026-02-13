# Flows

Globus Flows definitions and automation scripts.

## Structure

- `definitions/` — Flow definition JSON files
- `actions/` — Custom action provider implementations
- `deploy.py` — Utility to register/update flows with the Globus service

## Usage

1. Define your flow in `definitions/` as a JSON file following the
   [Globus Flows schema](https://docs.globus.org/api/flows/).
2. Use `deploy.py` to register or update the flow.
3. Trigger runs via the scripts in `scripts/` or programmatically through the SDK.
