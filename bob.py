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
        
        # Receive 10 lines of data from Alice
        buffer = ""
        while len(bob_bases) < 10:
            data = s.recv(1024).decode('utf-8')
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip() == '':
                    continue
                alice_basis, bit = line.split('|')
                bit = int(bit)
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

if __name__ == "__main__":
    main()
