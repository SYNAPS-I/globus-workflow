"""Test that the Globus Compute endpoint is online and responsive,
and that deployed compute functions exist and are callable."""

import sys
import os

import pytest
from globus_compute_sdk import Client

# Allow imports from the flows/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flows"))
from utils import load_config


CONFIG = load_config()
ENDPOINT_ID = CONFIG["endpoints"]["compute_endpoint_id"]
DEPLOYMENT = CONFIG["deployment"]

# Collect all deployed function IDs as (name, func_id) pairs
DEPLOYED_FUNCTIONS = [
    (name, func_id)
    for name, func_id in DEPLOYMENT.items()
    if func_id is not None
]


@pytest.fixture(scope="module")
def gc_client():
    """Return an authenticated Globus Compute client."""
    return Client()


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


def test_endpoint_is_online(gc_client):
    """Verify the Globus Compute endpoint reports an 'online' status."""
    status = gc_client.get_endpoint_status(ENDPOINT_ID)
    assert status["status"] == "online", (
        f"Endpoint {ENDPOINT_ID} is not online. Status: {status['status']}"
    )


def test_endpoint_can_execute(gc_client):
    """Submit a trivial function and confirm it returns a result."""
    from globus_compute_sdk import Executor
    from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies

    def _hello():
        import platform
        return f"Hello from {platform.node()}"

    with Executor(endpoint_id=ENDPOINT_ID, client=gc_client) as gce:
        gce.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
        future = gce.submit(_hello)
        result = future.result(timeout=60)

    assert result.startswith("Hello from"), f"Unexpected result: {result}"


# ---------------------------------------------------------------------------
# Deployed compute function tests
# ---------------------------------------------------------------------------


def test_all_function_ids_are_set():
    """Verify every deployment entry in flow_config.yaml has a non-null ID."""
    missing = [name for name, func_id in DEPLOYMENT.items() if func_id is None]
    assert not missing, (
        f"The following functions have no deployed ID: {missing}. "
        "Run deploy.py to register them."
    )


@pytest.mark.parametrize("func_name,func_id", DEPLOYED_FUNCTIONS)
def test_function_is_registered(gc_client, func_name, func_id):
    """Verify each deployed function ID is registered with Globus Compute."""
    result = gc_client.get_function(func_id)
    assert result is not None, (
        f"Function '{func_name}' ({func_id}) not found in Globus Compute."
    )
    assert "function_uuid" in result, (
        f"Function '{func_name}' ({func_id}) returned unexpected data: {result}"
    )


# ---------------------------------------------------------------------------
# Execute pi_calc on the remote endpoint
# ---------------------------------------------------------------------------


def test_pi_calc_executes(gc_client):
    """Run pi_calc on the remote endpoint and verify it returns a sane estimate.

    Submits the function directly with AllCodeStrategies (source-based
    serialization) to avoid deserialization issues caused by Python version
    mismatches between the local SDK and the endpoint workers.
    """
    from globus_compute_sdk import Executor
    from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies

    def pi_calc(num_points=1_000):
        """Monte-Carlo estimate of pi."""
        from random import random

        inside = 0
        for _ in range(num_points):
            x, y = random(), random()
            if x * x + y * y < 1:
                inside += 1
        return inside * 4 / num_points

    with Executor(endpoint_id=ENDPOINT_ID, client=gc_client) as gce:
        gce.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
        future = gce.submit(pi_calc, num_points=1_000)
        result = future.result(timeout=120)

    assert isinstance(result, float), f"Expected float, got {type(result)}: {result}"
    # With 1k points the estimate is rough — just verify it's in a sane range
    assert 2.0 < result < 4.0, (
        f"pi_calc returned {result}, expected a value between 2.0 and 4.0"
    )


# ---------------------------------------------------------------------------
# Execute the *deployed* pi_calc function by its registered ID
# ---------------------------------------------------------------------------


def test_deployed_pi_calc_executes(gc_client):
    """Invoke the deployed pi_calc function via its registered ID and verify the result."""
    from globus_compute_sdk import Executor

    func_id = DEPLOYMENT.get("func_id_pi_calc")
    assert func_id is not None, "func_id_pi_calc is not set in flow_config.yaml"

    with Executor(endpoint_id=ENDPOINT_ID, client=gc_client) as gce:
        future = gce.submit_to_registered_function(
            function_id=func_id, kwargs={"num_points": 1_000}
        )
        result = future.result(timeout=120)

    assert isinstance(result, float), f"Expected float, got {type(result)}: {result}"
    assert 2.0 < result < 4.0, (
        f"Deployed pi_calc returned {result}, expected a value between 2.0 and 4.0"
    )


# ---------------------------------------------------------------------------
# Python version compatibility
# ---------------------------------------------------------------------------


def test_python_version_match(gc_client):
    """Verify the local Python major.minor matches the endpoint workers."""
    from globus_compute_sdk import Executor
    from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies

    def _get_remote_version():
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}"

    local_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    with Executor(endpoint_id=ENDPOINT_ID, client=gc_client) as gce:
        gce.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
        future = gce.submit(_get_remote_version)
        remote_version = future.result(timeout=60)

    assert local_version == remote_version, (
        f"Python version mismatch: local={local_version}, endpoint={remote_version}. "
        "This may cause serialization errors with the default DillCodeSource strategy."
    )