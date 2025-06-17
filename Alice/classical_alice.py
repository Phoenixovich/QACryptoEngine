import os
import sys
import signal
import psutil
import socket
import base64
import hashlib
from cryptography.fernet import Fernet
import threading
import time
import argparse

# Kill previous instance of this script (except current PID)
current_pid = os.getpid()
script_name = os.path.basename(__file__)
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['pid'] != current_pid and proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
            proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

HOST = '127.0.0.1'
ALICE_PORT = 65433  # Alice's server port (for receiving)
BOB_PORT = 65434   # Bob's server port (for sending)

parser = argparse.ArgumentParser()
parser.add_argument('--mitm', action='store_true', help='Connect via MITM proxy')
args = parser.parse_args()

# Read the QKD key from file (ensure absolute path)
key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_key_alice.txt")
with open(key_path) as f:
    qkd_key = f.read().strip()

# Convert QKD key (bit string) to Fernet key
key_bytes = int(qkd_key, 2).to_bytes((len(qkd_key) + 7) // 8, byteorder='big')
hashed = hashlib.sha256(key_bytes).digest()
fernet_key = base64.urlsafe_b64encode(hashed)
fernet = Fernet(fernet_key)

def print_received(addr, msg):
    print(f"[Alice] Received: {msg}\n> ", end='', flush=True)

def receive_messages():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, ALICE_PORT))
        s.listen()
        # print(f"[Alice] Listening for incoming messages on port {ALICE_PORT}...\n")
        while True:
            conn, addr = s.accept()
            with conn:
                encrypted = conn.recv(4096)
                # print(f"[Alice] Debug: Received raw bytes: {encrypted}")
                if encrypted:
                    try:
                        decrypted = fernet.decrypt(encrypted)
                        print_received(addr, decrypted.decode())
                    except Exception as e:
                        print("[Alice] Decryption failed:", e)

def send_messages():
    while True:
        msg = input("> ")
        if msg.lower() in ("quit", "exit"): break
        encrypted = fernet.encrypt(msg.encode())
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, BOB_PORT))
                s.sendall(encrypted)
        except Exception as e:
            print(f"[Alice] Failed to send: {e}")

def receive_thread(sock, fernet):
    addr = 'peer'
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("[Alice] Connection closed by peer.")
                break
            try:
                decrypted = fernet.decrypt(data)
                print_received(addr, decrypted.decode())
            except Exception as e:
                print("[Alice] Decryption failed (incoming):", e)
        except Exception as e:
            print("[Alice] Receive error:", e)
            break

def mitm_chat():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, ALICE_PORT))
        threading.Thread(target=receive_thread, args=(s, fernet), daemon=True).start()
        while True:
            msg = input("> ")
            if msg.lower() in ("quit", "exit"): break
            encrypted = fernet.encrypt(msg.encode())
            try:
                s.sendall(encrypted)
            except Exception as e:
                print(f"[Alice] Failed to send: {e}")
                break

if __name__ == "__main__":
    if args.mitm:
        mitm_chat()
    else:
        t = threading.Thread(target=receive_messages, daemon=True)
        t.start()
        send_messages()
        t.join()  # Wait for receive thread to finish before exiting
    print("[Alice] Exiting chat.")
