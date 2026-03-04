"""Test that Globus OAuth tokens exist and are valid for accessing
the endpoints defined in flow_config.yaml.

Checks three token locations:
1. UserApp token file: ~/.globus/app/<client_id>/<app_name>/tokens.json
   (used by sample_flow.py, deploy.py via globus_sdk.UserApp)
2. Config token file: globus.token_file in flow_config.yaml
   (used by globus_flow_status.py, globus_flow_run_cancel.py via NativeAppAuthClient)
3. Default Globus CLI token file: ~/.globus/tokens.json
   (fallback location checked by globus_auth.py)
"""

import json
import sys
import os
import time
from pathlib import Path

import pytest
import globus_sdk

# Allow imports from the flows/ directory
FLOWS_DIR = Path(__file__).resolve().parent.parent / "flows"
sys.path.insert(0, str(FLOWS_DIR))
from utils import load_config
from globus_auth import (
    DEFAULT_GLOBUS_TOKENS_FILE,
    get_token_locations,
    get_user_app,
    _find_token_file,
)


CONFIG = load_config()
CLIENT_ID = CONFIG["globus"]["client_id"]
APP_NAME = CONFIG["globus"]["app_name"].lower()
SOURCE_COLLECTION_ID = CONFIG["endpoints"]["source_collection_id"]
DEST_COLLECTION_ID = CONFIG["endpoints"]["dest_collection_id"]

# --- Token location 1: UserApp token file ---
USERAPP_TOKEN_DIR = Path.home() / ".globus" / "app" / CLIENT_ID / APP_NAME
USERAPP_TOKEN_FILE = USERAPP_TOKEN_DIR / "tokens.json"

# --- Token location 2: Config-defined token file (NativeAppAuthClient) ---
_config_token_path = CONFIG["globus"].get("token_file", "")
if _config_token_path:
    CONFIG_TOKEN_FILE = (FLOWS_DIR / _config_token_path).resolve()
else:
    CONFIG_TOKEN_FILE = None

# Resource servers required for the workflow
REQUIRED_RESOURCE_SERVERS = [
    "auth.globus.org",
    "transfer.api.globus.org",
    "flows.globus.org",
    "funcx_service",
]

# Collect all known token locations for the discovery tests
ALL_TOKEN_LOCATIONS: dict[str, Path] = {}
ALL_TOKEN_LOCATIONS["userapp"] = USERAPP_TOKEN_FILE
if CONFIG_TOKEN_FILE:
    ALL_TOKEN_LOCATIONS["config"] = CONFIG_TOKEN_FILE
ALL_TOKEN_LOCATIONS["default_globus"] = DEFAULT_GLOBUS_TOKENS_FILE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_userapp_tokens() -> dict:
    """Load and return the token data from the UserApp token file."""
    with open(USERAPP_TOKEN_FILE) as f:
        raw = json.load(f)
    return raw.get("data", {}).get("DEFAULT", {})


def _load_config_tokens() -> dict:
    """Load and return the token data from the config-defined token file.

    This file uses the NativeAppAuthClient format:
    {resource_server: {access_token, refresh_token, expires_at_seconds, ...}}
    """
    with open(CONFIG_TOKEN_FILE) as f:
        return json.load(f)


# ===========================================================================
# Token location discovery tests
# ===========================================================================


class TestTokenDiscovery:
    """Verify that token-finding helpers work and at least one file exists."""

    def test_get_token_locations_includes_default(self):
        """get_token_locations() always includes the default Globus path."""
        locations = get_token_locations()
        assert "default_globus_tokens" in locations
        assert locations["default_globus_tokens"]["path"] == DEFAULT_GLOBUS_TOKENS_FILE

    def test_get_token_locations_includes_config(self):
        """get_token_locations() includes the config path when provided."""
        config_path = CONFIG["globus"].get("token_file", "")
        if not config_path:
            pytest.skip("No token_file defined in config")
        locations = get_token_locations(config_path)
        assert "config_token_file" in locations

    def test_at_least_one_token_file_exists(self):
        """At least one token file must exist for the workflows to work."""
        existing = {
            name: path for name, path in ALL_TOKEN_LOCATIONS.items() if path.is_file()
        }
        assert existing, (
            "No token files found in any location:\n"
            + "\n".join(f"  {n}: {p}" for n, p in ALL_TOKEN_LOCATIONS.items())
        )

    def test_find_token_file_returns_existing(self):
        """_find_token_file() returns an existing file (config or default)."""
        config_path = CONFIG["globus"].get("token_file", "")
        found = _find_token_file(config_path if config_path else None)
        if found is None:
            pytest.skip("No token file found at config or default path")
        assert found.is_file()


# ===========================================================================
# UserApp token file tests
# ===========================================================================


