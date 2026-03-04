import os
import subprocess
import time
import datetime
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from utils import load_config

# Load configuration from YAML
CONFIG = load_config()

PYTHON_EXECUTABLE = CONFIG["monitoring"]["python_executable"]
MONITOR_LOG_DIRECTORY = CONFIG["monitoring"]["monitor_log_directory"]

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
            # Trigger secondary process
            result = subprocess.run([PYTHON_EXECUTABLE, self.script_to_run], 
                                    check=True,
                                    capture_output=True,
                                    text=True)

            run_output = result.stdout
            if "ID: " in run_output:
                flow_id = run_output.split("ID: ")[-1].strip()
                print(f"Captured ID from the process: {flow_id}") # This will be the 

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                tfile = f"initialized_flow_{timestamp}_{flow_id}"
                with open(os.path.join(MONITOR_LOG_DIRECTORY, tfile), "x"): pass # This should create file 

                # Launch the detached external script
                subprocess.Popen(
                    [PYTHON_EXECUTABLE, self.monitor_flow_script_path, flow_id], 
                    start_new_session=True,        # DETACH: Creates a new process group (Linux/macOS)
                    env=env,                       # Unbuffered writes for the logger
                    stdout=subprocess.DEVNULL,     # Redirect output to void to prevent broken pipes
                    stderr=subprocess.DEVNULL      # Redirect errors to void
                ) 

            else: 
                print(f"Unable to interprete process output:\n stdout: {run_output}")
            

            result = subprocess.run(["rm", "-f", file_path], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully removed: {file_path}")
            else:
                print(f"Failed to remove {file_path}")
                print(f"Error: {result.stderr}")
                #os.remove(file_path)

        except subprocess.CalledProcessError as e:
            print(f"Subprocess execution failed: {e}")
        except OSError as e:
            print(f"File operations failed: {e}")

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
    DIRECTORY_TO_WATCH = CONFIG["monitoring"]["directory_to_watch"]
    TARGET_FILENAME = CONFIG["monitoring"]["target_filename"]
    SCRIPT_TO_EXECUTE = CONFIG["monitoring"]["script_to_execute"]
    MONITOR_FLOW_SCRIPT_PATH = CONFIG["monitoring"]["monitor_flow_script_path"]
    
    monitor_directory(DIRECTORY_TO_WATCH, TARGET_FILENAME, SCRIPT_TO_EXECUTE, MONITOR_FLOW_SCRIPT_PATH)
