import sys
import os
import random
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QGridLayout, QSpinBox, QScrollArea, QVBoxLayout
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QTimer, QPointF, QThread, pyqtSignal
import subprocess
import psutil

class ScriptRunner(QThread):
    output_signal = pyqtSignal(str)
    def __init__(self, cmd, cwd=None):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.proc = None

    def run(self):
        self.proc = subprocess.Popen(
            self.cmd, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in self.proc.stdout:
            self.output_signal.emit(line.rstrip())
        self.proc.wait()

    def stop(self):
        if self.proc:
            self.proc.terminate()

class QKDGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Quantum-Assisted Cryptographic Engine')
        self.setFixedSize(1920, 1080)
        self.setup_ui()
        self.reset_qkd_state()
        self.message_anim = None
        self.classical_alice_runner = None
        self.classical_bob_runner = None
        self.mitm_mode = False
        self.mitm_intercept_box = None
        # Start classical processes in normal mode at launch
        QTimer.singleShot(0, lambda: self.restart_classical_processes(mitm_mode=False))

    def load_device_image(self, filename, fallback_color):
        label = QLabel('', self)
        label.setFixedSize(180, 180)
        img_path = os.path.join("extras", "images", filename)
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setStyleSheet('background: transparent;')
        else:
            label.setStyleSheet(f'background-color: %s; border: 3px solid #333;' % fallback_color)
        return label

    def setup_ui(self):
        self.layout = QGridLayout()
        self.setLayout(self.layout)

        # QKD Alice label above image
        self.qkd_alice_label = QLabel('QKD Alice', self)
        self.qkd_alice_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.qkd_alice_label, 0, 0)
        self.qkd_alice = self.load_device_image("qkd_alice.png", "#00bcd4")
        self.layout.addWidget(self.qkd_alice, 1, 0, Qt.AlignCenter)

        # QKD Bob label above image
        self.qkd_bob_label = QLabel('QKD Bob', self)
        self.qkd_bob_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.qkd_bob_label, 0, 2)
        self.qkd_bob = self.load_device_image("qkd_bob.png", "#00bcd4")
        self.layout.addWidget(self.qkd_bob, 1, 2, Qt.AlignCenter)

        # Classical Alice (label below image)
        self.classical_alice = self.load_device_image("classical_alice.png", "#ff9800")
        self.layout.addWidget(self.classical_alice, 3, 0, Qt.AlignCenter)
        self.classical_alice_label = QLabel('Classical Alice', self)
        self.classical_alice_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.classical_alice_label, 4, 0)

        # Classical Bob (label below image)
        self.classical_bob = self.load_device_image("classical_bob.png", "#ff9800")
        self.layout.addWidget(self.classical_bob, 3, 2, Qt.AlignCenter)
        self.classical_bob_label = QLabel('Classical Bob', self)
        self.classical_bob_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.classical_bob_label, 4, 2)

        # QKD Key display
        self.key_label = QLabel('QKD Key: (not generated)', self)
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setFont(QFont('Arial', 10))
        self.layout.addWidget(self.key_label, 2, 1)

        # QKD Generation button
        self.qkd_button = QPushButton('Generate QKD Key', self)
        self.qkd_button.clicked.connect(self.start_qkd_animation)
        self.layout.addWidget(self.qkd_button, 0, 1)

        # Vertical layout for numeric inputs
        self.num_inputs_widget = QWidget(self)
        self.num_inputs_layout = QVBoxLayout()
        self.num_inputs_widget.setLayout(self.num_inputs_layout)

        # Number of bits selector
        self.bits_spin = QSpinBox(self)
        self.bits_spin.setMinimum(8)
        self.bits_spin.setMaximum(256)
        self.bits_spin.setValue(32)
        self.bits_spin.setSingleStep(1)
        self.num_inputs_layout.addWidget(QLabel("QKD Bits:"))
        self.num_inputs_layout.addWidget(self.bits_spin)

        # Number of error bits selector
        self.error_spin = QSpinBox(self)
        self.error_spin.setMinimum(1)
        self.error_spin.setMaximum(32)
        self.error_spin.setValue(5)
        self.error_spin.setSingleStep(1)
        self.num_inputs_layout.addWidget(QLabel("Error Check Bits:"))
        self.num_inputs_layout.addWidget(self.error_spin)

        # Add the vertical widget to the grid layout
        self.layout.addWidget(self.num_inputs_widget, 0, 3, 2, 1)

        # Message input/output for Alice
        self.alice_msg_box = QTextEdit(self)
        self.alice_msg_box.setPlaceholderText('Enter message to send from Alice...')
        self.layout.addWidget(self.alice_msg_box, 5, 0)
        self.alice_send_btn = QPushButton('Send from Alice', self)
        self.alice_send_btn.clicked.connect(self.send_from_alice)
        self.layout.addWidget(self.alice_send_btn, 6, 0)
        # Message input/output for Bob
        self.bob_msg_box = QTextEdit(self)
        self.bob_msg_box.setPlaceholderText('Enter message to send from Bob...')
        self.layout.addWidget(self.bob_msg_box, 5, 2)
        self.bob_send_btn = QPushButton('Send from Bob', self)
        self.bob_send_btn.clicked.connect(self.send_from_bob)
        self.layout.addWidget(self.bob_send_btn, 6, 2)

        # Visualization area (scrollable)
        self.visualization = QLabel('', self)
        self.visualization.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.visualization.setWordWrap(True)
        self.visualization.setMinimumHeight(120)
        self.visualization.setFont(QFont('Arial', 12))

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.visualization)
        self.scroll_area.setFixedHeight(200)
        self.layout.addWidget(self.scroll_area, 7, 0, 1, 5)

        # MITM Button and label (centered between classical devices)
        self.mitm_widget = QWidget(self)
        self.mitm_layout = QVBoxLayout()
        self.mitm_widget.setLayout(self.mitm_layout)
        self.mitm_button = QPushButton('', self)
        self.mitm_button.setFixedSize(40, 40)
        self.mitm_button.setStyleSheet('background-color: #888; border-radius: 8px;')
        self.mitm_button.clicked.connect(self.toggle_mitm)
        self.mitm_label = QLabel('MITM: Off', self)
        self.mitm_label.setAlignment(Qt.AlignCenter)
        self.mitm_layout.addWidget(self.mitm_button, alignment=Qt.AlignCenter)
        self.mitm_layout.addWidget(self.mitm_label, alignment=Qt.AlignCenter)
        # MITM intercepted message box (scrollable)
        self.mitm_intercept_box = QTextEdit(self)
        self.mitm_intercept_box.setReadOnly(True)
        self.mitm_intercept_box.setFixedHeight(100)
        self.mitm_layout.addWidget(self.mitm_intercept_box, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.mitm_widget, 3, 1, alignment=Qt.AlignCenter)

        self.mitm_process = None

    def reset_qkd_state(self):
        self.qkd_step = 0
        self.qkd_bits = []
        self.qkd_bases_alice = []
        self.qkd_bases_bob = []
        self.qkd_bob_results = []
        self.qkd_sifted_indices = []
        self.qkd_sifted_key = []
        self.qkd_sample_indices = []
        self.qkd_sample_bits_alice = []
        self.qkd_sample_bits_bob = []
        self.qkd_final_key = []
        self.qkd_error_rate = 0.0
        self.key_label.setText('QKD Key: (not generated)')
        self.visualization.setText('')
        self.qkd_button.setEnabled(True)
        self.message_anim = None

    def start_qkd_animation(self):
        import os
        os.makedirs("extras", exist_ok=True)
        num_bits = self.bits_spin.value()
        error_bits = self.error_spin.value()
        with open("extras/qkd_config.txt", "w") as f:
            f.write("# QKD Configuration File\n")
            f.write(f"num_bits={num_bits}\n")
            f.write(f"error_bits={error_bits}\n")
        self.reset_qkd_state()
        self.qkd_button.setEnabled(False)
        self.visualization.setText(f'QKD protocol started. Generating {num_bits} random bits and {error_bits} error check bits...')
        # Wait for both key files to exist, then restart classical processes
        def wait_for_keys_and_restart():
            alice_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Alice", "final_key_alice.txt")
            bob_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Bob", "final_key_bob.txt")
            import time
            waited = 0
            while waited < 20:  # Wait up to 20 seconds
                if os.path.exists(alice_key) and os.path.exists(bob_key):
                    self.append_visualization("[Debug] QKD key files detected. Starting classical processes.")
                    QTimer.singleShot(0, lambda: self.restart_classical_processes(mitm_mode=self.mitm_mode))
                    return
                time.sleep(0.5)
                waited += 0.5
            self.append_visualization("[Debug] Timeout waiting for QKD key files! Classical processes not started.")
        import threading
        threading.Thread(target=wait_for_keys_and_restart, daemon=True).start()
        # Re-enable the QKD button after a short delay to allow regeneration
        QTimer.singleShot(2500, lambda: self.qkd_button.setEnabled(True))

    def append_visualization(self, text):
        current = self.visualization.text()
        self.visualization.setText(current + ("\n" if current else "") + text)
        self.visualization.repaint()
        # Use a single-shot timer to scroll after the event loop updates the layout
        QTimer.singleShot(0, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def qkd_animate_step(self):
        # Step 1: Show bit and basis generation
        if self.qkd_step < len(self.qkd_bits):
            idx = self.qkd_step
            msg = f"Alice generates bit[{idx}]: {self.qkd_bits[idx]}, basis: {self.qkd_bases_alice[idx]}"
            self.append_visualization(msg)
            msg2 = f"Bob chooses basis[{idx}]: {self.qkd_bases_bob[idx]}"
            self.append_visualization(msg2)
            # Simulate Bob's measurement (random for now)
            if self.qkd_bases_alice[idx] == self.qkd_bases_bob[idx]:
                measured = self.qkd_bits[idx]
                self.append_visualization(f"Bob measures and gets correct bit: {measured}")
            else:
                measured = random.randint(0, 1)
                self.append_visualization(f"Bob measures in wrong basis, gets random bit: {measured}")
            self.qkd_bob_results.append(measured)
            self.qkd_step += 1
            self.update()
            return

        # Step 2: Sifting
        if self.qkd_step == len(self.qkd_bits):
            self.append_visualization("Comparing bases and sifting key...")
            self.qkd_sifted_indices = [i for i in range(len(self.qkd_bits)) if self.qkd_bases_alice[i] == self.qkd_bases_bob[i]]
            self.qkd_sifted_key = [self.qkd_bits[i] for i in self.qkd_sifted_indices]
            self.append_visualization(f"Sifted key indices: {self.qkd_sifted_indices}")
            self.append_visualization(f"Sifted key: {''.join(map(str, self.qkd_sifted_key))}")
            self.qkd_step += 1
            self.update()
            return

        # Step 3: Error estimation
        if self.qkd_step == len(self.qkd_bits) + 1:
            self.append_visualization("Performing error estimation...")
            if len(self.qkd_sifted_key) < self.qkd_error_bits:
                self.append_visualization("Not enough sifted bits for error estimation. Aborting.")
                self.qkd_timer.stop()
                self.qkd_button.setEnabled(True)
                return
            self.qkd_sample_indices = random.sample(range(len(self.qkd_sifted_key)), self.qkd_error_bits)
            self.qkd_sample_bits_alice = [self.qkd_sifted_key[i] for i in self.qkd_sample_indices]
            self.qkd_sample_bits_bob = [self.qkd_bob_results[self.qd_sifted_indices[i]] for i in self.qkd_sample_indices]
            errors = sum(a != b for a, b in zip(self.qkd_sample_bits_alice, self.qkd_sample_bits_bob))
            self.qkd_error_rate = errors / self.qkd_error_bits
            self.append_visualization(
                f"Sample indices for error estimation: {self.qkd_sample_indices}\n"
                f"Alice's sample bits: {self.qkd_sample_bits_alice}\n"
                f"Bob's sample bits: {self.qkd_sample_bits_bob}\n"
                f"Errors: {errors}/{self.qkd_error_bits}, Error rate: {self.qkd_error_rate:.2f}"
            )
            self.qkd_step += 1
            self.update()
            return

        # Step 4: Final key extraction and transmission animation
        if self.qkd_step == len(self.qkd_bits) + 2:
            if self.qkd_error_rate > 0.2:
                self.append_visualization("Error rate too high! Possible eavesdropping. Aborting.")
                self.qkd_timer.stop()
                self.qkd_button.setEnabled(True)
                return
            # Remove sample bits from the key
            self.qkd_final_key = [self.qkd_sifted_key[i] for i in range(len(self.qkd_sifted_key)) if i not in self.qkd_sample_indices]
            self.key_label.setText(f"QKD Key: {''.join(map(str, self.qkd_final_key))}")
            self.append_visualization(f"Final key (after removing sample bits): {''.join(map(str, self.qkd_final_key))}")
            self.append_visualization("Hashing the key with SHA-256 and saving for encryption.")
            self.qkd_step += 1
            # Start key transmission animation
            self.animate_key_transmission()
            return

    def animate_key_transmission(self):
        # Animate a green circle moving from QKD Alice to QKD Bob to represent key sharing
        start = self.get_device_center(self.qkd_alice)
        end = self.get_device_center(self.qkd_bob)
        self.key_anim = {'start': start, 'end': end, 'pos': start, 'step': 0}
        self.key_timer = QTimer(self)
        self.key_timer.timeout.connect(self.update_key_anim)
        self.key_timer.start(30)
        self.append_visualization("Transmitting the final key from QKD Alice to QKD Bob...")

    def update_key_anim(self):
        anim = self.key_anim
        if anim['step'] >= 30:
            self.key_timer.stop()
            self.key_anim = None
            self.append_visualization("Key successfully shared between QKD Alice and QKD Bob!")
            self.visualization.repaint()
            return
        t = anim['step'] / 30
        x = anim['start'].x() + (anim['end'].x() - anim['start'].x()) * t
        y = anim['start'].y() + (anim['end'].y() - anim['start'].y()) * t
        anim['pos'] = QPointF(x, y)
        anim['step'] += 1
        self.update()

    def get_device_center(self, widget):
        # Returns the center point of a widget in window coordinates
        pos = widget.mapTo(self, widget.rect().center())
        return QPointF(pos)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0), 4)
        painter.setPen(pen)

        # Draw lines between QKD Alice <-> QKD Bob (quantum channel)
        p1 = self.get_device_center(self.qkd_alice)
        p2 = self.get_device_center(self.qkd_bob)
        painter.drawLine(p1, p2)

        # Draw lines between Classical Alice <-> Classical Bob (classical channel)
        p3 = self.get_device_center(self.classical_alice)
        p4 = self.get_device_center(self.classical_bob)
        painter.drawLine(p3, p4)

        # Draw lines QKD Alice <-> Classical Alice, QKD Bob <-> Classical Bob
        painter.drawLine(p1, p3)
        painter.drawLine(p2, p4)

        # Draw animated message if any (green circle)
        if self.message_anim:
            painter.setBrush(QColor(0, 200, 0))  # Green
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.message_anim['pos'], 18, 18)

        # Draw animated key transmission (green circle)
        if hasattr(self, 'key_anim') and self.key_anim:
            painter.setBrush(QColor(0, 200, 0))  # Green
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.key_anim['pos'], 18, 18)

    def animate_message(self, from_widget, to_widget, text, receiver_box):
        # Animate a message (circle) moving from from_widget to to_widget
        start = self.get_device_center(from_widget)
        end = self.get_device_center(to_widget)
        self.message_anim = {'start': start, 'end': end, 'pos': start, 'step': 0, 'text': text, 'receiver_box': receiver_box}
        self.msg_timer = QTimer(self)
        self.msg_timer.timeout.connect(self.update_message_anim)
        self.msg_timer.start(30)

    def update_message_anim(self):
        anim = self.message_anim
        if anim['step'] >= 30:
            self.msg_timer.stop()
            self.message_anim = None
            anim['receiver_box'].setText(f"Decrypted: {anim['text']}")
            self.visualization.setText(f"Message delivered: {anim['text']}")
            self.update()
            return
        t = anim['step'] / 30
        x = anim['start'].x() + (anim['end'].x() - anim['start'].x()) * t
        y = anim['start'].y() + (anim['end'].y() - anim['start'].y()) * t
        anim['pos'] = QPointF(x, y)
        anim['step'] += 1
        self.update()

    def start_qkd_processes(self):
        # Stop any previous QKD processes
        if hasattr(self, 'alice_runner') and self.alice_runner:
            self.alice_runner.terminate()
        if hasattr(self, 'bob_runner') and self.bob_runner:
            self.bob_runner.terminate()
        project_root = os.path.dirname(os.path.abspath(__file__))
        alice_dir = os.path.join(project_root, "Alice")
        bob_dir = os.path.join(project_root, "Bob")
        
        # Buffer for important QKD lines
        self.qkd_output_queue = []
        self.qkd_output_timer = QTimer(self)
        self.qkd_output_timer.setSingleShot(False)
        self.qkd_output_timer.timeout.connect(self._show_next_qkd_line)
        self.qkd_showing_qkd = False

        def is_important_qkd_line(line):
            keywords = [
                "Alice's bases", "Bob's bases", "Shared key:", "Error estimation:", "Error rate too high", "Final key:", "Not enough sifted bits", "Aborting."
            ]
            return any(k in line for k in keywords)

        def handle_alice_output(line):
            if is_important_qkd_line(line):
                self.qkd_output_queue.append(line)
                if not self.qkd_showing_qkd:
                    self.qkd_showing_qkd = True
                    self.qkd_output_timer.start(500)  # 500ms between lines
            if line.startswith("Final key: "):
                key = line.split(": ", 1)[1].strip()
                self.qkd_final_key = list(key)
                self.key_label.setText(f"QKD Key: {key}")

        def handle_bob_output(line):
            if is_important_qkd_line(line):
                self.qkd_output_queue.append(line)
                if not self.qkd_showing_qkd:
                    self.qkd_showing_qkd = True
                    self.qkd_output_timer.start(500)

        self.alice_runner = ScriptRunner(["python3", "alice.py"], cwd=alice_dir)
        self.bob_runner = ScriptRunner(["python3", "bob.py"], cwd=bob_dir)
        self.alice_runner.output_signal.connect(handle_alice_output)
        self.bob_runner.output_signal.connect(handle_bob_output)
        self.alice_runner.start()
        def start_bob():
            self.bob_runner = ScriptRunner(["python3", "bob.py"], cwd=bob_dir)
            self.bob_runner.output_signal.connect(handle_bob_output)
            self.bob_runner.start()
        QTimer.singleShot(1000, start_bob)

    def _show_next_qkd_line(self):
        if self.qkd_output_queue:
            line = self.qkd_output_queue.pop(0)
            self.append_visualization(line)
        else:
            self.qkd_output_timer.stop()
            self.qkd_showing_qkd = False

    def send_from_alice(self):
        project_root = os.path.dirname(os.path.abspath(__file__))
        msg = self.alice_msg_box.toPlainText()
        if msg.startswith("Decrypted: "):
            msg = msg[len("Decrypted: ") :]
        if msg and self.qkd_final_key:
            self.append_visualization(f'Alice encrypts and sends: "{msg}" to Bob')
            # Send message to already running classical Alice process via socket
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("127.0.0.1", 65433))  # Alice's server port
                s.sendall(msg.encode("utf-8"))
                s.close()
            except Exception as e:
                self.append_visualization(f"[Error] Could not send from Alice: {e}")
        else:
            self.visualization.setText("Generate a QKD key first!")

    def send_from_bob(self):
        project_root = os.path.dirname(os.path.abspath(__file__))
        msg = self.bob_msg_box.toPlainText()
        if msg.startswith("Decrypted: "):
            msg = msg[len("Decrypted: ") :]
        if msg and self.qkd_final_key:
            self.append_visualization(f'Bob encrypts and sends: "{msg}" to Alice')
            # Send message to already running classical Bob process via socket
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("127.0.0.1", 65434))  # Bob's server port
                s.sendall(msg.encode("utf-8"))
                s.close()
            except Exception as e:
                self.append_visualization(f"[Error] Could not send from Bob: {e}")
        else:
            self.visualization.setText("Generate a QKD key first!")

    def handle_mitm_output(self, line):
        if hasattr(self, 'mitm_intercept_box') and self.mitm_intercept_box:
            self.mitm_intercept_box.append(line)
            self.mitm_intercept_box.moveCursor(self.mitm_intercept_box.textCursor().End)
        self.append_visualization(f"MITM: {line}")

    def toggle_mitm(self):
        self.mitm_mode = not self.mitm_mode
        if self.mitm_mode:
            self.mitm_button.setStyleSheet('background-color: #e53935; border-radius: 8px;')
            self.mitm_label.setText('MITM: On')
            self.visualization.setText('MITM mode enabled. Restarting classical processes in MITM mode...')
            # Stop classical processes first
            self.restart_classical_processes(mitm_mode=True, for_mitm=True)
        else:
            self.mitm_button.setStyleSheet('background-color: #888; border-radius: 8px;')
            self.mitm_label.setText('MITM: Off')
            self.visualization.setText('MITM mode disabled. Restarting classical processes in normal mode...')
            if hasattr(self, 'mitm_runner') and self.mitm_runner:
                self.mitm_runner.terminate()
                self.mitm_runner = None
            # Wait for ports to be released, then restart classical processes
            QTimer.singleShot(2000, lambda: self.restart_classical_processes(mitm_mode=False))

    def restart_classical_processes(self, mitm_mode, for_mitm=False):
        # Stop any previous classical processes
        if hasattr(self, 'classical_alice_runner') and self.classical_alice_runner:
            self.classical_alice_runner.terminate()
            self.classical_alice_runner = None
        if hasattr(self, 'classical_bob_runner') and self.classical_bob_runner:
            self.classical_bob_runner.terminate()
            self.classical_bob_runner = None
        # Kill any lingering processes by name
        kill_process_by_name("classical_alice.py")
        kill_process_by_name("classical_bob.py")
        project_root = os.path.dirname(os.path.abspath(__file__))
        if not mitm_mode:
            # Start classical Alice
            args_alice = ["python3", "-u", "Alice/classical_alice.py"]
            self.classical_alice_runner = ScriptRunner(args_alice, cwd=project_root)
            self.classical_alice_runner.output_signal.connect(self.handle_classical_alice_output)
            self.classical_alice_runner.start()
            # Start classical Bob
            args_bob = ["python3", "-u", "Bob/classical_bob.py"]
            self.classical_bob_runner = ScriptRunner(args_bob, cwd=project_root)
            self.classical_bob_runner.output_signal.connect(self.handle_classical_bob_output)
            self.classical_bob_runner.start()
        elif for_mitm:
            # Wait for ports to be released, then start MITM
            QTimer.singleShot(2000, self._start_mitm_after_ports_free)

    def _start_mitm_after_ports_free(self):
        project_root = os.path.dirname(os.path.abspath(__file__))
        mitm_path = os.path.join(project_root, "MITM", "classical_mitm.py")
        if hasattr(self, 'mitm_runner') and self.mitm_runner:
            self.mitm_runner.terminate()
        self.mitm_runner = ScriptRunner(["python3", mitm_path], cwd=project_root)
        self.mitm_runner.output_signal.connect(self.handle_mitm_output)
        self.mitm_runner.start()

    def closeEvent(self, event):
        # Terminate all background processes
        if hasattr(self, 'mitm_runner') and self.mitm_runner:
            self.mitm_runner.stop()
        if hasattr(self, 'classical_alice_runner') and self.classical_alice_runner:
            self.classical_alice_runner.stop()
        if hasattr(self, 'classical_bob_runner') and self.classical_bob_runner:
            self.classical_bob_runner.stop()
        event.accept()

    def handle_classical_alice_output(self, line):
        self.append_visualization(f"Classical Alice: {line}")
        if line.startswith("[Alice] Received: "):
            try:
                msg = line.split(": ", 1)[1]
                msg = msg.split("\n")[0]
                self.alice_msg_box.setText(f"Decrypted: {msg}")
            except Exception:
                pass

    def handle_classical_bob_output(self, line):
        self.append_visualization(f"Classical Bob: {line}")
        if line.startswith("[Bob] Received: "):
            try:
                msg = line.split(": ", 1)[1]
                msg = msg.split("\n")[0]
                self.bob_msg_box.setText(f"Decrypted: {msg}")
            except Exception:
                pass

def kill_process_by_name(name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if not cmdline:
                continue
            if name in ' '.join(cmdline):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            continue

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = QKDGui()
    gui.show()
    sys.exit(app.exec_())
