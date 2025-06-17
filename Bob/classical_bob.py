import os
import sys
import signal
import psutil

# Kill previous instance of this script (except current PID)
current_pid = os.getpid()
script_name = os.path.basename(__file__)
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['pid'] != current_pid and proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
            proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

import socket
import base64
import hashlib
from cryptography.fernet import Fernet
import threading

HOST = '127.0.0.1'
BOB_PORT = 65434  # Bob's server port (for receiving)
ALICE_PORT = 65433  # Alice's server port (for sending)

# Read the QKD key from file (ensure absolute path)
key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_key_bob.txt")
with open(key_path) as f:
    qkd_key = f.read().strip()

# Convert QKD key (bit string) to Fernet key
key_bytes = int(qkd_key, 2).to_bytes((len(qkd_key) + 7) // 8, byteorder='big')
hashed = hashlib.sha256(key_bytes).digest()
fernet_key = base64.urlsafe_b64encode(hashed)

cipher = Fernet(fernet_key)

def receive_messages():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, BOB_PORT))
        s.listen()
        print(f"[Bob] Listening for incoming messages on port {BOB_PORT}...")
        while True:
            conn, addr = s.accept()
            with conn:
                encrypted = conn.recv(4096)
                if encrypted:
                    try:
                        decrypted = cipher.decrypt(encrypted)
                        print(f"\n[Bob] Message from {addr}: {decrypted.decode()}\n> ", end='', flush=True)
                    except Exception as e:
                        print("[Bob] Decryption failed:", e)

def send_messages():
    while True:
        msg = input("> ")
        if msg.lower() in ("quit", "exit"): break
        encrypted = cipher.encrypt(msg.encode())
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, ALICE_PORT))
                s.sendall(encrypted)
        except Exception as e:
            print(f"[Bob] Failed to send: {e}")

if __name__ == "__main__":
    threading.Thread(target=receive_messages, daemon=True).start()
    send_messages()
    print("[Bob] Exiting chat.")
