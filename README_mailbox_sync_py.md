# Mailbox Sync Orchestrator (`mailbox_sync.py`)

## Overview
`mailbox_sync.py` is the primary orchestrator script for the priority-based transmission system. It bridges the local file system with the `RockRemoteIMT` modem library to automatically manage, prioritize, and transmit outbound files, as well as receive and decode inbound messages.



## Configuration (`config.ini`)
Before running the sync, the script reads operational parameters from a `config.ini` file. 
* **Modem Settings:** Defines the serial port (e.g., `/dev/ttyUSB0`), baudrate (default `115200`), and the default Topic ID.
* **Directory Paths:** Sets the names for the `InboxDir`, `OutboxDir`, `SentDir`, and `UnsentDir`.
* **Limits:** Enforces `MaxFilesPerSync` (e.g., 5 files per run) and `MaxMessageLength` (e.g., 100,000 bytes) to respect modem payload limitations.

## Directory Structure
Upon execution, the script automatically verifies or creates the following directory structure:
* `outbox/`: Where edge applications drop files ready for transmission.
* `sent/`: Where successfully transmitted files are archived (appended with a timestamp).
* `unsent/`: Where stale, redundant volatile files are moved when pruned from the queue.
* `inbox/`: Where incoming messages downloaded from the satellite are saved.

---

## Core Features & Workflow

### 1. The File Naming Convention
The orchestrator relies on strict file naming conventions parsed via regular expressions to route data.
* **Priority Tier:** Extracted from integer suffixes (e.g., `alert.txt.1` is priority 1, `status.txt.100` is priority 100). Files without a tier default to priority `999`.
* **Volatile Flag:** Files ending in `.v` are flagged as volatile and subject to pruning.
* **Base Family:** The prefix before any underscores or periods is used to group similar files together (e.g., `telemetry_2026.gz.10.v` belongs to the "telemetry" family).

### 2. Phase 1: Sending Outbox
When Phase 1 begins, the script executes the following queue logic:
1. **Volatile Pruning:** It groups all `.v` flagged files by their base family name. It sorts them by modification time (`mtime`), keeps the newest file in the active queue, and moves the older files to the `unsent/` directory.
2. **Priority Sorting:** The remaining active queue is sorted first by Priority Tier (lowest number first), and then chronologically (newest files first within the same tier).
3. **Payload Sniffing:** Before sending, it reads the first 1024 bytes of the file. If it detects a null byte (`b'\0'`), it dynamically routes the file through the binary transmission method (`AT+IMTWU`). Otherwise, it uses the text method (`AT+IMTWT`).
4. **Transmission & Cleanup:** It streams the data up to the `MAX_PAYLOAD_SIZE`. If successful, the file is timestamped and moved to the `sent/` directory.

### 3. Phase 2: Receiving Inbox
After processing the outbox, the script polls the modem for incoming data:
1. **Queue Polling:** It sends `AT+IMTMTS` to check for incoming Mobile Terminated (MT) messages.
2. **Data Extraction:** If a message is waiting, it parses the Topic ID, Message ID, and payload size from the modem's response.
3. **Download & Decoding:** It downloads the raw bytes using `AT+IMTRB`. It then attempts to decode the bytes as `utf-8` text. If successful, it saves as a `.txt` file; if a `UnicodeDecodeError` occurs, it saves the raw data as a `.bin` file.
4. **Acknowledgment:** It clears the message from the modem's internal queue by sending `AT+IMTA=[message_id]`.

---

## Execution Guide

To run a synchronization cycle, simply execute the script from the command line:

```bash
python mailbox_sync.py
```

### Expected Output
The console will output the step-by-step process:
1. Directory preparation.
2. Notification of any pruned stale files.
3. The number of files queued for transmission (capped at `MaxFilesPerSync`).
4. TX status for each file, including whether it was detected as "Binary" or "Text".
5. RX status, displaying any incoming messages downloaded and acknowledged.
