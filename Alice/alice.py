import socket
import random
import time
import hashlib
from cryptography.fernet import Fernet
import base64
import os
import cirq

HOST = '127.0.0.1'
PORT = 65432

def prepare_qubit(bit, basis):
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit()
    if bit == 1:
        circuit.append(cirq.X(q))
    if basis == 'X':
        circuit.append(cirq.H(q))
    # No measurement here; just return the circuit and qubit
    return circuit, q

def main():
    # Read config
    n = 32  # fallback default
    ERROR_CHECK_BITS = 5  # fallback default
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../extras/qkd_config.txt")
    try:
        with open(config_path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                if line.startswith("num_bits="):
                    n = int(line.strip().split("=")[1])
                if line.startswith("error_bits="):
                    ERROR_CHECK_BITS = int(line.strip().split("=")[1])
    except Exception:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print("Alice: Waiting for Bob to connect...")
        conn, addr = s.accept()
        with conn:
            print('Alice: Connected by', addr)
            alice_bits = [random.randint(0,1) for _ in range(n)]
            alice_bases = [random.choice(['Z', 'X']) for _ in range(n)]

            # Prepare qubits using Cirq and send basis/bit to Bob
            for bit, basis in zip(alice_bits, alice_bases):
                circuit, q = prepare_qubit(bit, basis)
                # Simulate the state preparation (no measurement)
                simulator = cirq.Simulator()
                result = simulator.simulate(circuit)
                # For protocol, send basis and bit (as before)
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

            # Error estimation
            sifted_key = [int(k) for k in shared_key if k != 'x']
            # Use ERROR_CHECK_BITS from config
            if len(sifted_key) < ERROR_CHECK_BITS:
                print("Not enough sifted bits for error estimation. Aborting.")
                return
            
            # Select indices for error estimation
            sample_indices = random.sample(range(len(sifted_key)), ERROR_CHECK_BITS)
            sample_bits = [sifted_key[i] for i in sample_indices]

            # Send sample indices to Bob
            conn.sendall(('SAMPLE:' + ','.join(map(str, sample_indices)) + '\n').encode('utf-8'))

            # Receive Bob's bits
            bob_sample_bytes = conn.recv(1024)
            bob_sample_bits = list(map(int, bob_sample_bytes.decode('utf-8').strip().split(',')))

            # Error rate
            errors = sum(a != b for a, b in zip(sample_bits, bob_sample_bits))
            error_rate = errors / ERROR_CHECK_BITS
            print(f"Error estimation: {errors} errors out of {ERROR_CHECK_BITS} samples (rate: {error_rate:.2f})")
            if error_rate > 0.2:
                print("Error rate too high! Possible eavesdropping. Aborting.")
                return
            
            # Remove sample bits from the final key
            final_key = [str(sifted_key[i]) for i in range(len(sifted_key)) if i not in sample_indices]
            print("Final key: ", ''.join(final_key))

        # Existing: final_key is a list of '0'/'1' strings
        final_key_str = ''.join(final_key)  # e.g., "1010101..."

        # Hash it using SHA-256
        hashed_key = hashlib.sha256(final_key_str.encode('utf-8')).digest()

        # Save the hashed key to a file (Fernet expects base64)
        fernet_key = base64.urlsafe_b64encode(hashed_key[:32])  # Fernet needs 32-byte key

        # Write it to a file
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_key_alice.txt")
        with open(key_path, "w") as f:
            f.write("".join(final_key))
            print("Final key saved to final_key_alice.txt")
if __name__ == "__main__":
    main()
