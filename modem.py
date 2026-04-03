import serial
import time
import logging

# --- CONFIGURE LOGGING ---
logger = logging.getLogger("RockRemote")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('at_commands.log')
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(file_handler)

class RockRemoteIMT:
    def __init__(self, port, baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def __enter__(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            logger.info(f"Port OPENED: {self.port} at {self.baudrate} baud")
            return self
        except serial.SerialException as e:
            error_msg = f"Failed to open serial port {self.port}: {e}"
            logger.critical(error_msg)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info(f"Port CLOSED: {self.port}")
        
        if exc_type:
            logger.error(f"Execution Error: {exc_val}")
        return False

    def send_command(self, command, wait_time=1):
        if not self.ser or not self.ser.is_open:
            return "Error: Serial port is not open."
        
        try:
            logger.debug(f"TX: {command}")
            full_command = f"{command}\r".encode('ascii')
            self.ser.write(full_command)
            
            time.sleep(wait_time) 
            
            response = ""
            while self.ser.in_waiting > 0:
                response += self.ser.read(self.ser.in_waiting).decode('ascii', errors='ignore')
            
            response = response.replace('\r\n', '\n').replace('\r', '\n').strip()
            
            if '\n' in response:
                logger.debug(f"RX:\n{response}")
            else:
                logger.debug(f"RX: {response}")
                
            return response
            
        except serial.SerialException as e:
            logger.error(f"Serial Error: {e}")
            return f"Serial Error: {e}"
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            return f"Unexpected Error: {e}"

    # --- TEXT METHODS ---
    def list_topics(self):
        return self.send_command("AT+IMTT")

    def check_queue(self):
        return self.send_command("AT+IMTQ")

    def check_mt_status(self):
        return self.send_command("AT+IMTMTS")

    def acknowledge_message(self, message_id=""):
        command = f"AT+IMTA={message_id}" if message_id else "AT+IMTA"
        return self.send_command(command)

    def send_text_message(self, topic_id, text):
        command = f'AT+IMTWT={topic_id},"{text}"'
        return self.send_command(command)

    def receive_text_message(self, topic_id=""):
        command = f"AT+IMTRT={topic_id}" if topic_id else "AT+IMTRT"
        return self.send_command(command, wait_time=2)

    # --- BINARY METHODS ---
    def send_binary_message(self, topic_id, binary_payload):
        length = len(binary_payload)
        logger.debug(f"TX: AT+IMTWU={topic_id},{length} (Binary Mode)")
        
        if not self.ser or not self.ser.is_open:
            return "Error: Serial port is not open."
            
        try:
            command = f"AT+IMTWU={topic_id},{length}\r".encode('ascii')
            self.ser.write(command)
            
            response = ""
            start_time = time.time()
            while "READY" not in response and time.time() - start_time < 5:
                if self.ser.in_waiting > 0:
                    response += self.ser.read(self.ser.in_waiting).decode('ascii', errors='ignore')
                time.sleep(0.1)
                
            if "READY" in response:
                logger.debug("RX: " + response.strip())
                logger.debug(f"TX: <{length} bytes of raw binary data>")
                
                self.ser.write(binary_payload)
                
                time.sleep(2) 
                final_response = ""
                while self.ser.in_waiting > 0:
                    final_response += self.ser.read(self.ser.in_waiting).decode('ascii', errors='ignore')
                
                clean_response = final_response.replace('\r\n', '\n').strip()
                logger.debug(f"RX: {clean_response}")
                return clean_response
            else:
                logger.error(f"Failed to get READY prompt. Got: {response}")
                return f"ERROR: No READY prompt. Modem said: {response}"
                
        except Exception as e:
            logger.error(f"Binary Transmission Error: {e}")
            return f"ERROR: {e}"

    def receive_binary_message(self, topic_id, expected_length):
        logger.debug(f"TX: AT+IMTRB={topic_id} (Expecting {expected_length} bytes)")
        
        try:
            command = f"AT+IMTRB={topic_id}\r".encode('ascii')
            self.ser.write(command)
            
            time.sleep(2) 
            raw_data = b""
            start_time = time.time()
            
            while time.time() - start_time < 5:
                if self.ser.in_waiting > 0:
                    raw_data += self.ser.read(self.ser.in_waiting)
                    start_time = time.time() 
                time.sleep(0.1)

            start_idx = raw_data.find(b'\n') + 1
            
            if start_idx > 0:
                # The modem appends a 2-byte CRC, we slice exactly the payload length to ignore it
                payload = raw_data[start_idx : start_idx + expected_length]
                logger.debug(f"RX: <{len(payload)} bytes of binary data downloaded>")
                return payload
            else:
                logger.error("Failed to parse binary start index.")
                return b""
                
        except Exception as e:
            logger.error(f"Binary Reception Error: {e}")
            return b""
