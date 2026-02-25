#!/usr/bin/env python3
import argparse
import sys
import os
import json
import globus_sdk
from globus_compute_sdk import Client, Executor

#TODO:
# Add ALCF directory clean up
# Incorporate to monitor script for a file named kill_flow_run_{id}

TOKEN_FILE = os.path.expanduser("./.globus_tokens.json")
CLIENT_ID = "f600d0cc-fb3b-4dd8-9284-13c20be841be"
ENDPOINT_ID = "60e69085-5bd0-43a2-8d4e-e0e216181d02"

# Functions
def get_authorizer(client):
    """Loads tokens from disk or performs a new login."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            tokens = json.load(f)
        
        # Use the refresh token to keep the session alive indefinitely
        return globus_sdk.RefreshTokenAuthorizer(
            tokens["flows.globus.org"]["refresh_token"],
            client,
            access_token=tokens["flows.globus.org"]["access_token"],
            expires_at=tokens["flows.globus.org"]["expires_at_seconds"]
        )

    # If no token file, do the browser login flow
    scopes = [
        globus_sdk.FlowsClient.scopes.manage_flows,
        globus_sdk.FlowsClient.scopes.run_manage,
        globus_sdk.FlowsClient.scopes.view_flows,
        globus_sdk.FlowsClient.scopes.run_status,
        "offline_access" # Required to get a refresh_token
    ]
    
    client.oauth2_start_flow(requested_scopes=scopes, refresh_tokens=True)
    print(f"Please login here:\n{client.oauth2_get_authorize_url()}\n")
    auth_code = input("Enter the auth code: ").strip()
    
    token_response = client.oauth2_exchange_code_for_tokens(auth_code)
    
    # Save tokens to disk for next time
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_response.by_resource_server, f)
        
    return globus_sdk.RefreshTokenAuthorizer(
        token_response.by_resource_server["flows.globus.org"]["refresh_token"],
        client
    )


def delete_flow(client_id: str, flow_id: str) -> None:
    """Deletes a Flow definition."""
    fc = authenticate_flows_client(client_id, flow_id)
    fc.delete_flow(flow_id)
    print(f"Successfully deleted Flow ID: {flow_id}")

def cancel_run(client_id: str, flow_id: str, run_id: str) -> None:
    """Cancels an active Flow Run."""
    fc = authenticate_flows_client(client_id, flow_id)


# Globus compute function
def run_terminal_command(command_pbs_job_script):
    import subprocess
    try:
        # Executes the command and captures the output
        result = subprocess.run(
            command_pbs_job_script,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)

def kill_all_pbs_jobs(user: str, queue: str) -> None:
    """ Kill all the jobs in PBS queue corresponding to a user """
    cmd = f"qselect -q {queue} -u {user} | xargs qdel"

    # Initialize the Client
    # This will prompt for a login if you haven't authenticated on this machine
    gc_executor = Executor(endpoint_id=ENDPOINT_ID)

    print(f"Submitting task to endpoint: {ENDPOINT_ID}...")
    
    # Submit the function
    #future = gc_executor.submit(hello_world)
    future = gc_executor.submit(run_terminal_command, [cmd])

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
    authorizer = get_authorizer(native_client)
    
    flows_client = globus_sdk.FlowsClient(authorizer=authorizer)
    
    try:
        if args.run_id:
            flows_client.cancel_run(args.run_id)
            print(f"Successfully cancelled Run ID: {args.run_id}")
            kill_all_pbs_jobs(user='bicer', queue='demand')
        else:
            print(f"Unable to cancel Run ID: {args.run_id}")
            pass
    except globus_sdk.GlobusAPIError as e:
        print(f"Globus API Error: {e.http_status} - {e.message}", file=sys.stderr)
        sys.exit(1)
