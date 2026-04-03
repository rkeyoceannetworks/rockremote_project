import os
import time
import gzip

OUTBOX_DIR = 'outbox'

def setup():
    """Ensure the outbox directory exists and is empty."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    print(f"Clearing and preparing '{OUTBOX_DIR}' directory...")
    
    for f in os.listdir(OUTBOX_DIR):
        file_path = os.path.join(OUTBOX_DIR, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

def create_test_file(filename, content, age_in_seconds=0, is_gzip=False):
    """
    Creates a file (text or gzip binary) and spoofs its modification time.
    """
    filepath = os.path.join(OUTBOX_DIR, filename)
    
    if is_gzip:
        # Create a real, compressed binary gzip file
        with gzip.open(filepath, 'wb') as f:
            f.write(content.encode('utf-8'))
    else:
        # Create a standard plain text file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    # Spoof the modification time
    current_time = time.time()
    spoofed_time = current_time - age_in_seconds
    os.utime(filepath, (spoofed_time, spoofed_time))
    
    file_type = "BINARY (.gz)" if is_gzip else "TEXT"
    print(f"Created: {filename:<30} | Age: {age_in_seconds:>4}s | Type: {file_type}")

if __name__ == "__main__":
    setup()
    print("-" * 60)
    
    # --- 1. TEXT FILES (Priority & Sorting) ---
    # Even though regular_data is newest, alert_new should go first.
    create_test_file("alert_new.txt.1", "High priority alert - Newest", age_in_seconds=10)
    create_test_file("alert_old.txt.1", "High priority alert - Older", age_in_seconds=600)
    create_test_file("status.txt.100", "Low priority status update", age_in_seconds=30)
    create_test_file("regular_data.txt", "No priority specified (Defaults to 999)", age_in_seconds=5)

    # --- 2. TEXT FILES (Volatile Pruning) ---
    # The older log should be moved to 'unsent', and ONLY the newer log should be queued.
    create_test_file("log_2026_04_01.txt.5.v", "Volatile Log - Yesterday (PRUNE ME)", age_in_seconds=86400)
    create_test_file("log_2026_04_02.txt.5.v", "Volatile Log - Today (SEND ME)", age_in_seconds=100)
    
    # --- 3. BINARY GZIP FILES ---
    # Standard compressed payload (No priority, defaults to 999)
    create_test_file("sensor_dump.gz", "This text is compressed into a binary gzip format.", age_in_seconds=15, is_gzip=True)
    
    # High Priority compressed payload
    create_test_file("urgent_image.gz.1", "Fake compressed image data.", age_in_seconds=5, is_gzip=True)

    # Volatile compressed payloads (Testing if our pruning logic works on binary files too!)
    # Because their base family is "telemetry", they will be grouped. The older one gets pruned.
    create_test_file("telemetry_2026_04_01.gz.10.v", "Old compressed telemetry (PRUNE ME)", age_in_seconds=5000, is_gzip=True)
    create_test_file("telemetry_2026_04_02.gz.10.v", "New compressed telemetry (SEND ME)", age_in_seconds=50, is_gzip=True)

    # --- 4. CSV FILES (Simulated Temperature Data) ---
    
    csv_standard = """sensor,temp,status
S1,18.5,OK
S2,19.0,OK
S3,18.8,OK
S4,19.2,OK
S5,18.9,OK
S6,19.1,OK
S7,18.7,OK
S8,19.3,OK
S9,18.6,OK
S10,19.0,OK"""

    csv_urgent = """URGENT - temp,sensor
45.5,S1
46.1,S2
45.8,S3
47.2,S4
46.5,S5
48.0,S6
45.9,S7
46.8,S8
47.5,S9
48.2,S10"""

    csv_compressed = """temp,sensor
24.5,S1
24.6,S2
24.4,S3
24.7,S4
24.5,S5
24.8,S6
24.3,S7
24.6,S8
24.5,S9
24.7,S10"""

    # Uncompressed CSV (Standard) - defaults to priority 999
    create_test_file("temp_data_standard.csv", csv_standard, age_in_seconds=20)
    
    # Uncompressed CSV (Urgent) - Priority 1 (.1 suffix) triggers front-of-line placement
    create_test_file("temp_data_urgent.csv.1", csv_urgent, age_in_seconds=8)

    # Compressed CSV (Newest Telemetry) - Binary gzip format
    create_test_file("temp_data_newest.csv.gz", csv_compressed, age_in_seconds=2, is_gzip=True)

    print("-" * 60)
    print("Test files generated successfully!")
    print("Run 'python mailbox_sync.py' to watch the hybrid text/binary logic in action.")
