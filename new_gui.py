import sys
import os
import random
import base64
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QGridLayout, QSpinBox, QScrollArea, QVBoxLayout
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QTimer, QPointF
from cryptography.fernet import Fernet

class QKDGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Quantum-Assisted Cryptographic Engine')
        self.setFixedSize(1920, 1080)
        self.setup_ui()
        self.reset_qkd_state()
        self.message_anim = None
        self.mitm_show_output = False

    def load_device_image(self, filename, fallback_color):
        label = QLabel('', self)
        label.setFixedSize(180, 180)
        img_path = os.path.join("extras", "images", filename)
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setStyleSheet('background: transparent;')
        else:
            label.setStyleSheet(f'background-color: {fallback_color}; border: 3px solid #333;')
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

        # Add encrypted message label below MITM button
        self.mitm_encrypted_label = QLabel('', self)
        self.mitm_encrypted_label.setAlignment(Qt.AlignCenter)
        self.mitm_encrypted_label.setWordWrap(True)
        self.mitm_encrypted_label.setFont(QFont('Arial', 10))
        self.mitm_layout.addWidget(self.mitm_encrypted_label, alignment=Qt.AlignCenter)

        self.layout.addWidget(self.mitm_widget, 3, 1, alignment=Qt.AlignCenter)

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
        self.fernet = None

    def start_qkd_animation(self):
        num_bits = self.bits_spin.value()
        error_bits = self.error_spin.value()
        self.reset_qkd_state()
        self.qkd_button.setEnabled(False)
        self.visualization.setText('Generating random bits and bases...')
        self.qkd_bits = [random.randint(0, 1) for _ in range(num_bits)]
        self.qkd_bases_alice = [random.choice(['Z', 'X']) for _ in range(num_bits)]
        self.qkd_bases_bob = [random.choice(['Z', 'X']) for _ in range(num_bits)]
        self.qkd_error_bits = error_bits
        self.qkd_step = 0
        self.qkd_bob_results = []
        self.qkd_sifted_indices = []
        self.qkd_sifted_key = []
        self.qkd_sample_indices = []
        self.qkd_sample_bits_alice = []
        self.qkd_sample_bits_bob = []
        self.qkd_final_key = []
        self.qkd_error_rate = 0.0
        self.qkd_timer = QTimer(self)
        self.qkd_timer.timeout.connect(self.qkd_animate_step)
        self.qkd_timer.start(500)

    def append_visualization(self, text):
        current = self.visualization.text()
        self.visualization.setText(current + ("\n" if current else "") + text)
        self.visualization.repaint()
        QTimer.singleShot(0, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def qkd_animate_step(self):
        if self.qkd_step < len(self.qkd_bits):
            idx = self.qkd_step
            msg = f"Alice generates bit[{idx}]: {self.qkd_bits[idx]}, basis: {self.qkd_bases_alice[idx]}"
            self.append_visualization(msg)
            msg2 = f"Bob chooses basis[{idx}]: {self.qkd_bases_bob[idx]}"
            self.append_visualization(msg2)
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

        if self.qkd_step == len(self.qkd_bits):
            self.append_visualization("Comparing bases and sifting key...")
            self.qkd_sifted_indices = [i for i in range(len(self.qkd_bits)) if self.qkd_bases_alice[i] == self.qkd_bases_bob[i]]
            self.qkd_sifted_key = [self.qkd_bits[i] for i in self.qkd_sifted_indices]
            self.append_visualization(f"Sifted key indices: {self.qkd_sifted_indices}")
            self.append_visualization(f"Sifted key: {''.join(map(str, self.qkd_sifted_key))}")
            self.qkd_step += 1
            self.update()
            return

        if self.qkd_step == len(self.qkd_bits) + 1:
            self.append_visualization("Performing error estimation...")
            if len(self.qkd_sifted_key) < self.qkd_error_bits:
                self.append_visualization("Not enough sifted bits for error estimation. Aborting.")
                self.qkd_timer.stop()
                self.qkd_button.setEnabled(True)
                return
            self.qkd_sample_indices = random.sample(range(len(self.qkd_sifted_key)), self.qkd_error_bits)
            self.qkd_sample_bits_alice = [self.qkd_sifted_key[i] for i in self.qkd_sample_indices]
            self.qkd_sample_bits_bob = [self.qkd_bob_results[self.qkd_sifted_indices[i]] for i in self.qkd_sample_indices]
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

        if self.qkd_step == len(self.qkd_bits) + 2:
            if self.qkd_error_rate > 0.2:
                self.append_visualization("Error rate too high! Possible eavesdropping. Aborting.")
                self.qkd_timer.stop()
                self.qkd_button.setEnabled(True)
                return
            self.qkd_final_key = [self.qkd_sifted_key[i] for i in range(len(self.qkd_sifted_key)) if i not in self.qkd_sample_indices]
            self.key_label.setText(f"QKD Key: {''.join(map(str, self.qkd_final_key))}")
            self.append_visualization(f"Final key (after removing sample bits): {''.join(map(str, self.qkd_final_key))}")
            self.append_visualization("Hashing the key with SHA-256 and saving for encryption.")
            # Prepare Fernet key
            key_bytes = int(''.join(map(str, self.qkd_final_key)), 2).to_bytes((len(self.qkd_final_key) + 7) // 8, byteorder='big')
            hashed = hashlib.sha256(key_bytes).digest()
            fernet_key = base64.urlsafe_b64encode(hashed)
            self.fernet = Fernet(fernet_key)
            self.qkd_step += 1
            self.animate_key_transmission()
            return

    def animate_key_transmission(self):
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
        pos = widget.mapTo(self, widget.rect().center())
        return QPointF(pos)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0), 4)
        painter.setPen(pen)
        p1 = self.get_device_center(self.qkd_alice)
        p2 = self.get_device_center(self.qkd_bob)
        painter.drawLine(p1, p2)
        p3 = self.get_device_center(self.classical_alice)
        p4 = self.get_device_center(self.classical_bob)
        painter.drawLine(p3, p4)
        painter.drawLine(p1, p3)
        painter.drawLine(p2, p4)
        if self.message_anim:
            painter.setBrush(QColor(0, 200, 0))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.message_anim['pos'], 18, 18)
        if hasattr(self, 'key_anim') and self.key_anim:
            painter.setBrush(QColor(0, 200, 0))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.key_anim['pos'], 18, 18)

    def animate_message(self, from_widget, to_widget, text, receiver_box, mitm=False):
        start = self.get_device_center(from_widget)
        end = self.get_device_center(to_widget)
        self.message_anim = {'start': start, 'end': end, 'pos': start, 'step': 0, 'text': text, 'receiver_box': receiver_box, 'mitm': mitm}
        self.msg_timer = QTimer(self)
        self.msg_timer.timeout.connect(self.update_message_anim)
        self.msg_timer.start(30)

    def update_message_anim(self):
        anim = self.message_anim
        if anim['step'] >= 30:
            self.msg_timer.stop()
            self.message_anim = None
            # Encrypt the message
            encrypted = self.fernet.encrypt(anim['text'].encode())
            # MITM interception: show encrypted message if MITM is active
            if anim['mitm'] and self.mitm_show_output:
                self.mitm_encrypted_label.setText(f"MITM intercepted (encrypted):\n{encrypted.decode()}")
            else:
                self.mitm_encrypted_label.setText("")
            # Decrypt and display
            decrypted = self.fernet.decrypt(encrypted).decode()
            anim['receiver_box'].setText(f"Decrypted: {decrypted}")
            self.visualization.setText(f"Message delivered: {decrypted}")
            self.update()
            return
        t = anim['step'] / 30
        x = anim['start'].x() + (anim['end'].x() - anim['start'].x()) * t
        y = anim['start'].y() + (anim['end'].y() - anim['start'].y()) * t
        anim['pos'] = QPointF(x, y)
        anim['step'] += 1
        self.update()

    def send_from_alice(self):
        msg = self.alice_msg_box.toPlainText()
        if msg.startswith("Decrypted: "):
            msg = msg[len("Decrypted: "):]
        if msg and self.fernet:
            self.append_visualization(f'Alice encrypts and sends: "{msg}" to Bob')
            self.animate_message(self.classical_alice, self.classical_bob, msg, self.bob_msg_box, mitm=self.mitm_show_output)
        else:
            self.visualization.setText("Generate a QKD key first!")

    def send_from_bob(self):
        msg = self.bob_msg_box.toPlainText()
        if msg.startswith("Decrypted: "):
            msg = msg[len("Decrypted: "):]
        if msg and self.fernet:
            self.append_visualization(f'Bob encrypts and sends: "{msg}" to Alice')
            self.animate_message(self.classical_bob, self.classical_alice, msg, self.alice_msg_box, mitm=self.mitm_show_output)
        else:
            self.visualization.setText("Generate a QKD key first!")

    def toggle_mitm(self):
        self.mitm_show_output = not self.mitm_show_output
        if self.mitm_show_output:
            self.mitm_button.setStyleSheet('background-color: #e53935; border-radius: 8px;')
            self.mitm_label.setText('MITM: On')
        else:
            self.mitm_button.setStyleSheet('background-color: #888; border-radius: 8px;')
            self.mitm_label.setText('MITM: Off')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = QKDGui()
    gui.show()
    sys.exit(app.exec_())