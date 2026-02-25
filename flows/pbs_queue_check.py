from globus_compute_sdk import Client, Executor

# 1. Replace with your actual Endpoint ID
ENDPOINT_ID = "60e69085-5bd0-43a2-8d4e-e0e216181d02"

# 2. Define a simple function to run on the remote node

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

def main():
    # Initialize the Client
    # This will prompt for a login if you haven't authenticated on this machine
    gc_executor = Executor(endpoint_id=ENDPOINT_ID)

    print(f"Submitting task to endpoint: {ENDPOINT_ID}...")
    
    # Submit the function
    #future = gc_executor.submit(hello_world)
    future = gc_executor.submit(run_terminal_command, ["qstat -u bicer | tail -n 1"])

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
