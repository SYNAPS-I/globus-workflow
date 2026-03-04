import os
import sys
import json
import logging
import argparse
import time
import globus_sdk
from globus_sdk import GlobusAPIError

# Allow imports from the flows/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "flows"))
from utils import load_config
from globus_auth import get_authorizer

# 1. Configuration (from flow_config.yaml)
CONFIG = load_config()
CLIENT_ID = CONFIG["globus"]["native_app_client_id"]
TOKEN_FILE = CONFIG["globus"]["token_file"]
RUN_ID = CONFIG["globus"]["default_run_id"]

# Status Check Configuration
POLL_INTERVAL_SECONDS = CONFIG["monitoring"]["poll_interval_seconds"]
TERMINAL_STATES = set(CONFIG["monitoring"]["terminal_states"])



# Setup logging for professional, direct reporting
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Run ID: %(run_id)s; Status: %(status)s; %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)



# Functions
def monitor_flow_run(run_id: str):
    """
    Continuously polls a Globus Flow run and reports its status to stdout.
    Stops execution when the flow reaches a terminal state.
    """
    previous_status = None

    native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    authorizer = get_authorizer(native_client, TOKEN_FILE)
    
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
    authorizer = get_authorizer(native_client, TOKEN_FILE)
    
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

