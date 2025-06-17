import socket
import base64
import hashlib
from cryptography.fernet import Fernet

HOST = '127.0.0.1'
PORT = 65433  # Different from QKD port

# Read key
with open("final_key_alice.txt", "rb") as f:
    key = f.read().strip()  # already base64-encoded Fernet key
fernet = Fernet(key)


# Encrypt message
message = "This is a secret message from Alice."
encrypted = fernet.encrypt(message.encode())

# Send over socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print("Alice (Classical): Waiting for Bob...")
    conn, addr = s.accept()
    with conn:
        print(f"Connected to {addr}")
        conn.sendall(encrypted)
        print("Encrypted message sent.")
