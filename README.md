# QACryptoEngine
Quantum-Assisted Cryptographic Engine - by NoCloningAllowed Team during the RoNaQCI Quantum Hackathon

## Quantum Key Distribution (QKD) Scripts

This project includes a simulation of the BB84 Quantum Key Distribution protocol using Python scripts for Alice and Bob.

### How it Works

- **Alice (`Alice/alice.py`)** acts as the sender/server. She generates a random sequence of bits and bases, sends them to Bob, and performs basis reconciliation, error estimation, and key sifting.
- **Bob (`Bob/bob.py`)** acts as the receiver/client. He receives Alice’s bits and bases, measures them in randomly chosen bases, and participates in basis reconciliation and error estimation.

### Protocol Steps

1. **Preparation:**  
   Alice generates `n` random bits and random bases (Z or X). Bob also randomly chooses his measurement bases.

2. **Quantum Transmission (Simulated):**  
   Alice sends each bit and its basis to Bob over a socket connection.

3. **Measurement:**  
   Bob simulates quantum measurement using Cirq, records his results, and sends his chosen bases back to Alice.

4. **Key Sifting:**  
   Both keep only the bits where their bases matched.

5. **Error Estimation:**  
   Alice randomly selects a subset of the sifted key and asks Bob to reveal his corresponding bits. If the error rate is low, the remaining bits form the final shared key.

6. **Key Output:**  
   The final key can be used for classical encryption or further cryptographic protocols.

### Usage

1. Start Alice’s script:
   ```bash
   python Alice/alice.py
   ```
2. Start Bob’s script in another terminal:
   ```bash
   python Bob/bob.py
   ```

Both scripts will display protocol progress and output the final shared key.


