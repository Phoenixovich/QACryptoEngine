import socket
import random
import cirq

HOST = '127.0.0.1'
PORT = 65432

def measure_bit(bit, alice_basis, bob_basis):
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit()
    if bit == 1:
        circuit.append(cirq.X(q))
    if alice_basis == 'X':
        circuit.append(cirq.H(q))
    # Now Bob measures in his basis:
    if bob_basis == 'X':
        circuit.append(cirq.H(q))
    circuit.append(cirq.measure(q, key='m'))
    
    simulator = cirq.Simulator()
    result = simulator.run(circuit)
    return int(result.measurements['m'][0][0])

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("Bob: Connecting to Alice...")
        s.connect((HOST, PORT))
        
        bob_bases = []
        bob_results = []
        alice_bases = []

        # Receive 32 lines of data from Alice
        buffer = ""
        while len(bob_bases) < 32:
            data = s.recv(1024).decode('utf-8')
            buffer += data
            while '\n' in buffer and len(bob_bases) < 32:
                line, buffer = buffer.split('\n', 1)
                if line.strip() == '':
                    continue
                if '|' in line:
                    alice_basis, bit = line.split('|')
                    bit = int(bit)
                    alice_bases.append(alice_basis)
                    # Bob randomly picks basis
                    bob_basis = random.choice(['Z', 'X'])
                    bob_bases.append(bob_basis)
                    measured_bit = measure_bit(bit, alice_basis, bob_basis)
                    bob_results.append(measured_bit)
                    print(f"Bob measured bit {measured_bit} in basis {bob_basis}")

        # Send bob's bases back to Alice
        bases_message = ','.join(bob_bases)
        s.sendall(bases_message.encode('utf-8'))
        print("Bob: Bases sent for reconciliation")

        # Sift Bob's key to match Alice's sifted key
        sifted_indices = [i for i, (a, b) in enumerate(zip(alice_bases, bob_bases)) if a == b]
        sifted_key = [bob_results[i] for i in sifted_indices]

        # Wait for Alice's sample request and respond
        while True:
            data = s.recv(1024).decode('utf-8')
            if not data:
                break
            if data.startswith('SAMPLE:'):
                # Receive sample indices from Alice and prepare the sample
                sample_indices = list(map(int, data[len('SAMPLE:'):].strip().split(',')))
                sample_bits = [sifted_key[i] for i in sample_indices]

                # Send the sample back to Alice
                s.sendall((','.join(map(str, sample_bits)) + '\n').encode('utf-8'))

                # Remove sample from final key
                final_key = [str(sifted_key[i]) for i in range(len(sifted_key)) if i not in sample_indices]
                print("Bob's final key: ", ''.join(final_key))

        import hashlib
        # Existing: final_key is a list of '0'/'1' strings
        final_key_str = ''.join(final_key)  # e.g., "1010101..."

        # Hash it using SHA-256
        hashed_key = hashlib.sha256(final_key_str.encode('utf-8')).digest()

        # Save the hashed key to a file (Fernet expects base64)
        from cryptography.fernet import Fernet
        import base64

        fernet_key = base64.urlsafe_b64encode(hashed_key[:32])

        # Write it to a file
        with open("final_key_bob.txt", "wb") as f:  
            f.write(fernet_key)
            print("Final key saved to final_key_bob.txt")
if __name__ == "__main__":
    main()
