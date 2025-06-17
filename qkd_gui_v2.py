import sys
import os
import psutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QGridLayout, QSpinBox, QVBoxLayout
)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal

class ScriptRunner(QThread):
    output_signal = pyqtSignal(str)
    def __init__(self, cmd, cwd=None):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.proc = None

    def run(self):
        import subprocess
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        for line in self.proc.stdout:
            self.output_signal.emit(line.rstrip())
        self.proc.wait()

    def stop(self):
        if self.proc:
            self.proc.terminate()

    def send_stdin(self, msg):
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(msg + "\n")
                self.proc.stdin.flush()
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

class QKDControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Quantum-Assisted Cryptographic Engine')
        self.setFixedSize(1920, 1080)
        self.setup_ui()
        self.classical_alice_runner = None
        self.classical_bob_runner = None
        self.mitm_mode = False
        self.mitm_runner = None
        self.qkd_final_key = []
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
        # Decrypted output for Alice
        self.alice_decrypted_box = QTextEdit(self)
        self.alice_decrypted_box.setReadOnly(True)
        self.alice_decrypted_box.setPlaceholderText("Decrypted messages received by Alice")
        self.layout.addWidget(self.alice_decrypted_box, 7, 0)

        # Message input/output for Bob
        self.bob_msg_box = QTextEdit(self)
        self.bob_msg_box.setPlaceholderText('Enter message to send from Bob...')
        self.layout.addWidget(self.bob_msg_box, 5, 2)
        self.bob_send_btn = QPushButton('Send from Bob', self)
        self.bob_send_btn.clicked.connect(self.send_from_bob)
        self.layout.addWidget(self.bob_send_btn, 6, 2)
        # Decrypted output for Bob
        self.bob_decrypted_box = QTextEdit(self)
        self.bob_decrypted_box.setReadOnly(True)
        self.bob_decrypted_box.setPlaceholderText("Decrypted messages received by Bob")
        self.layout.addWidget(self.bob_decrypted_box, 7, 2)

        # Visualization area (scrollable, now QTextEdit)
        self.visualization = QTextEdit(self)
        self.visualization.setReadOnly(True)
        self.visualization.setFont(QFont('Arial', 12))
        self.visualization.setMinimumHeight(120)
        self.layout.addWidget(self.visualization, 8, 0, 1, 5)

        # MITM label and intercepted box in the grid as before
        self.mitm_label = QLabel('MITM: Off', self)
        self.mitm_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        # Add the label to the grid in the same cell as the button (row 5, col 1)
        self.layout.addWidget(self.mitm_label, 5, 1, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.mitm_intercept_box = QTextEdit(self)
        self.mitm_intercept_box.setReadOnly(True)
        self.mitm_intercept_box.setFixedHeight(100)
        self.layout.addWidget(self.mitm_intercept_box, 6, 1, alignment=Qt.AlignCenter)

        # MITM button as a floating widget (not in the grid)
        self.mitm_button = QPushButton('', self)
        self.mitm_button.setFixedSize(40, 40)
        self.mitm_button.setStyleSheet('background-color: #888; border-radius: 8px;')
        self.mitm_button.clicked.connect(self.toggle_mitm)
        self.mitm_button.raise_()

    def append_visualization(self, text):
        self.visualization.append(text)
        QTimer.singleShot(0, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.visualization.verticalScrollBar().setValue(self.visualization.verticalScrollBar().maximum())

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor("#333"), 4)
        painter.setPen(pen)

        def center(widget):
            pos = widget.mapTo(self, widget.rect().topLeft())
            return QPoint(pos.x() + widget.width() // 2, pos.y() + widget.height() // 2)

        # Draw lines between QKD Alice <-> QKD Bob
        painter.drawLine(center(self.qkd_alice), center(self.qkd_bob))
        # Draw lines between Classical Alice <-> Classical Bob
        painter.drawLine(center(self.classical_alice), center(self.classical_bob))
        # Draw lines QKD Alice <-> Classical Alice, QKD Bob <-> Classical Bob
        painter.drawLine(center(self.qkd_alice), center(self.classical_alice))
        painter.drawLine(center(self.qkd_bob), center(self.classical_bob))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Center the MITM button on the line between classical Alice and Bob
        a_center = self.classical_alice.mapToGlobal(self.classical_alice.rect().center())
        b_center = self.classical_bob.mapToGlobal(self.classical_bob.rect().center())
        mid_x = (a_center.x() + b_center.x()) // 2
        mid_y = (a_center.y() + b_center.y()) // 2
        mid = self.mapFromGlobal(QPoint(mid_x, mid_y))
        # Move MITM button
        btn_x = int(mid.x() - self.mitm_button.width() / 2)
        btn_y = int(mid.y() - self.mitm_button.height() / 2)
        self.mitm_button.move(btn_x, btn_y)
        # Move MITM label just below the button using the button's geometry
        # label_x = btn_x + (self.mitm_button.width() - self.mitm_label.width()) // 2
        # label_y = btn_y + self.mitm_button.height() + 5  # 5px gap below button
        # self.mitm_label.move(label_x, label_y)
        # Resize and move MITM intercepted box to span from top of send box to bottom of receive box
        send_top = min(
            self.alice_msg_box.mapTo(self, self.alice_msg_box.rect().topLeft()).y(),
            self.bob_msg_box.mapTo(self, self.bob_msg_box.rect().topLeft()).y()
        )
        recv_bottom = max(
            self.alice_decrypted_box.mapTo(self, self.alice_decrypted_box.rect().bottomLeft()).y(),
            self.bob_decrypted_box.mapTo(self, self.bob_decrypted_box.rect().bottomLeft()).y()
        )
        box_height = recv_bottom - send_top
        box_width = 220
        box_x = mid.x() - box_width // 2
        self.mitm_intercept_box.setGeometry(
            int(box_x),
            int(send_top),
            int(box_width),
            int(box_height)
        )
        self.mitm_label.setStyleSheet("padding-top: 50px;")  # Adjust 50px as needed for your button size

    def start_qkd_animation(self):
        kill_process_by_name("alice.py")
        kill_process_by_name("bob.py")
        QTimer.singleShot(500, self._do_qkd_generation)

    def _do_qkd_generation(self):
        os.makedirs("extras", exist_ok=True)
        num_bits = self.bits_spin.value()
        error_bits = self.error_spin.value()
        with open("extras/qkd_config.txt", "w") as f:
            f.write("# QKD Configuration File\n")
            f.write(f"num_bits={num_bits}\n")
            f.write(f"error_bits={error_bits}\n")
        self.key_label.setText('QKD Key: (not generated)')
        self.visualization.clear()
        self.visualization.append(f'QKD protocol started. Generating {num_bits} random bits and {error_bits} error check bits...')
        alice_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Alice")
        bob_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Bob")
        self.qkd_alice_runner = ScriptRunner(["python3", "-u", "alice.py"], cwd=alice_dir)
        self.qkd_bob_runner = ScriptRunner(["python3", "-u", "bob.py"], cwd=bob_dir)
        self.qkd_alice_runner.output_signal.connect(lambda line: self.visualization.append("[QKD Alice] " + line))
        self.qkd_bob_runner.output_signal.connect(lambda line: self.visualization.append("[QKD Bob] " + line))
        self.qkd_alice_runner.start()
        self.qkd_bob_runner.start()
        QTimer.singleShot(2500, self.update_key_label)

    def update_key_label(self):
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Alice", "final_key_alice.txt")
        if os.path.exists(key_path):
            with open(key_path) as f:
                key = f.read().strip()
            self.key_label.setText(f"QKD Key: {key}")
        else:
            self.key_label.setText("QKD Key: (not generated)")

    def send_from_alice(self):
        msg = self.alice_msg_box.toPlainText().strip()
        if msg:
            self.append_visualization(f'Alice encrypts and sends: "{msg}" to Bob')
            if self.classical_alice_runner:
                self.classical_alice_runner.send_stdin(msg)

    def send_from_bob(self):
        msg = self.bob_msg_box.toPlainText().strip()
        if msg:
            self.append_visualization(f'Bob encrypts and sends: "{msg}" to Alice')
            if self.classical_bob_runner:
                self.classical_bob_runner.send_stdin(msg)

    def handle_mitm_output(self, line):
        # Always append MITM output to the intercepted box
        if hasattr(self, 'mitm_intercept_box') and self.mitm_intercept_box:
            self.mitm_intercept_box.append(line)
            self.mitm_intercept_box.moveCursor(self.mitm_intercept_box.textCursor().End)
        # Optionally, also show in the visualization area
        self.append_visualization(f"MITM: {line}")

    def toggle_mitm(self):
        self.mitm_mode = not self.mitm_mode
        self.visualization.clear()
        if self.mitm_mode:
            self.mitm_button.setStyleSheet('background-color: #e53935; border-radius: 8px;')
            self.mitm_label.setText('MITM: On')
            self.append_visualization('MITM mode enabled. Restarting classical processes in MITM mode...')
            self.restart_classical_processes(mitm_mode=True)
        else:
            self.mitm_button.setStyleSheet('background-color: #888; border-radius: 8px;')
            self.mitm_label.setText('MITM: Off')
            self.append_visualization('MITM mode disabled. Restarting classical processes in normal mode...')
            if self.mitm_runner:
                self.mitm_runner.stop()
                self.mitm_runner = None
            QTimer.singleShot(2000, lambda: self.restart_classical_processes(mitm_mode=False))

    def restart_classical_processes(self, mitm_mode=False):
        if self.classical_alice_runner:
            self.classical_alice_runner.stop()
            self.classical_alice_runner = None
        if self.classical_bob_runner:
            self.classical_bob_runner.stop()
            self.classical_bob_runner = None
        kill_process_by_name("classical_alice.py")
        kill_process_by_name("classical_bob.py")
        project_root = os.path.dirname(os.path.abspath(__file__))
        alice_dir = os.path.join(project_root, "Alice")
        bob_dir = os.path.join(project_root, "Bob")
        alice_cmd = ["python3", "-u", "classical_alice.py"]
        bob_cmd = ["python3", "-u", "classical_bob.py"]
        if mitm_mode:
            alice_cmd.append("--mitm")
            bob_cmd.append("--mitm")
            # Start MITM process
            mitm_dir = os.path.join(project_root, "MITM")
            mitm_cmd = ["python3", "-u", "classical_mitm.py"]
            if self.mitm_runner:
                self.mitm_runner.stop()
            self.mitm_runner = ScriptRunner(mitm_cmd, cwd=mitm_dir)
            self.mitm_runner.output_signal.connect(self.handle_mitm_output)
            self.mitm_runner.start()
            QTimer.singleShot(1500, lambda: self._start_classical(alice_cmd, bob_cmd, alice_dir, bob_dir))
        else:
            if self.mitm_runner:
                self.mitm_runner.stop()
                self.mitm_runner = None
            self._start_classical(alice_cmd, bob_cmd, alice_dir, bob_dir)

    def _start_classical(self, alice_cmd, bob_cmd, alice_dir, bob_dir):
        self.classical_alice_runner = ScriptRunner(alice_cmd, cwd=alice_dir)
        self.classical_bob_runner = ScriptRunner(bob_cmd, cwd=bob_dir)
        self.classical_alice_runner.output_signal.connect(self.handle_classical_alice_output)
        self.classical_bob_runner.output_signal.connect(self.handle_classical_bob_output)
        self.classical_alice_runner.start()
        self.classical_bob_runner.start()

    def closeEvent(self, event):
        if self.mitm_runner:
            self.mitm_runner.stop()
        if self.classical_alice_runner:
            self.classical_alice_runner.stop()
        if self.classical_bob_runner:
            self.classical_bob_runner.stop()
        event.accept()

    def handle_classical_alice_output(self, line):
        self.append_visualization(f"Classical Alice: {line}")
        if "[Alice] Received:" in line:
            msg = line.split(":", 1)[1].strip()
            self.alice_decrypted_box.append(msg)

    def handle_classical_bob_output(self, line):
        self.append_visualization(f"Classical Bob: {line}")
        if "[Bob] Received:" in line:
            msg = line.split(":", 1)[1].strip()
            self.bob_decrypted_box.append(msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = QKDControlGUI()
    gui.show()
    sys.exit(app.exec_())