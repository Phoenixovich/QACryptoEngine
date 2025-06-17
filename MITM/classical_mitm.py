import socket
import threading
import os
import sys
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

ALICE_HOST = '127.0.0.1'
ALICE_PORT = 65433
BOB_HOST = '127.0.0.1'
BOB_PORT = 65434

# Accept a single connection from Alice and Bob, then forward between them

def forward(src, dst, direction):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            print(f"MITM intercepted ({direction}): {data!r}")
            # MITM does not decrypt
            dst.sendall(data)
    except Exception as e:
        print(f"MITM forwarding error ({direction}): {e}")
    finally:
        try: dst.shutdown(socket.SHUT_WR)
        except: pass
        try: src.shutdown(socket.SHUT_RD)
        except: pass
        # Don't close sockets here; let the other thread finish

def handle_session(alice_conn, bob_conn):
    t1 = threading.Thread(target=forward, args=(alice_conn, bob_conn, "Alice->Bob"))
    t2 = threading.Thread(target=forward, args=(bob_conn, alice_conn, "Bob->Alice"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    alice_conn.close()
    bob_conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_alice, \
         socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_bob:
        s_alice.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_bob.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_alice.bind((ALICE_HOST, ALICE_PORT))
        s_bob.bind((BOB_HOST, BOB_PORT))
        s_alice.listen(5)
        s_bob.listen(5)
        print("MITM: Waiting for Alice and Bob to connect (multi-session mode)...")
        while True:
            print("MITM: Waiting for Alice...")
            alice_conn, alice_addr = s_alice.accept()
            print(f"MITM: Alice connected from {alice_addr}.")
            print("MITM: Waiting for Bob...")
            bob_conn, bob_addr = s_bob.accept()
            print(f"MITM: Bob connected from {bob_addr}.")
            threading.Thread(target=handle_session, args=(alice_conn, bob_conn), daemon=True).start()

if __name__ == "__main__":
    main()