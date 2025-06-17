import socket
import random
import time

HOST = '127.0.0.1'
PORT = 65432

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print("Alice: Waiting for Bob to connect...")
        conn, addr = s.accept()
        with conn:
            print('Alice: Connected by', addr)
            n = 32
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

            # Error estimation
            sifted_key = [int(k) for k in shared_key if k != 'x']

            # Select error estimation bit size
            ERROR_CHECK_BITS = 5
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

if __name__ == "__main__":
    main()
