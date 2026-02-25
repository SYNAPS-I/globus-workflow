from globus_compute_sdk import Client, Executor

# 1. Replace with your actual Endpoint ID
ENDPOINT_ID = "60e69085-5bd0-43a2-8d4e-e0e216181d02"

# 2. Define a simple function to run on the remote node
def hello_world():
    import platform
    import sys
    return f"Hello from {platform.node()}! Python version: {sys.version}"

def main():
    # Initialize the Client
    # This will prompt for a login if you haven't authenticated on this machine
    gc_executor = Executor(endpoint_id=ENDPOINT_ID)

    print(f"Submitting task to endpoint: {ENDPOINT_ID}...")
    
    # Submit the function
    future = gc_executor.submit(hello_world)

    # Get the result
    try:
        result = future.result()
        print(f"Success! Result: {result}")
    except Exception as e:
        print(f"Task failed: {e}")

if __name__ == "__main__":
    main()
