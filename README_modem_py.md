# RockRemoteIMT Library (`modem.py`)

The `modem.py` script provides the `RockRemoteIMT` class, a robust Python wrapper for communicating with a RockREMOTE satellite modem over a serial interface. It translates standard Python methods into the necessary AT commands required for both text and binary payload transmissions.

## Features
* **Context Management:** Designed to be used with Python's `with` statement to ensure serial ports are safely opened and closed.
* **Text & Binary Support:** Distinct methods for sending plain text (`AT+IMTWT`) and raw binary bytes (`AT+IMTWU`).
* **Automatic Logging:** Records all inbound (RX) and outbound (TX) serial traffic to an `at_commands.log` file for debugging.

## Requirements
* `pyserial` (imported as `serial`).
* Built-in libraries: `time`, `logging`.

---

## Usage Guide

### 1. Initialization and Connection
The recommended way to instantiate the modem is using a context manager. This automatically handles port closure even if an execution error occurs.

```python
from modem import RockRemoteIMT

# Initialize with the port and baudrate
with RockRemoteIMT(port='/dev/ttyUSB0', baudrate=115200) as modem:
    # Modem is connected and ready
    pass
```

### 2. Transmitting Text Messages
Text messages are sent to a specific Topic ID. The payload must be a string.

```python
with RockRemoteIMT(port='/dev/ttyUSB0') as modem:
    topic_id = 244
    text_payload = "Sensor OK: 18.5C"
    
    response = modem.send_text_message(topic_id, text_payload)
    print(f"Modem Response: {response}")
```

### 3. Transmitting Binary Messages
Binary transmissions require strict timing. The library automatically sends the header (`AT+IMTWU`), calculates the length, waits for a `READY` prompt (with a 5-second timeout), and then streams the raw bytes.

```python
with RockRemoteIMT(port='/dev/ttyUSB0') as modem:
    topic_id = 244
    binary_payload = b'\x1f\x8b\x08\x00...' # e.g., a GZIP archive
    
    response = modem.send_binary_message(topic_id, binary_payload)
    print(f"Modem Response: {response}")
```

### 4. Receiving Messages (Inbox Polling)
To receive messages, you must first check the Mobile Terminated (MT) queue status. 

```python
with RockRemoteIMT(port='/dev/ttyUSB0') as modem:
    # 1. Check if there are messages waiting
    status = modem.check_mt_status() 
    
    # 2. Extract routing variables (assuming we parsed from status)
    topic = "244"
    msg_id = "123"
    expected_length = 50
    
    # 3. Download the binary payload. 
    # The library automatically slices the exact payload length to ignore the 2-byte CRC appended by the modem.
    payload = modem.receive_binary_message(topic, expected_length)
    
    # 4. Acknowledge the message to remove it from the modem's queue
    modem.acknowledge_message(msg_id)
```

---

## API Reference

### Core Methods
* `__init__(self, port, baudrate=115200, timeout=2)`: Configures the serial port settings and timeout threshold.
* `send_command(self, command, wait_time=1)`: A lower-level method to send a raw AT command and read the response. It handles appending carriage returns (`\r`) and cleaning up newlines from the response.

### Text Transmission
* `send_text_message(self, topic_id, text)`: Transmits an ASCII text string to the specified topic using `AT+IMTWT`.
* `receive_text_message(self, topic_id="")`: Requests the next pending text message from the modem using `AT+IMTRT`.

### Binary Transmission 
* `send_binary_message(self, topic_id, binary_payload)`: Calculates payload length, initiates transfer via `AT+IMTWU`, waits for `READY`, and streams the bytearray over the serial port.
* `receive_binary_message(self, topic_id, expected_length)`: Downloads a binary payload via `AT+IMTRB`. Finds the newline delimiter and slices the bytes to accurately exclude the trailing CRC.

### Queue and Topic Management
* `list_topics(self)`: Sends `AT+IMTT` to list configured topics.
* `check_queue(self)`: Sends `AT+IMTQ` to check the outbound transmission queue.
* `check_mt_status(self)`: Sends `AT+IMTMTS` to check for incoming (Mobile Terminated) messages.
* `acknowledge_message(self, message_id="")`: Sends `AT+IMTA` to clear a message from the incoming queue after a successful download.

---

## Logging Details
The library leverages Python's built-in `logging` module. It creates a logger named `RockRemote` and writes timestamped debug information (including full TX/RX payloads and AT commands) to `at_commands.log`. If a serial connection fails to open, it logs a critical error and raises the exception.
