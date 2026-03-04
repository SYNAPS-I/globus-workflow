"""Globus token management utilities.

Provides helpers to load cached OAuth tokens from disk or run the
browser-based login flow and persist the resulting tokens for reuse.

Supports both authentication paradigms used in the project:
- **NativeAppAuthClient** (``get_authorizer``): for ``globus_flow_status.py``
  and ``globus_flow_run_cancel.py``.
- **UserApp** (``get_user_app``): for ``sample_flow.py``, ``deploy.py``, and
  test files.

Checks both the config-defined token path and the default Globus CLI
path (``~/.globus/tokens.json``) when looking for cached tokens.
"""

import json
import os
from pathlib import Path

import globus_sdk
from globus_sdk.globus_app import UserApp
from globus_sdk.scopes import (
    TransferScopes,
    FlowsScopes,
    ComputeScopes,
    GCSCollectionScopeBuilder,
    MutableScope,
)


# Default Globus CLI token storage path
DEFAULT_GLOBUS_TOKENS_FILE = Path.home() / ".globus" / "tokens.json"

# Directory containing this module (flows/) — used to resolve relative paths
_FLOWS_DIR = Path(__file__).resolve().parent


def _resolve_token_path(token_file: str | Path) -> Path:
    """Resolve a token file path.

    Absolute paths and ``~``-prefixed paths are expanded directly.
    Relative paths (like ``./. globus_tokens.json``) are resolved relative
    to the ``flows/`` directory so the result is independent of the working
    directory the script was launched from.
    """
    p = Path(os.path.expanduser(str(token_file)))
    if p.is_absolute():
        return p
    return (_FLOWS_DIR / p).resolve()

# Default scopes — superset used across all scripts
DEFAULT_SCOPES = [
    globus_sdk.FlowsClient.scopes.manage_flows,
    globus_sdk.FlowsClient.scopes.run_manage,
    globus_sdk.FlowsClient.scopes.view_flows,
    globus_sdk.FlowsClient.scopes.run_status,
    "offline_access",  # Required to get a refresh_token
]


def _find_token_file(token_file: str | Path | None = None) -> Path | None:
    """Search for an existing token file in order of priority.

    1. Explicit *token_file* argument (from config).
    2. Default Globus CLI token path (``~/.globus/tokens.json``).

    Returns the first path that exists, or ``None``.
    """
    candidates: list[Path] = []
    if token_file is not None:
        candidates.append(_resolve_token_path(token_file))
    candidates.append(DEFAULT_GLOBUS_TOKENS_FILE)

    for path in candidates:
        if path.is_file():
            return path
    return None


def _load_tokens(token_file: Path) -> dict | None:
    """Load and return token data from a JSON file, or ``None`` on failure."""
    try:
        with open(token_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_token_locations(config_token_file: str | Path | None = None) -> dict:
    """Return a dict summarising all known token file locations and their status.

    Useful for diagnostics and tests.

    Returns
    -------
    dict
        Keys are descriptive names, values are dicts with ``path`` and ``exists``.
    """
    locations: dict[str, dict] = {}

    if config_token_file is not None:
        p = _resolve_token_path(config_token_file)
        locations["config_token_file"] = {"path": p, "exists": p.is_file()}

    locations["default_globus_tokens"] = {
        "path": DEFAULT_GLOBUS_TOKENS_FILE,
        "exists": DEFAULT_GLOBUS_TOKENS_FILE.is_file(),
    }

    return locations


def get_authorizer(
    client: globus_sdk.NativeAppAuthClient,
    token_file: str,
    scopes: list[str] | None = None,
) -> globus_sdk.RefreshTokenAuthorizer:
    """Return a RefreshTokenAuthorizer, loading cached tokens when available.

    Searches for cached tokens at the *token_file* path (from config) first,
    then falls back to the default Globus CLI path (``~/.globus/tokens.json``).

    Parameters
    ----------
    client:
        An already-instantiated ``NativeAppAuthClient``.
    token_file:
        Path to the JSON file used to cache tokens between sessions.
    scopes:
        OAuth scopes to request.  Falls back to ``DEFAULT_SCOPES``.
    """
    if scopes is None:
        scopes = DEFAULT_SCOPES

    # Where to save new tokens (always use the config-defined path)
    save_path = _resolve_token_path(token_file)

    # Check both config path and default Globus CLI path
    existing = _find_token_file(token_file)
    if existing is not None:
        tokens = _load_tokens(existing)
        if tokens and "flows.globus.org" in tokens:
            return globus_sdk.RefreshTokenAuthorizer(
                tokens["flows.globus.org"]["refresh_token"],
                client,
                access_token=tokens["flows.globus.org"]["access_token"],
                expires_at=tokens["flows.globus.org"]["expires_at_seconds"],
            )

    # No cached tokens — run the interactive browser login flow
    client.oauth2_start_flow(requested_scopes=scopes, refresh_tokens=True)
    print(f"Please login here:\n{client.oauth2_get_authorize_url()}\n")
    auth_code = input("Enter the auth code: ").strip()

    token_response = client.oauth2_exchange_code_for_tokens(auth_code)

    # Persist tokens for next time
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(token_response.by_resource_server, f)

    return globus_sdk.RefreshTokenAuthorizer(
        token_response.by_resource_server["flows.globus.org"]["refresh_token"],
        client,
    )


# ---------------------------------------------------------------------------
# UserApp-based authentication (sample_flow.py, deploy.py, tests)
# ---------------------------------------------------------------------------


def build_transfer_scope(config: dict) -> MutableScope:
    """Build a transfer scope with ``data_access`` dependencies.

    Parameters
    ----------
    config:
        The loaded ``flow_config.yaml`` dict.

    Returns
    -------
    MutableScope
        A ``TransferScopes.all`` scope with ``data_access`` dependencies for
        both source and destination collections.
    """
    src = config["endpoints"]["source_collection_id"]
    dst = config["endpoints"]["dest_collection_id"]

    transfer_scope = MutableScope(TransferScopes.all)
    transfer_scope.add_dependency(GCSCollectionScopeBuilder(src).data_access)
    transfer_scope.add_dependency(GCSCollectionScopeBuilder(dst).data_access)
    return transfer_scope


def build_scope_requirements(config: dict) -> dict:
    """Build the default scope requirements for the project.

    Includes Transfer (with ``data_access``), Flows, and Compute scopes.

    Parameters
    ----------
    config:
        The loaded ``flow_config.yaml`` dict.
    """
    transfer_scope = build_transfer_scope(config)
    return {
        TransferScopes.resource_server: [transfer_scope],
        FlowsScopes.resource_server: [FlowsScopes.all],
        ComputeScopes.resource_server: [ComputeScopes.all],
    }


def get_user_app(
    config: dict,
    scope_requirements: dict | None = None,
) -> UserApp:
    """Create and return a ``UserApp`` for Globus SDK clients.

    Parameters
    ----------
    config:
        The loaded ``flow_config.yaml`` dict.
    scope_requirements:
        Optional override for the OAuth scope requirements dict.  When
        ``None`` (default), :func:`build_scope_requirements` is used to
        build a scope set covering Transfer, Flows, and Compute.

    Returns
    -------
    UserApp
        An authenticated ``UserApp`` that can be passed to any Globus SDK
        client (``FlowsClient``, ``TransferClient``, ``SpecificFlowClient``,
        etc.).
    """
    if scope_requirements is None:
        scope_requirements = build_scope_requirements(config)

    return UserApp(
        config["globus"]["app_name"],
        client_id=config["globus"]["client_id"],
        scope_requirements=scope_requirements,
    )
