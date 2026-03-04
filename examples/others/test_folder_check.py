import os
import subprocess
import time
import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Copy current environment and add PYTHONUNBUFFERED
env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

class FileTriggerHandler(FileSystemEventHandler):
    def __init__(self, target_file, script_to_run, monitor_flow_script_path):
        self.target_file = target_file
        self.script_to_run = script_to_run
        self.monitor_flow_script_path = monitor_flow_script_path

    def on_created(self, event):
        if not event.is_directory and os.path.basename(event.src_path) == self.target_file:
            self.execute_logic(event.src_path)

    def execute_logic(self, file_path):
        print(f"Captured the file: {file_path}")

        try:
        ## Atomic-like cleanup
            if os.path.exists(file_path):
                print(f"deleting: {file_path}")
                result = subprocess.run(["rm", "-f", file_path], capture_output=True, text=True)
                #os.remove(file_path)

        except OSError as e:
        #    print(f"File operations failed: {e}")
            pass

def monitor_directory(path, target_file, script_to_run, monitor_flow_script_path):
    event_handler = FileTriggerHandler(target_file, script_to_run, monitor_flow_script_path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    DIRECTORY_TO_WATCH = "/home/beams/TBICER/test_area"
    TARGET_FILENAME = "testing"
    SCRIPT_TO_EXECUTE = "/home/beams/TBICER/projects/synaps-i/flows/sample_flow.py"
    MONITOR_FLOW_SCRIPT_PATH = "/home/beams/TBICER/projects/synaps-i/flows/globus_flow_status.py"
    
    monitor_directory(DIRECTORY_TO_WATCH, TARGET_FILENAME, SCRIPT_TO_EXECUTE, MONITOR_FLOW_SCRIPT_PATH)
