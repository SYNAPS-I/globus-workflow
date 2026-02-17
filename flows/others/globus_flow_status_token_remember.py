import os
import json
import logging
import argparse
import time
import globus_sdk
from globus_sdk import GlobusAPIError


# 1. Configuration
CLIENT_ID = "f600d0cc-fb3b-4dd8-9284-13c20be841be"
RUN_ID = "9e848ee5-90d3-47f2-8e95-de77f6195f3c"
TOKEN_FILE = os.path.expanduser("./.globus_tokens.json")

# Status Check Configuration
POLL_INTERVAL_SECONDS = 5
TERMINAL_STATES = {"SUCCEEDED", "FAILED"}



# Setup logging for professional, direct reporting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Run ID: %(run_id)s; Status: %(status)s; %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)



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

def monitor_flow_run(run_id: str):
    """
    Continuously polls a Globus Flow run and reports its status to stdout.
    Stops execution when the flow reaches a terminal state.
    """
    previous_status = None

    native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    authorizer = get_authorizer(native_client)
    
    flows_client = globus_sdk.FlowsClient(authorizer=authorizer)

    try:
        while True:
            # Fetch current run details
            try:
                run = flows_client.get_run(run_id)
                status = run["status"]
                
                # Report status
                # Option A: Report only on state change (less noisy)
                if status != previous_status:
                    logger.info(f"State transition detected: {previous_status} -> {status}", extra={"run_id": run_id, "status": status})
                    previous_status = status

                # Option B: Report heartbeat (uncomment if continuous "alive" signals are needed)
                # logger.info("Monitoring...", extra={"run_id": run_id, "status": status})

                # Check for terminal state
                if status in TERMINAL_STATES:
                    if status == "FAILED":
                        # Retrieve run logs for failure details
                        log_entries = flows_client.get_run_logs(run_id, limit=1)
                        details = log_entries.data['entries'][0].get('details', 'No details available')
                        logger.error(f"Flow failed. Reason: {details}", extra={"run_id": run_id, "status": status})
                    else:
                        logger.info("Flow completed successfully.", extra={"run_id": run_id, "status": status})
                    break

            except GlobusAPIError as e:
                # Handle transient network or API errors gracefully
                logger.warning(f"API Error during poll: {e.message}", extra={"run_id": run_id, "status": "UNKNOWN"})

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        sys.stdout.write("\n")
        logger.info("Monitoring stopped by user.", extra={"run_id": run_id, "status": "ABORTED"})


def get_flow_state_3_65(run_id):
    native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    authorizer = get_authorizer(native_client)
    
    flows_client = globus_sdk.FlowsClient(authorizer=authorizer)

    try:
        run = flows_client.get_run(run_id).data
        print(f"\n--- Run json: {run}) ---")

        print(f"\n--- Flow: {run.get('flow_title', 'N/A')} ({run['status']}) ---")
        
        log_response = flows_client.get_run_logs(run_id)
        print("\n--- State History ---")
        for entry in log_response.data.get('entries', []):
            print(entry)
            #timestamp = entry.get('time', 'Unknown')
            #state = entry.get('state_name', 'FLOW_LEVEL')
            #event = entry.get('event_type', 'Unknown')
            #print(f"[{timestamp}] {state.ljust(20)} -> {event}")

    except globus_sdk.FlowsAPIError as e:
        print(f"Flows API Error: {e.message}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor the status of a Globus Flow run.")
    parser.add_argument("run_id", type=str, nargs='?', default="9e848ee5-90d3-47f2-8e95-de77f6195f3c", help="The UUID of the Globus Flow run to monitor")
    args = parser.parse_args()

    run_id = args.run_id
    #get_flow_state_3_65(run_id)
    monitor_flow_run(run_id)

