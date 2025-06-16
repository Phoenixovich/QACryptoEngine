import cirq
import numpy as np

# Number of bits (qubits) we want to use to generate the key
num_bits = 32

# STEP 1: ALICE'S PREPARATION

# Alice randomly chooses her key bits (0 or 1)
alice_bits = np.random.randint(2, size=num_bits)

# Alice also randomly chooses which basis to use for each bit:
# 0 = standard basis (Z), 1 = diagonal basis (X / Hadamard)
alice_bases = np.random.randint(2, size=num_bits)

# Bob also randomly chooses which basis he'll use to measure each qubit
bob_bases = np.random.randint(2, size=num_bits)

# Prepare 32 linearly arranged qubits
qubits = [cirq.LineQubit(i) for i in range(num_bits)]

# Create a quantum circuit
circuit = cirq.Circuit()

# STEP 2: ENCODING BY ALICE

for i in range(num_bits):
    # If Alice wants to send a 1, apply an X gate (flips 0 to 1)
    if alice_bits[i] == 1:
        circuit.append(cirq.X(qubits[i]))
    
    # If using diagonal basis, apply Hadamard gate (creates superposition)
    if alice_bases[i] == 1:
        circuit.append(cirq.H(qubits[i]))

# STEP 3: MEASUREMENT BY BOB

for i in range(num_bits):
    # If Bob is measuring in diagonal basis, apply Hadamard before measuring
    if bob_bases[i] == 1:
        circuit.append(cirq.H(qubits[i]))  # This puts it into Z basis for measurement
    
    # Measure each qubit and label it 'bit{i}'
    circuit.append(cirq.measure(qubits[i], key=f'bit{i}'))

# STEP 4: SIMULATION

# Create a simulator to run the quantum circuit
simulator = cirq.Simulator()

# Run the circuit and store the measurement results
result = simulator.run(circuit)

# Extract Bob's measurement results as an array of integers
# Each result is a single value from a 1-element array, so we use .item() to get the scalar
bob_results = np.array([result.measurements[f'bit{i}'].item() for i in range(num_bits)])

# STEP 5: SIFTING THE KEY

# Only keep bits where Alice and Bob used the same basis
sifted_key = [int(bob_results[i]) for i in range(num_bits) if alice_bases[i] == bob_bases[i]]

# STEP 6: OUTPUT THE RESULTS

print(f"Alice's Bits       : {alice_bits}")
print(f"Alice's Bases      : {alice_bases}")
print(f"Bob's Bases        : {bob_bases}")
print(f"Bob's Measurements : {bob_results}")
print(f"Sifted Key         : {sifted_key}")
