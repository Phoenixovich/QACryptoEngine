import socket
import base64
import hashlib
from cryptography.fernet import Fernet

HOST = '127.0.0.1'
PORT = 65433

# Read key
with open("final_key_bob.txt", "rb") as f:
    key = f.read().strip()
fernet = Fernet(key)


# Receive and decrypt
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    encrypted = s.recv(2048)
    decrypted = fernet.decrypt(encrypted)
    print("Bob (Classical): Decrypted message:")
    print(decrypted.decode())
