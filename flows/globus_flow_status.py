import os
import subprocess
import sys
import json
import logging
import argparse
import time
import datetime
import globus_sdk
from globus_sdk import GlobusAPIError
from globus_compute_sdk import Client, Executor
from globus_auth import get_authorizer
from utils import load_config, run_local_terminal_command


# 1. Configuration — loaded from YAML
CONFIG = load_config()

CLIENT_ID = CONFIG["globus"]["native_app_client_id"]
RUN_ID = CONFIG["globus"]["default_run_id"]
TOKEN_FILE = CONFIG["globus"]["token_file"]
ENDPOINT_ID = CONFIG["endpoints"]["compute_endpoint_id"]
GC_EXECUTOR = Executor(endpoint_id=ENDPOINT_ID)

# Status Check Configuration
POLL_INTERVAL_SECONDS = CONFIG["monitoring"]["poll_interval_seconds"]
TERMINAL_STATES = set(CONFIG["monitoring"]["terminal_states"])

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
def get_queue_status():
    try:
        # Executes the command and captures the output
        result = subprocess.run(
            "python3 pbs_queue_check.py",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)
    


def get_flow_state_3_65(run_id):
    native_client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
    authorizer = get_authorizer(native_client, TOKEN_FILE)
    
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
                            log_str = f"Current state: {field}"

                            if field == "TriggerFineTuningProcess":
                              result = get_queue_status()
                              if result != "": # job exists in queue
                                job_queue_state =  result.split()[-2]
                                log_str = f"{log_str}; Job queue: {job_queue_state}"
                                if job_queue_state == "R": # running state
                                  wandb_res = run_local_terminal_command("python3 query_epoch_number_w_total.py")
                                  log_str = f"{log_str}; Epoch: {wandb_res}"

                            #   append info to the log line
                            logger.info(log_str.rstrip(), extra={"run_id": run_id, "status": flow_status})
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
    parser.add_argument("run_id", type=str, nargs='?', default=RUN_ID, help="The UUID of the Globus Flow run to monitor")
    args = parser.parse_args()

    run_id = args.run_id

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"flow_{timestamp}_{run_id}.log"
    log_dir = CONFIG["monitoring"]["log_directory"]
    setup_logging(os.path.join(log_dir, log_file_name))

    get_flow_state_3_65(run_id)
