# Quantum-Assisted Cryptographic Engine

## Overview

This project is a graphical simulation and demonstration of a quantum-assisted cryptographic communication system. It features a PyQt5-based GUI that visually represents the flow of quantum and classical information between Alice and Bob, with optional Man-In-The-Middle (MITM) interception. The system integrates quantum key distribution (QKD) and classical encrypted messaging, allowing for interactive experimentation and visualization.

---

## Features

- **Quantum Key Distribution (QKD):**  
  Simulates QKD between Alice and Bob, generating a shared secret key using quantum protocols.
- **Classical Encrypted Messaging:**  
  Alice and Bob can exchange encrypted messages using the generated QKD key.
- **Man-In-The-Middle (MITM) Simulation:**  
  Activate MITM mode to see intercepted messages and how the system responds to eavesdropping.
- **Live Visualization:**  
  All protocol steps, messages, and MITM activity are visualized in real time.
- **Interactive GUI:**  
  Send messages, generate new keys, and toggle MITM mode with a user-friendly interface.
- **Process Management:**  
  The GUI manages all Alice, Bob, and MITM processes, ensuring ports are free and processes are restarted as needed.
- **Device-Centric Layout:**  
  Each device (QKD Alice, QKD Bob, Classical Alice, Classical Bob) is visually represented with images and message boxes.
- **Lines Between Devices:**  
  Visual lines connect the devices, showing the logical and physical flow of information.
- **MITM Output Panel:**  
  MITM intercepted messages are displayed in a dedicated panel spanning the communication channel.

---

## Project Structure

```
quantum/
├── QACryptoEngine/
│   ├── qkd_gui_v2.py         # Main GUI application
│   ├── Alice/
│   │   ├── alice.py
│   │   └── classical_alice.py
│   ├── Bob/
│   │   ├── bob.py
│   │   └── classical_bob.py
│   ├── MITM/
│   │   └── classical_mitm.py
│   └── extras/
│       └── images/           # Device images
│       └── qkd_config.txt    # QKD configuration file
```

---

## How It Works

1. **Startup:**  
   The GUI launches and starts the classical Alice and Bob scripts as subprocesses, each listening for messages and reading from stdin.
2. **QKD Key Generation:**  
   Click "Generate QKD Key" to run the QKD protocol between Alice and Bob. The shared key is displayed in the GUI.
3. **Sending Messages:**  
   Type a message in Alice's or Bob's input box and click "Send". The message is sent to the respective script's stdin, encrypted, and transmitted to the other party.
4. **Receiving Messages:**  
   When a message is received and decrypted, it appears in the "Decrypted messages" box below the corresponding device.
5. **MITM Mode:**  
   Toggle MITM mode to start the MITM process. Intercepted messages are displayed in the MITM panel, and the GUI visually indicates MITM activity.
6. **Visualization:**  
   All protocol steps, messages, and MITM events are logged in the visualization area for easy tracking.

---

## Usage

### Prerequisites

- Python 3.7+
- PyQt5
- cryptography
- psutil

Install dependencies:
```bash
pip install pyqt5 cryptography psutil
```

### Running the Application

```bash
cd QACryptoEngine
python3 qkd_gui_v2.py
```

### Controls

- **Generate QKD Key:**  
  Starts a new QKD session and updates the shared key.
- **Send from Alice/Bob:**  
  Sends the message in the input box through the running script.
- **MITM Toggle:**  
  Enables/disables MITM mode. Intercepted messages appear in the MITM panel.
- **QKD Bits/Error Check Bits:**  
  Configure the number of bits for QKD and error checking.

---

## Credits

- Developed by [No Cloning Allowed Team]
- Quantum protocol logic inspired by standard QKD protocols (e.g., BB84)
- GUI built with PyQt5

---

## License

MIT License


