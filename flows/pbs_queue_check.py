from globus_compute_sdk import Client, Executor
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from utils import load_config

# Load configuration from YAML
CONFIG = load_config()

ENDPOINT_ID = CONFIG["endpoints"]["compute_endpoint_id"]


def _run_command(command: str) -> str:
    """Execute a shell command (self-contained for remote serialization)."""
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)


def main():
    # Initialize the Client
    gc_executor = Executor(endpoint_id=ENDPOINT_ID)
    gc_executor.serializer = ComputeSerializer(strategy_code=AllCodeStrategies())

    print(f"Submitting task to endpoint: {ENDPOINT_ID}...")
    
    pbs_user = CONFIG["pbs"]["user"]
    tail_lines = CONFIG["pbs"]["tail_lines"]
    future = gc_executor.submit(_run_command, f"qstat -u {pbs_user} | tail -n {tail_lines}")

    # Get the result
    try:
        result = future.result()
        #print(f"Success! Result: {result}")
        if result != "": print(result)
        #print(f"{result.split()[-2]}")

    except Exception as e:
        print(f"Task failed: {e}")

if __name__ == "__main__":
    main()
