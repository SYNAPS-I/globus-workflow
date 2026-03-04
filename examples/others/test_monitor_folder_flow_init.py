import os
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileTriggerHandler(FileSystemEventHandler):
    def __init__(self, target_file, script_to_run):
        self.target_file = target_file
        self.script_to_run = script_to_run

    def on_created(self, event):
        if not event.is_directory and os.path.basename(event.src_path) == self.target_file:
            self.execute_logic(event.src_path)

    def execute_logic(self, file_path):
        print(f"Captured the file: {file_path}")
        try:
            # Trigger secondary process
            result = subprocess.run(["python3", self.script_to_run], 
                                    check=True,
                                    capture_output=True,
                                    text=True)

            run_output = result.stdout
            if "ID: " in run_output:
                flow_id = run_output.split("ID: ")[-1].strip()
                print(f"Captured ID from the process: {flow_id}") # This will be the 
            else: 
                print(f"Unable to interprete process output:\n stdout: {run_output}")
            
            # Atomic-like cleanup
            if os.path.exists(file_path):
                os.remove(file_path)
        except subprocess.CalledProcessError as e:
            print(f"Subprocess execution failed: {e}")
        except OSError as e:
            print(f"File operations failed: {e}")

def monitor_directory(path, target_file, script_to_run):
    event_handler = FileTriggerHandler(target_file, script_to_run)
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
    DIRECTORY_TO_WATCH = "/home/beams/TBICER/flow_ptycho_fine_tune/flow/"
    TARGET_FILENAME = "dm_data_ready"
    SCRIPT_TO_EXECUTE = "/home/beams/TBICER/projects/synaps-i/flows/test_process_data.py"
    
    monitor_directory(DIRECTORY_TO_WATCH, TARGET_FILENAME, SCRIPT_TO_EXECUTE)
