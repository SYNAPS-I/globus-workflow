"""Example: submit a Globus transfer and monitor progress."""

import argparse
import sys
import time

from utils.auth import get_transfer_client
from utils.transfer import submit_transfer


def main():
    parser = argparse.ArgumentParser(description="Submit a Globus Transfer task.")
    parser.add_argument("--source", required=True, help="Source endpoint UUID")
    parser.add_argument("--dest", required=True, help="Destination endpoint UUID")
    parser.add_argument("--source-path", required=True, help="Path on source endpoint")
    parser.add_argument("--dest-path", required=True, help="Path on destination endpoint")
    parser.add_argument("--label", default="globus-workflow transfer", help="Task label")
    parser.add_argument("--wait", action="store_true", help="Wait for task to complete")
    args = parser.parse_args()

    result = submit_transfer(
        source_endpoint=args.source,
        dest_endpoint=args.dest,
        source_path=args.source_path,
        dest_path=args.dest_path,
        label=args.label,
    )

    task_id = result["task_id"]
    print(f"Transfer submitted. Task ID: {task_id}")

    if args.wait:
        tc = get_transfer_client()
        print("Waiting for transfer to complete...")
        while True:
            task = tc.get_task(task_id)
            status = task["status"]
            if status in ("SUCCEEDED", "FAILED"):
                print(f"Task {task_id}: {status}")
                sys.exit(0 if status == "SUCCEEDED" else 1)
            print(f"  Status: {status} — checking again in 10s")
            time.sleep(10)


if __name__ == "__main__":
    main()
