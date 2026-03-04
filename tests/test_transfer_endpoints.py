"""Test that the Globus Transfer endpoints (collections) defined in
flow_config.yaml are accessible and operational."""

import sys
import os

import pytest
import globus_sdk

# Allow imports from the flows/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flows"))
from utils import load_config
from globus_auth import get_user_app


CONFIG = load_config()
SOURCE_COLLECTION_ID = CONFIG["endpoints"]["source_collection_id"]
DEST_COLLECTION_ID = CONFIG["endpoints"]["dest_collection_id"]
SOURCE_PATH = CONFIG["paths"]["source_path"]
DEST_PATH = CONFIG["paths"]["dest_path"]

COLLECTIONS = [
    ("source", SOURCE_COLLECTION_ID, SOURCE_PATH),
    ("dest", DEST_COLLECTION_ID, DEST_PATH),
]


@pytest.fixture(scope="module")
def transfer_client():
    """Return an authenticated Globus TransferClient with data_access on both collections."""
    app = get_user_app(CONFIG)
    return globus_sdk.TransferClient(app=app)


# ---------------------------------------------------------------------------
# Collection availability
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,collection_id,_path", COLLECTIONS)
def test_collection_exists(transfer_client, label, collection_id, _path):
    """Verify each collection ID resolves to a valid Globus endpoint/collection."""
    response = transfer_client.get_endpoint(collection_id)
    assert response is not None, (
        f"{label} collection {collection_id} not found."
    )
    display_name = response.get("display_name", "(unnamed)")
    assert response["id"] == collection_id, (
        f"Returned ID mismatch for {label}: expected {collection_id}, "
        f"got {response['id']}"
    )
    print(f"  {label}: {display_name} ({collection_id})")


@pytest.mark.parametrize("label,collection_id,_path", COLLECTIONS)
def test_collection_is_active(transfer_client, label, collection_id, _path):
    """Verify each collection is not paused or inactive."""
    response = transfer_client.get_endpoint(collection_id)

    # GCSv5 mapped collections may not have 'activated'; skip that check
    # but verify the endpoint is not explicitly disabled/paused.
    is_paused = False
    paused_rules = response.get("pause_rules") or response.data.get("pause_rules")
    if paused_rules:
        is_paused = len(paused_rules) > 0

    assert not is_paused, (
        f"{label} collection {collection_id} has active pause rules: {paused_rules}"
    )


# ---------------------------------------------------------------------------
# Directory listing (proves data_access consent + path validity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,collection_id,path", COLLECTIONS)
def test_can_list_directory(transfer_client, label, collection_id, path):
    """Verify the configured path is listable on each collection.

    This proves:
    1. The collection is reachable.
    2. The authenticated user has data_access consent.
    3. The configured path exists on the collection.
    """
    try:
        response = transfer_client.operation_ls(collection_id, path=path)
    except globus_sdk.TransferAPIError as e:
        pytest.fail(
            f"Cannot list {label} path '{path}' on {collection_id}: {e.message}"
        )

    # operation_ls returns an iterable of entries; just confirm it didn't error
    entries = list(response)
    assert isinstance(entries, list), (
        f"Unexpected response type from ls on {label}: {type(entries)}"
    )
    print(f"  {label}: {path} contains {len(entries)} entries")
