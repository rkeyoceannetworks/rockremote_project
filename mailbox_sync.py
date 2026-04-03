import os
import glob
import time
import shutil
import configparser
import re
from datetime import datetime
from collections import defaultdict
from modem import RockRemoteIMT 

# --- LOAD CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

PORT_NAME = config.get('Modem', 'Port', fallback='/dev/ttyUSB0')
BAUDRATE = config.getint('Modem', 'Baudrate', fallback=115200)
DEFAULT_TOPIC = config.getint('Modem', 'DefaultTopic', fallback=244)

INBOX_DIR = config.get('Directories', 'InboxDir', fallback='inbox')
OUTBOX_DIR = config.get('Directories', 'OutboxDir', fallback='outbox')
SENT_DIR = config.get('Directories', 'SentDir', fallback='sent')
UNSENT_DIR = config.get('Directories', 'UnsentDir', fallback='unsent')

MAX_FILES = config.getint('Limits', 'MaxFilesPerSync', fallback=5)
MAX_PAYLOAD_SIZE = config.getint('Limits', 'MaxMessageLength', fallback=100000)

def setup_directories():
    for directory in [INBOX_DIR, OUTBOX_DIR, SENT_DIR, UNSENT_DIR]:
        os.makedirs(directory, exist_ok=True)

def is_binary_file(filepath):
    """Sniffs a file to determine if it is text or binary."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
            return False
    except Exception:
        return True

def move_file(original_filepath, filename, destination_dir, suffix):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{filename}.{timestamp}.{suffix}"
    destination = os.path.join(destination_dir, new_filename)
    try:
        shutil.move(original_filepath, destination)
        print(f"Moved to: {destination}")
    except Exception as e:
        print(f"Failed to move file {filename}: {e}")

def parse_outbox_files(file_paths):
    parsed_files = []
    for filepath in file_paths:
        filename = os.path.basename(filepath)
        is_volatile = filename.endswith('.v')
        
        priority = 999 
        match = re.search(r'\.(\d+)(?:\.v)?$', filename)
        if match:
            priority = int(match.group(1))
            
        base_family = re.split(r'[_.]', filename)[0]
        mtime = os.path.getmtime(filepath)
        
        parsed_files.append({
            'filepath': filepath,
            'filename': filename,
            'priority': priority,
            'is_volatile': is_volatile,
            'base_family': base_family,
            'mtime': mtime
        })
    return parsed_files

def process_outbox(modem):
    raw_files = glob.glob(os.path.join(OUTBOX_DIR, '*'))
    raw_files = [f for f in raw_files if os.path.isfile(f)]
    
    if not raw_files:
        print("Outbox is empty.")
        return

    parsed_files = parse_outbox_files(raw_files)
    files_to_send = []
    files_to_discard = []

    # --- HANDLE VOLATILE FILES ---
    volatile_groups = defaultdict(list)
    for f in parsed_files:
        if f['is_volatile']:
            volatile_groups[f['base_family']].append(f)
        else:
            files_to_send.append(f) 

    for family, v_files in volatile_groups.items():
        v_files.sort(key=lambda x: x['mtime'], reverse=True)
        files_to_send.append(v_files[0]) 
        files_to_discard.extend(v_files[1:]) 

    for f in files_to_discard:
        print(f"Pruning stale volatile file: {f['filename']}")
        move_file(f['filepath'], f['filename'], UNSENT_DIR, 'unsent')

    # --- SORT THE SEND QUEUE ---
    files_to_send.sort(key=lambda x: (x['priority'], -x['mtime']))
    final_batch = files_to_send[:MAX_FILES]
    print(f"\nQueueing {len(final_batch)} files for transmission...")

    # --- SEND FILES ---
    for f in final_batch:
        filepath = f['filepath']
        filename = f['filename']
        print(f"\n[TX] Processing: {filename} (Priority: {f['priority']})")
        
        try:
            if is_binary_file(filepath):
                print("Detected Binary file. Using AT+IMTWU...")
                with open(filepath, 'rb') as file:
                    payload = file.read(MAX_PAYLOAD_SIZE)
                    
                if not payload:
                    print("Skipping empty file.")
                    move_file(filepath, filename, SENT_DIR, 'sent')
                    continue
                    
                response = modem.send_binary_message(DEFAULT_TOPIC, payload)
                
            else:
                print("Detected Text file. Using AT+IMTWT...")
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                    payload = file.read(MAX_PAYLOAD_SIZE).strip()
                    
                if not payload:
                    print("Skipping empty file.")
                    move_file(filepath, filename, SENT_DIR, 'sent')
                    continue
                    
                response = modem.send_text_message(DEFAULT_TOPIC, payload)
            
            if "ERROR" not in response:
                print("Successfully queued for transmission.")
                move_file(filepath, filename, SENT_DIR, 'sent')
            else:
                print(f"Failed to send. Modem response: {response}")

        except Exception as e:
            print(f"Error processing file {filename}: {e}")

def process_inbox(modem):
    mt_status = modem.check_mt_status()
    
    if "+IMTMTS:" in mt_status:
        try:
            data_str = mt_status.split("+IMTMTS:")[1].strip()
            parts = data_str.split(",")
            
            if len(parts) >= 3:
                topic_id = parts[0].strip()
                message_id = parts[1].strip()
                message_length = int(parts[2].strip())
                
                print(f"\nIncoming message detected! Topic: {topic_id}, Msg ID: {message_id}, Size: {message_length} bytes")
                
                raw_payload_bytes = modem.receive_binary_message(topic_id, message_length)
                
                if raw_payload_bytes:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    try:
                        text_payload = raw_payload_bytes.decode('utf-8')
                        filename = f"msg_{message_id}_{timestamp}.txt"
                        filepath = os.path.join(INBOX_DIR, filename)
                        with open(filepath, 'w', encoding='utf-8') as file:
                            file.write(text_payload)
                        print(f"Decoded as Text. Saved to inbox as: {filename}")
                        
                    except UnicodeDecodeError:
                        filename = f"msg_{message_id}_{timestamp}.bin"
                        filepath = os.path.join(INBOX_DIR, filename)
                        with open(filepath, 'wb') as file:
                            file.write(raw_payload_bytes)
                        print(f"Kept as Binary. Saved to inbox as: {filename}")
                    
                    ack_response = modem.acknowledge_message(message_id)
                    if "OK" in ack_response:
                        print(f"Successfully acknowledged Message ID {message_id}.")
                    else:
                        print(f"Warning: Failed to acknowledge Message ID {message_id}. Response: {ack_response}")
                else:
                    print("Failed to download payload.")
        except Exception as parse_error:
            print(f"Error parsing MT status or saving file: {parse_error}")
    else:
        print("\nNo incoming messages in the modem queue.")

if __name__ == "__main__":
    setup_directories()
    
    print("\n--- Starting Mailbox Sync ---")
    try:
        with RockRemoteIMT(port=PORT_NAME, baudrate=BAUDRATE) as modem:
            
            print("\n[ PHASE 1: SENDING OUTBOX ]")
            process_outbox(modem)
            
            time.sleep(1)
            
            print("\n[ PHASE 2: RECEIVING INBOX ]")
            process_inbox(modem)
            
    except Exception as e:
        print(f"Script execution failed: {e}")
        
    print("\n--- Mailbox Sync Complete ---")