class TestUserAppTokens:
    """Tests for the UserApp token file (~/.globus/app/...)."""

    def test_token_file_exists(self):
        """Verify the UserApp token file exists on disk."""
        assert USERAPP_TOKEN_FILE.exists(), (
            f"UserApp token file not found at {USERAPP_TOKEN_FILE}. "
            "Run a Globus-authenticated script (e.g. sample_flow.py) to create it."
        )

    def test_token_file_is_valid_json(self):
        """Verify the UserApp token file is valid JSON with expected structure."""
        with open(USERAPP_TOKEN_FILE) as f:
            raw = json.load(f)

        assert "data" in raw, "Token file missing 'data' key"
        assert "DEFAULT" in raw["data"], "Token file missing 'data.DEFAULT' key"

    @pytest.mark.parametrize("resource_server", REQUIRED_RESOURCE_SERVERS)
    def test_token_exists_for_resource_server(self, resource_server):
        """Verify a token entry exists for each required resource server."""
        tokens = _load_userapp_tokens()
        assert resource_server in tokens, (
            f"No UserApp token for '{resource_server}'. Re-authenticate."
        )
        assert "access_token" in tokens[resource_server], (
            f"UserApp token for '{resource_server}' is missing 'access_token'."
        )

    @pytest.mark.parametrize("resource_server", REQUIRED_RESOURCE_SERVERS)
    def test_token_not_expired(self, resource_server):
        """Verify the UserApp access token has not expired."""
        tokens = _load_userapp_tokens()
        token_data = tokens.get(resource_server, {})
        expires_at = token_data.get("expires_at_seconds", 0)
        now = int(time.time())

        assert expires_at > now, (
            f"UserApp token for '{resource_server}' expired {now - expires_at}s ago. "
            "Re-authenticate."
        )


# ===========================================================================
# Config-defined token file tests (NativeAppAuthClient)
# ===========================================================================


# Only run these tests if token_file is defined in the config
_skip_config_tokens = CONFIG_TOKEN_FILE is None or not CONFIG_TOKEN_FILE.exists()
_skip_reason = (
    "Config token file not found"
    if CONFIG_TOKEN_FILE and not CONFIG_TOKEN_FILE.exists()
    else "No token_file defined in flow_config.yaml"
)


@pytest.mark.skipif(_skip_config_tokens, reason=_skip_reason)
class TestConfigTokens:
    """Tests for the config-defined token file (NativeAppAuthClient format)."""

    def test_token_file_is_valid_json(self):
        """Verify the config token file is valid JSON."""
        tokens = _load_config_tokens()
        assert isinstance(tokens, dict), "Config token file is not a JSON object"
        assert len(tokens) > 0, "Config token file is empty"

    def test_flows_token_exists(self):
        """Verify a flows.globus.org token exists (needed by status/cancel scripts)."""
        tokens = _load_config_tokens()
        assert "flows.globus.org" in tokens, (
            "Config token file missing 'flows.globus.org'. "
            "Run globus_flow_status.py to authenticate."
        )
        flow_token = tokens["flows.globus.org"]
        assert "access_token" in flow_token, "Missing access_token"
        assert "refresh_token" in flow_token, (
            "Missing refresh_token — token cannot be refreshed automatically."
        )

    def test_flows_token_not_expired(self):
        """Verify the flows token in the config file has not expired."""
        tokens = _load_config_tokens()
        flow_token = tokens.get("flows.globus.org", {})
        expires_at = flow_token.get("expires_at_seconds", 0)
        now = int(time.time())

        assert expires_at > now, (
            f"Config flows token expired {now - expires_at}s ago. "
            "Re-authenticate via globus_flow_status.py."
        )

    def test_all_expected_servers_present(self):
        """Check which resource servers have tokens in the config file."""
        tokens = _load_config_tokens()
        expected = ["flows.globus.org"]
        missing = [rs for rs in expected if rs not in tokens]
        assert not missing, f"Config token file missing: {missing}"


# ===========================================================================
# Default Globus CLI token file tests (~/.globus/tokens.json)
# ===========================================================================


class TestDefaultGlobusTokens:
    """Tests for the default Globus CLI token path (~/.globus/tokens.json)."""

    @pytest.fixture(autouse=True)
    def _require_default_tokens(self):
        if not DEFAULT_GLOBUS_TOKENS_FILE.is_file():
            pytest.skip(
                f"Default Globus token file not found: {DEFAULT_GLOBUS_TOKENS_FILE}"
            )

    def test_token_file_is_valid_json(self):
        """Verify the default token file is valid JSON."""
        with open(DEFAULT_GLOBUS_TOKENS_FILE) as f:
            data = json.load(f)
        assert isinstance(data, dict), "Default Globus token file is not a JSON object"

    def test_has_any_tokens(self):
        """Verify the default token file is not empty."""
        with open(DEFAULT_GLOBUS_TOKENS_FILE) as f:
            data = json.load(f)
        assert len(data) > 0, "Default Globus token file is empty"

    def test_flows_token_exists(self):
        """Check if a flows.globus.org token exists at the default path."""
        with open(DEFAULT_GLOBUS_TOKENS_FILE) as f:
            data = json.load(f)
        if "flows.globus.org" not in data:
            pytest.skip("No flows.globus.org token at default path")
        assert "access_token" in data["flows.globus.org"]


# ===========================================================================
# Functional token tests (make real API calls)
# ===========================================================================


@pytest.fixture(scope="module")
def user_app():
    """Return an authenticated UserApp with transfer + flows + compute scopes."""
    return get_user_app(CONFIG)


def test_transfer_token_works(user_app):
    """Verify the transfer token can make a successful API call."""
    tc = globus_sdk.TransferClient(app=user_app)
    # A lightweight call that requires a valid token
    response = tc.get_endpoint(SOURCE_COLLECTION_ID)
    assert response["id"] == SOURCE_COLLECTION_ID, (
        "Transfer token is invalid or cannot access the source collection."
    )


def test_flows_token_works(user_app):
    """Verify the flows token can retrieve flow status."""
    fc = globus_sdk.FlowsClient(app=user_app)
    flow_id = CONFIG["globus"]["flow_id"]
    try:
        response = fc.get_flow(flow_id)
        assert response["id"] == flow_id
    except globus_sdk.GlobusAPIError as e:
        pytest.fail(f"Flows token failed: {e.message}")
