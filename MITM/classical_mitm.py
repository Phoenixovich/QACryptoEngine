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

# Configuration
ALICE_HOST = '127.0.0.1'
ALICE_PORT = 65433
BOB_HOST = '127.0.0.1'
BOB_PORT = 65434  # MITM will forward to Bob on a different port

def forward(src, dst, direction):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            print(f"MITM intercepted ({direction}): {data!r}")
            # Optionally modify data here
            dst.sendall(data)
    except Exception as e:
        print(f"MITM forwarding error ({direction}): {e}")
    finally:
        try: src.shutdown(socket.SHUT_RD)
        except: pass
        try: dst.shutdown(socket.SHUT_WR)
        except: pass
        src.close()
        dst.close()

def handle_session(alice_conn, bob_conn):
    t1 = threading.Thread(target=forward, args=(alice_conn, bob_conn, "Alice->Bob"))
    t2 = threading.Thread(target=forward, args=(bob_conn, alice_conn, "Bob->Alice"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_alice:
        s_alice.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_alice.bind((ALICE_HOST, ALICE_PORT))
        s_alice.listen(5)
        print("MITM: Waiting for Alice to connect (multi-session mode)...")
        while True:
            alice_conn, alice_addr = s_alice.accept()
            print(f"MITM: Alice connected from {alice_addr}.")
            try:
                s_bob = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s_bob.connect((BOB_HOST, BOB_PORT))
                print("MITM: Connected to Bob.")
                threading.Thread(target=handle_session, args=(alice_conn, s_bob), daemon=True).start()
            except Exception as e:
                print(f"MITM: Failed to connect to Bob: {e}")
                alice_conn.close()

if __name__ == "__main__":
    main()