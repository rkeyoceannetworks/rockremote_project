# Test Data Generator (`generate_test_files.py`)

## Overview
The `generate_test_files.py` script is a simulation utility designed to populate the `outbox/` directory with a controlled set of test data. It acts as a mock edge application, generating files with specific naming conventions, varying payload types (text, CSV, binary), and manipulated timestamps. 

This allows you to safely test the queuing, sorting, and pruning logic of your `modem.py` and `mailbox_sync.py` scripts without waiting for real-world telemetry or alerts.



## Key Features
* **Environment Reset:** Automatically creates the `outbox/` directory if it doesn't exist and completely clears out any old files to ensure a clean slate for every test run.
* **Timestamp Spoofing:** Uses the `os.utime()` function to artificially age files. By passing `age_in_seconds`, it simulates a realistic timeline of older and newer files to test chronological sorting.
* **Native Compression:** Capable of generating both standard UTF-8 text files and real, binary-compressed GZIP archives on the fly using Python's built-in `gzip` library.

---

## The Generated File Queue

When executed, the script generates four distinct categories of test files to stress-test different routing rules:

### 1. Text Files (Priority & Sorting)
These files test the basic priority tiering and chronological sorting mechanism.
* `alert_new.txt.1`: High priority (Tier 1), generated with a 10-second age.
* `alert_old.txt.1`: High priority (Tier 1), generated with a 600-second age to test chronological sorting against the newer alert.
* `status.txt.100`: Low priority (Tier 100).
* `regular_data.txt`: No priority suffix specified, which defaults to the lowest priority (999).

### 2. Text Files (Volatile Pruning)
These test the volatile (`.v`) pruning logic, ensuring older data is discarded in favor of newer data.
* `log_2026_04_01.txt.5.v`: Simulates an old log (86,400 seconds / 1 day old) that should be pruned.
* `log_2026_04_02.txt.5.v`: Simulates a newer log (100 seconds old) that should successfully queue.

### 3. Binary GZIP Files
These test the modem's ability to handle raw binary bytes and apply priority rules to `.gz` extensions.
* `urgent_image.gz.1`: A high-priority binary file.
* `sensor_dump.gz`: A standard, unprioritized binary file.
* `telemetry_2026_04_01.gz.10.v` & `telemetry_2026_04_02.gz.10.v`: Tests if the volatile pruning logic correctly groups and drops older binary files.

### 4. CSV Files (Simulated Temperature Data)
These simulate larger payloads of structured data (10 rows each) to test both plain text and compressed CSV handling.
* `temp_data_urgent.csv.1`: An urgent plain text CSV that should jump to the front of the queue.
* `temp_data_standard.csv`: A standard uncompressed CSV.
* `temp_data_newest.csv.gz`: A very recent (2 seconds old) GZIP-compressed CSV.

---

## Execution Guide

### Prerequisites
* Python 3.x
* No external dependencies are required (relies strictly on standard libraries: `os`, `time`, `gzip`).

### Running the Script
Execute the script from your terminal before running the mailbox sync:

```bash
python generate_test_files.py
```

### Expected Output
The script will output a clean log to your terminal confirming the setup of the `outbox/` directory and detailing the creation of each file, including its filename, spoofed age in seconds, and whether it was saved as `TEXT` or `BINARY (.gz)`.
