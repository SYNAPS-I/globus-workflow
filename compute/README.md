# Compute

Globus Compute (formerly funcX) function definitions and endpoint configurations.

## Structure

- `functions/` — Python functions to be registered with Globus Compute
- `endpoints/` — Endpoint configuration files
- `register.py` — Utility to register functions with Globus Compute

## Usage

Define functions in `functions/`, then register them:

```bash
python compute/register.py --function functions/my_function.py
```
