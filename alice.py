import socket
import random
import time

HOST = '127.0.0.1'
PORT = 65432

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("Alice: Waiting for Bob to connect...")
        conn, addr = s.accept()
        with conn:
            print('Alice: Connected by', addr)
            n = 10
            alice_bits = [random.randint(0,1) for _ in range(n)]
            alice_bases = [random.choice(['Z', 'X']) for _ in range(n)]
            
            # Send bit and basis line by line
            for bit, basis in zip(alice_bits, alice_bases):
                message = f"{basis}|{bit}\n"
                conn.sendall(message.encode('utf-8'))
                time.sleep(0.1)
            
            # Receive Bob's bases
            bob_bases_bytes = conn.recv(1024)
            bob_bases = bob_bases_bytes.decode('utf-8').strip().split(',')
            
            shared_key = []
            for a_bit, a_basis, b_basis in zip(alice_bits, alice_bases, bob_bases):
                if a_basis == b_basis:
                    shared_key.append(str(a_bit))
                else:
                    shared_key.append('x')
            
            print("Alice's bases: ", alice_bases)
            print("Bob's bases:   ", bob_bases)
            print("Shared key:    ", ''.join(k for k in shared_key if k != 'x'))

if __name__ == "__main__":
    main()
