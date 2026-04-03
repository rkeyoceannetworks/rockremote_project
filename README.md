# Priority Mailbox System Overview
Together, these files create a specialized file-transfer queue designed to operate over a serial modem. 

## 1. `generate_test_files.py`
This script is a simulation tool used to safely test your transmission logic without needing live data. 
* **Environment Setup:** It verifies that an `outbox` directory exists and clears out any preexisting files to ensure a clean test run.
* **Payload Generation:** It creates a variety of dummy files, including plain text logs, raw CSVs, and compressed binary GZIP archives.
* **Timestamp Spoofing:** It intentionally alters the modification times of the generated files to simulate a timeline of older and newer data.
* **Naming Conventions:** It appends specific routing flags to the filenames—such as `.1` to indicate an urgent priority, or `.v` to designate volatile data that can be safely overwritten by newer versions.

## 2. `modem.py`
This script acts as the communication wrapper, translating Python functions into the AT commands required by the physical hardware.
* **Connection Management:** It defines the `RockRemoteIMT` class, which handles opening and closing the serial port at the designated baudrate.
* **Text Handling:** It provides functions (`send_text_message` and `receive_text_message`) to transmit and receive standard ASCII data using `AT+IMTWT` and `AT+IMTRT`.
* **Binary Handling:** It manages the strict timing required for binary transfers via `AT+IMTWU` and `AT+IMTRB`, which includes waiting for a `READY` prompt before streaming raw byte payloads.
* **Diagnostic Logging:** It intercepts all inbound and outbound serial traffic and records it to an `at_commands.log` file.

## 3. `mailbox_sync.py`
This is the core orchestrator that applies your business logic to the raw files and commands the modem to act.
* **Configuration Loading:** It reads operational parameters (like the max payload size of 100,000 bytes and the max files per sync) directly from `config.ini`.
* **Volatile Pruning:** It groups files tagged with `.v` by their base family name, keeps only the most recent file in that group, and moves the older, stale files to the `unsent` directory.
* **Priority Sorting:** It evaluates the remaining queue based on the priority suffix (e.g., `.1`) and timestamp, ensuring the most critical files are positioned at the front of the line.
* **Transmission Routing:** It reads the contents of the files to sniff for null bytes; if found, it dynamically routes the file through the modem's binary protocol, otherwise, it defaults to the text protocol.
* **Inbox Checking:** After transmitting, it polls the modem for incoming messages (`AT+IMTMTS`), downloads any pending payloads, and attempts to decode them as UTF-8 text before saving them to the `inbox` directory.

#############
Accidental old stuf from other project



# Cloudloop Iridium MQTT Bridge

A Python-based interface for interacting with the Cloudloop MQTT Broker. This tool allows you to send (MT) and receive (MO) messages from remote Iridium satellite devices using an authenticated TLS connection.

## 🚀 Features
- **Real-time Monitoring**: Subscribes to Mobile Originated (MO) messages.
- **Bi-directional Comm**: Interactive terminal to send Mobile Terminated (MT) messages.
- **Secure**: Uses Certificate-based authentication (TLS 1.2).
- **Environment Driven**: Decoupled configuration using `.env` files.

---

## 🛠️ Setup & Installation

### 1. Clone & Environment
git clone https://github.com/YOUR_USERNAME/cloudloop-mqtt.git
cd cloudloop-mqtt
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

### 2. Certificates
Create a certs/ directory and place your Cloudloop-provided certificates inside:
- CloudloopMQTT.pem (CA Root)
- XXXXXXXX-certificate.pem.crt (Client Cert)
- XXXXXXXX-private.pem.crt (Private Key)

### 3. Configuration
Copy the example environment file:
cp .env.example .env

Edit .env and fill in your specific Account ID, Thing ID, and the filenames of your certificates.

---

## 📖 Usage
Run the main script to start the bridge:
python main.py

- Incoming messages from your Iridium device will print to the console automatically.
- Outgoing messages can be typed directly into the prompt. Type 'q' to exit.

---

## 🔒 Security Notice
This repository is configured to ignore sensitive files. Ensure your .gitignore includes:
- .env
- certs/
- venv/

Never commit your private keys or .pem files to a public repository.
