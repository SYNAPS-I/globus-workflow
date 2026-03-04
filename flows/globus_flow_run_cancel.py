#!/usr/bin/env python3
import argparse
import sys
import os
import json
import globus_sdk
from globus_compute_sdk import Client, Executor
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from globus_auth import get_authorizer
from utils import load_config

#TODO:
# Add ALCF directory clean up
# Incorporate to monitor script for a file named kill_flow_run_{id}

# Load configuration from YAML
CONFIG = load_config()

TOKEN_FILE = CONFIG["globus"]["token_file"]
CLIENT_ID = CONFIG["globus"]["native_app_client_id"]
ENDPOINT_ID = CONFIG["endpoints"]["compute_endpoint_id"]

# Functions
def delete_flow(client_id: str, flow_id: str) -> None:
    """Deletes a Flow definition."""
    fc = authenticate_flows_client(client_id, flow_id)
    fc.delete_flow(flow_id)
    print(f"Successfully deleted Flow ID: {flow_id}")

def cancel_run(client_id: str, flow_id: str, run_id: str) -> None:
    """Cancels an active Flow Run."""
    fc = authenticate_flows_client(client_id, flow_id)


def kill_all_pbs_jobs(user: str, queue: str) -> None:
    """ Kill all the jobs in PBS queue corresponding to a user """
    cmd = f"qselect -q {queue} -u {user} | xargs qdel"

    def _run_command(command: str) -> str:
        """Execute a shell command (self-contained for remote serialization)."""
        import subprocess
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return str(e)

    # Initialize the Client
    gc_executor = Executor(endpoint_id=ENDPOINT_ID)
    gc_executor.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())

    print(f"Submitting task to endpoint: {ENDPOINT_ID}...")
    
    # Submit the function
    future = gc_executor.submit(_run_command, cmd)

    # Get the result
    try:
        result = future.result()
        #print(f"Success! Result: {result}")
        if result != "": print(result)
        #print(f"{result.split()[-2]}")
    except Exception as e:
        print(f"Task failed: {e}")

    c_executor = Executor(endpoint_id=ENDPOINT_ID)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminate a Globus Flow definition or an active Flow Run.")
    #parser.add_argument("--flow-id", required=True, help="UUID of the Flow definition (required for auth scope)")
    parser.add_argument("--run-id", help="UUID of the active Flow Run to cancel. If omitted, deletes the Flow.")

    
    args = parser.parse_args()

    native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    authorizer = get_authorizer(native_client, TOKEN_FILE)
    
    flows_client = globus_sdk.FlowsClient(authorizer=authorizer)
    
    try:
        if args.run_id:
            flows_client.cancel_run(args.run_id)
            print(f"Successfully cancelled Run ID: {args.run_id}")
            kill_all_pbs_jobs(user=CONFIG["pbs"]["user"], queue=CONFIG["pbs"]["queue"])
        else:
            print(f"Unable to cancel Run ID: {args.run_id}")
            pass
    except globus_sdk.GlobusAPIError as e:
        print(f"Globus API Error: {e.http_status} - {e.message}", file=sys.stderr)
        sys.exit(1)
