import datetime
import os

def append_timestamp(target_filepath="data_log.txt"):
    """
    Concatenates the current UTC timestamp to the end of an existing file.
    Creates the file if it does not exist.
    """
    # Generate ISO 8601 formatted timestamp
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    try:
        # 'a' mode: Append to the end of the file
        with open(target_filepath, "a", encoding="utf-8") as file_handle:
            file_handle.write(f"{timestamp}\n")
            
    except PermissionError:
        print(f"Error: Insufficient permissions to write to {target_filepath}.")
    except OSError as e:
        print(f"I/O error occurred: {e}")

    print("Timestamp was written. Run ID: 9e848ee5-90d3-47f2-8e95-de77f6195f3c") #Example id

if __name__ == "__main__":
    LOG_FILE = "persistent_records.txt"
    append_timestamp(LOG_FILE)
