import sys
import sounddevice as sd
import numpy as np
import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QHBoxLayout, QProgressBar
)
from diagnosis_window import DiagnosisWindow
import pyaudio


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio/Video Setup")
        self.setFixedSize(400, 520)

        layout = QVBoxLayout()

        # Webcam preview
        self.camera_label = QLabel("Webcam Preview")
        self.camera_label.setFixedSize(360, 240)
        self.camera_label.setStyleSheet("background-color: black;")
        self.camera_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.camera_label)

        # Webcam selection
        layout.addWidget(QLabel("Select Webcam:"))
        self.video_combo = QComboBox()
        self.video_combo.addItems(["Camera 0", "Camera 1"])
        self.video_combo.currentIndexChanged.connect(self.update_camera_source)
        layout.addWidget(self.video_combo)

        # Microphone selection
        layout.addWidget(QLabel("Select Microphone:"))
        self.mic_combo = QComboBox()
        layout.addWidget(self.mic_combo)

        # Microphone level indicator
        self.mic_level = QProgressBar()
        self.mic_level.setRange(0, 100)
        layout.addWidget(self.mic_level)

        # Speaker selection
        layout.addWidget(QLabel("Select Speaker:"))
        self.speaker_combo = QComboBox()
        layout.addWidget(self.speaker_combo)

        # Buttons
        button_row = QHBoxLayout()
        self.test_button = QPushButton("Test Microphone")
        self.test_button.clicked.connect(self.test_microphone)
        self.speaker_test_button = QPushButton("Test Speaker")
        self.speaker_test_button.clicked.connect(self.test_speaker)
        self.start_button = QPushButton("Start Diagnosis")
        self.start_button.clicked.connect(self.start_diagnosis)
        button_row.addWidget(self.test_button)
        button_row.addWidget(self.speaker_test_button)
        button_row.addWidget(self.start_button)
        layout.addLayout(button_row)

        self.setLayout(layout)

        # Webcam setup
        self.capture = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera_frame)
        self.update_camera_source()
        self.timer.start(30)

        # Audio setup
        self.audio_stream = None
        self.mic_volume = 0
        self.mic_timer = QTimer()
        self.mic_timer.timeout.connect(self.update_mic_level_ui)

        self.populate_audio_devices()

    def populate_audio_devices(self):
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                self.mic_combo.addItem(f"{dev['name']}", idx)
            if dev['max_output_channels'] > 0:
                self.speaker_combo.addItem(f"{dev['name']}", idx)

    def update_camera_source(self):
        index = self.video_combo.currentIndex()
        if self.capture:
            self.capture.release()
        self.capture = cv2.VideoCapture(index)

    def update_camera_frame(self):
        if self.capture and self.capture.isOpened():
            ret, frame = self.capture.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], QImage.Format_RGB888)
                self.camera_label.setPixmap(QPixmap.fromImage(image))

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        volume_norm = int(np.linalg.norm(indata) * 100)
        self.mic_volume = min(volume_norm, 100)  # store only

    def update_mic_level_ui(self):
        self.mic_level.setValue(self.mic_volume)

    def test_microphone(self):
        mic_index = self.mic_combo.currentData()
        if mic_index is None:
            print("[ERROR] No microphone selected.")
            return

        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.mic_timer.stop()

        try:
            self.audio_stream = sd.InputStream(
                device=mic_index,
                channels=1,
                callback=self.audio_callback
            )
            self.audio_stream.start()
            self.mic_timer.start(50)  # update UI every 50ms
        except Exception as e:
            print(f"[ERROR] Could not start microphone test: {e}")

    def test_speaker(self):
        speaker_index = self.speaker_combo.currentData()
        if speaker_index is None:
            print("[ERROR] No speaker selected.")
            return

        samplerate = 44100
        duration = 1.0  # seconds
        frequency = 440  # Hz
        t = np.linspace(0, duration, int(samplerate * duration), False)
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)
        try:
            sd.play(tone, samplerate=samplerate, device=speaker_index)
            sd.wait()
        except Exception as e:
            print(f"[ERROR] Could not play test tone: {e}")

    def start_diagnosis(self):
        selected_mic = self.mic_combo.currentData()
        selected_camera = self.video_combo.currentIndex()
        print(f"[DEBUG] Starting Diagnosis with Mic Index {selected_mic} and Camera Index {selected_camera}")

        self.diagnosis = DiagnosisWindow(mic_index=selected_mic, camera_index=selected_camera)
        self.diagnosis.show()
        self.close()

    def closeEvent(self, event):
        if self.capture:
            self.capture.release()
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
        self.mic_timer.stop()
        self.timer.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec_())
