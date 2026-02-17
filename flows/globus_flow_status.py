import os
import sys
import json
import logging
import argparse
import time
import datetime
import globus_sdk
from globus_sdk import GlobusAPIError


# 1. Configuration
CLIENT_ID = "f600d0cc-fb3b-4dd8-9284-13c20be841be"
RUN_ID = "9e848ee5-90d3-47f2-8e95-de77f6195f3c"
TOKEN_FILE = os.path.expanduser("./.globus_tokens.json")

# Status Check Configuration
POLL_INTERVAL_SECONDS = 5
TERMINAL_STATES = {"SUCCEEDED", "FAILED"}

# Logger setup
logger = logging.getLogger(__name__)

def setup_logging(log_filename):
    """Configures logging handlers with a dynamic filename."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] Run ID: %(run_id)s; Status: %(status)s; %(message)s",
        datefmt="%H:%M:%S",
        # force=True is required if you accidentally called basicConfig elsewhere
        force=True, 
        handlers=[
            logging.FileHandler(log_filename), # Dynamic filename
            logging.StreamHandler(sys.stdout)  # Console output
        ]
    )


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

def get_flow_state_3_65(run_id):
    native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    authorizer = get_authorizer(native_client)
    
    flows_client = globus_sdk.FlowsClient(authorizer=authorizer)

    try:
        while True:
            try:
                run = flows_client.get_run(run_id).data
                flow_status = run["status"]

                if flow_status in TERMINAL_STATES:
                    if flow_status == "FAILED":
                        # Retrieve run logs for failure details
                        log_entries = flows_client.get_run_logs(run_id, limit=1)
                        details = log_entries.data['entries'][0].get('details', 'No details available')
                        logger.error(f"Flow failed. Reason: {details}", extra={"run_id": run_id, "status": flow_status})
                    else:
                        logger.info("Flow completed successfully.", extra={"run_id": run_id, "status": flow_status})
                    break

                if flow_status == "ACTIVE":
                    try:
                        for action in run["details"]["action_statuses"]:
                            field = action["state_name"]
                            logger.info(f"Current state: {field}", extra={"run_id": run_id, "status": flow_status})
                    except (KeyError, TypeError, IndexError):
                        # This block runs if any key is missing or if 'details' is None
                        pass
                time.sleep(3)

            except globus_sdk.FlowsAPIError as e:
                print(f"Flows API Error: {e.message}")


    except KeyboardInterrupt:
        sys.stdout.write("\n")
        logger.info("Monitoring stopped by user.", extra={"run_id": run_id, "status": "ABORTED"})



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor the status of a Globus Flow run.")
    parser.add_argument("run_id", type=str, nargs='?', default="9e848ee5-90d3-47f2-8e95-de77f6195f3c", help="The UUID of the Globus Flow run to monitor")
    args = parser.parse_args()

    run_id = args.run_id

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"flow_{timestamp}_{run_id}.log"
    setup_logging(f"/home/beams/TBICER/flow_ptycho_fine_tune/monitor/{log_file_name}")

    get_flow_state_3_65(run_id)
