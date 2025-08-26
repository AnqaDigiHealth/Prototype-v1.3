# diagnosis_window.py

import cv2
import threading
import json
import uuid
import random
import logging
import numpy as np
import speech_recognition as sr

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog,
    QComboBox, QDialogButtonBox, QApplication, QLineEdit
)
from PyQt5.QtCore import Qt, QTimer, QEventLoop, QUrl, QPointF, pyqtSignal, QThread
from PyQt5.QtGui  import QImage, QPixmap, QPainter, QColor, QPen, QPolygonF
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from TTS.api import TTS
from gptoss_client import chat
from neural_adhd_guidance import evaluate_answer_traits

logging.basicConfig(level=logging.DEBUG)
logging.debug("diagnosis_window loaded")

# ───────────────────────────────────────────────────────────────────────────────
# Interview content
# (Kept inline for simplicity; identical structure to your original file.)
# ───────────────────────────────────────────────────────────────────────────────
interview_data = [
    {
        "intro": "Let’s start with your ability to focus, sustain attention, and organize tasks. I’ll ask about your experiences over the past six months.",
        "questions": [
            "How often do you make mistakes in tasks because you overlooked details?",
            "Do you frequently miss parts of instructions even when they’re clearly explained?",
            "Do you struggle to stay focused when reading, even if the material interests you?",
            "Do you often lose track of what you were doing when working on tasks?",
            "How often do you find yourself re-reading the same line of text multiple times?",
            "Do you regularly have difficulty following conversations in noisy or busy environments?",
            "Do you frequently forget what someone just said during a conversation?",
            "Do you find yourself starting tasks but leaving them incomplete?",
            "Do you feel it is difficult to stay focused during long meetings or lectures?",
            "Do you have difficulty remembering and executing multi-step tasks without reminders?",
            "Do you often miss deadlines or due dates for tasks or responsibilities?",
            "Do you frequently feel overwhelmed by tasks that require planning or organization?",
            "Do you often avoid tasks that require a lot of mental effort or concentration?",
            "Do you feel that your workspace, schedule, or personal systems are often disorganized?",
            "Do you misplace items like keys, glasses, paperwork, or devices on a regular basis?",
            "Do you lose track of time and run late for appointments or scheduled events?",
            "Do you find yourself easily distracted by sounds or visual stimuli while working?",
            "Do you find your own thoughts interrupt your concentration during tasks?",
            "Do you regularly forget appointments, errands, or commitments?",
            "Do you forget to return messages, emails, or complete tasks that others expect from you?",
            "Do distracting noises or visual stimuli pull you out of concentration easily?",
            "Do conversations seem hard to follow, even at moderate volume?",
            "Do you desperately need reminders to follow multi-step instructions or tasks?"
        ]
    },
    {
        "intro": "Now let’s discuss activity level and impulsivity—both physical restlessness and quick decision-making—again focusing on the past six months.",
        "questions": [
            "Do you find it hard to remain seated for extended periods?",
            "Do you frequently tap your fingers, bounce your knee, or fidget with objects when seated?",
            "Do you often feel a physical restlessness or internal sense of pressure to move?",
            "Do you engage in multiple tasks at once even when it causes you to be less productive?",
            "Do you experience difficulty relaxing even when you try to unwind?",
            "Do you feel uncomfortable when expected to sit still without stimulation?",
            "Do you talk excessively in social or professional situations?",
            "Do you frequently interrupt others during conversations?",
            "Do you answer questions before they have been fully asked?",
            "Do you speak without thinking in situations where it might cause problems?",
            "Do you cut into lines, conversations, or activities without waiting your turn?",
            "Do others comment that you are impulsive or act without thinking things through?",
            "Do you often make decisions quickly without considering long-term consequences?",
            "Do you change topics frequently when speaking without realizing it?",
            "Do you engage in risky behaviors because you feel bored or impatient?"
        ]
    },
    {
        "intro": "Let’s look back at childhood—specifically before age twelve—to see how early these patterns may have appeared.",
        "questions": [
            "As a child, did you frequently get in trouble at school for talking or moving around too much?",
            "Did you have difficulty staying seated in class or during family meals?",
            "Were you often told that you were inattentive, careless, or not living up to your potential?",
            "Did you frequently forget to turn in homework or lose school supplies?",
            "Were you often late for school, activities, or family events?",
            "Did you struggle to keep up with classmates in terms of staying focused on tasks?",
            "Did teachers or adults frequently describe you as overly active, distracted, or impulsive?",
            "Did you have trouble keeping friends because of interrupting or being too intense?",
            "Did you get bored easily and jump from one activity to another without finishing?",
            "Were there repeated concerns about your behavior from teachers or caregivers?",
            "Do you feel an urge to stand, walk, or move even when you know you should stay seated?",
            "Did caregivers describe you as unable to sit still, even during quiet play?"
        ]
    },
    {
        "intro": "Next, I’d like to understand how these difficulties affect your daily functioning in different areas of life.",
        "questions": [
            "Have your difficulties with focus or impulsivity affected your ability to meet expectations at work?",
            "Do you feel that ADHD-like symptoms have negatively affected your academic performance?",
            "Have you changed jobs frequently due to issues with attention or task follow-through?",
            "Have you received feedback from supervisors about inconsistency, disorganization, or poor time management?",
            "Do symptoms interfere with your ability to manage daily home responsibilities?",
            "Do you experience frequent conflicts or misunderstandings with loved ones due to inattention or impulsivity?",
            "Has anyone close to you suggested you may have problems with focus, planning, or self-control?",
            "Do you feel your social life is negatively affected by forgetting plans or interrupting others?",
            "Do you find it hard to manage long-term goals due to difficulties staying organized or on track?",
            "Have you ever been formally disciplined, reprimanded, or let go from a job due to behavioral issues?",
            "Do these patterns cause challenges in more than one area of your life, such as work, school, and home?"
        ]
    },
    {
        "intro": "I’ll ask about other experiences that can mimic or contribute to attention and activity difficulties so we can consider all possibilities.",
        "questions": [
            "Do you experience persistent anxiety that interferes with your ability to focus?",
            "Have you had extended periods of low energy or sadness that affected your attention span?",
            "Do you often feel mentally foggy or slow, especially under stress?",
            "Do you experience sleep problems such as frequent waking or excessive fatigue during the day?",
            "Have you had any head injuries or neurological conditions that could impact your attention or activity level?",
            "Do you use substances such as caffeine, nicotine, or others to enhance your focus?",
            "Do you have intrusive thoughts or flashbacks from past trauma that interfere with your concentration?",
            "Did you ever receive a diagnosis of a learning disorder such as dyslexia or math disability?",
            "Have you been treated in the past for anxiety, depression, or another mental health condition?",
            "Do you experience manic or high-energy periods that include impulsive behavior and reduced need for sleep?"
        ]
    },
    {
        "intro": "Finally, let’s consider your family background, as genetics can play a role in attention and behavior patterns.",
        "questions": [
            "Has anyone in your immediate family been diagnosed with ADHD or ADD?",
            "Do close family members have a history of depression, anxiety, or other mental health conditions?",
            "Is there a family history of learning disabilities or difficulties in school performance?",
            "Have relatives described experiencing similar attention or behavioral challenges?"
        ]
    }
]

thinking_timeout   = 15   # max silence after question
phrase_time_limit  = 20   # max length of one answer
repeat_prompt_text = "Would you like me to repeat the question?"

# ───────────────────────────────────────────────────────────────────────────────
# Simple Bar Visualizer
# ───────────────────────────────────────────────────────────────────────────────
class WaveformVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 300)
        self.setStyleSheet("background-color: black;")
        self.bars = [0] * 20
        self.active = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_bars)

    def start(self):
        self.active = True
        self.timer.start(50)  # 20 fps

    def stop(self):
        self.active = False
        self.timer.stop()
        self.bars = [0] * len(self.bars)
        self.update()

    def update_bars(self):
        if self.active:
            self.bars = [random.randint(1, 100) for _ in self.bars]
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor("#00CFFF"))
        painter.setBrush(QColor("#00CFFF"))
        bar_w = self.width() // len(self.bars)
        for i, h in enumerate(self.bars):
            x = i * bar_w
            y = self.height() - h
            painter.drawRect(x, y, bar_w - 2, h)

# ───────────────────────────────────────────────────────────────────────────────
# Participant dialog
# ───────────────────────────────────────────────────────────────────────────────
class ParticipantInfoDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Participant Info")
        self.setFixedSize(300, 200)
        layout = QVBoxLayout(self)

        self.age_input = QLineEdit()
        self.age_input.setPlaceholderText("Enter your age")
        layout.addWidget(QLabel("Age:"))
        layout.addWidget(self.age_input)

        self.sex_input = QComboBox()
        self.sex_input.addItems(["Male", "Female", "Other"])
        layout.addWidget(QLabel("Sex:"))
        layout.addWidget(self.sex_input)

        self.response_display = QLabel("")
        layout.addWidget(self.response_display)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        if not self.age_input.text().isdigit():
            self.response_display.setText("Please enter a valid age.")
            return
        self.accept()

    def get_info(self):
        return int(self.age_input.text()), self.sex_input.currentText()

# ───────────────────────────────────────────────────────────────────────────────
# LLM WORKERS (non-blocking usage of gptoss_client.chat, just like adhd_app_gui)
# ───────────────────────────────────────────────────────────────────────────────
class LLMClassifyWorker(QThread):
    done = pyqtSignal(str, str, str)  # action, tag, raw_json
    error = pyqtSignal(str)

    def __init__(self, question, answer):
        super().__init__()
        self.question = question
        self.answer = answer

    def run(self):
        try:
            prompt = (
                'You are assisting an ADHD diagnostic interview.\n'
                f'Question: "{self.question}"\n'
                f'Answer: "{self.answer}"\n'
                'Return STRICT JSON with keys "action" (FOLLOW_UP or CONTINUE) '
                'and "tag" (INATTENTION|IMPULSIVITY|CHILDHOOD|FUNCTIONING|DIFFERENTIAL|FAMILY):\n'
                '{"action":"FOLLOW_UP","tag":"INATTENTION"}'
            )
            raw = chat(prompt, max_tokens=128) or ""
            action, tag = "CONTINUE", ""
            try:
                parsed = json.loads(raw)
                action = str(parsed.get("action", "CONTINUE")).upper()
                tag    = str(parsed.get("tag", "")).upper()
                if action not in ("FOLLOW_UP", "CONTINUE"):
                    action = "CONTINUE"
            except Exception:
                # Soft fallback if server returned plain text
                if "follow" in raw.lower():
                    action = "FOLLOW_UP"
            self.done.emit(action, tag, raw)
        except Exception as e:
            self.error.emit(str(e))


class LLMFollowUpWorker(QThread):
    done  = pyqtSignal(str)  # follow-up question
    error = pyqtSignal(str)

    def __init__(self, question, answer):
        super().__init__()
        self.question = question
        self.answer   = answer

    def run(self):
        try:
            prompt = (
                "Generate a concise, clinically helpful follow-up question for ADHD evaluation.\n"
                f"Original question: {self.question}\n"
                f"User answer: {self.answer}\n"
                "Follow-up (one sentence):"
            )
            text = (chat(prompt, max_tokens=80) or "").strip()
            if not text.endswith("?"):
                text = text.rstrip(".") + "?"
            self.done.emit(text or "Could you say more about that?")
        except Exception as e:
            self.error.emit(str(e))

# ───────────────────────────────────────────────────────────────────────────────
# Main window
# ───────────────────────────────────────────────────────────────────────────────
class DiagnosisWindow(QWidget):
    def __init__(self, mic_index=None, camera_index=0):
        super().__init__()
        self.mic_index = mic_index
        self.camera_index = camera_index
        self.capture = cv2.VideoCapture(self.camera_index)

        self.transcript_log = []
        self.silence_timer = QTimer(self)
        self.silence_timer.setSingleShot(True)
        self.silence_timer.timeout.connect(self.prompt_repeat_question)
        self.silence_strikes = 0
        self.awaiting_repeat_reply = False
        self.awaiting_start_confirmation = False
        self.just_played_intro = False
        self.tts_busy = False
        self.allow_mic_capture = True

        # Ask for participant info
        info_dialog = ParticipantInfoDialog()
        if info_dialog.exec_() != QDialog.Accepted:
            self.close()
            return
        self.participant_age, self.participant_sex = info_dialog.get_info()

        self.setWindowTitle("Diagnosis Interview")
        self.setGeometry(100, 100, 1200, 720)
        self.media_player = QMediaPlayer(self)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)

        self.interview_sections = interview_data
        self.current_section_index = 0
        self.current_question_index = 0

        # Layout
        main_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()
        bottom_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        main_layout.addLayout(bottom_layout)

        # Left (visualizer + AI text)
        self.left_layout = QVBoxLayout()
        content_layout.addLayout(self.left_layout)

        self.waveform_visualizer = WaveformVisualizer()
        self.left_layout.addWidget(self.waveform_visualizer)

        self.question_label = QLabel("AI subtitles go here...")
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("background-color: black; color: white; padding: 8px;")
        bottom_layout.addWidget(self.question_label)

        # Right (webcam + feedback)
        self.right_layout = QVBoxLayout()
        content_layout.addLayout(self.right_layout)

        self.video_label = QLabel()
        self.video_label.setFixedSize(500, 300)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.right_layout.addWidget(self.video_label)

        self.feedback_display = QLabel("User response will appear here...\nIs this correct?")
        self.feedback_display.setWordWrap(True)
        self.feedback_display.setStyleSheet("background-color: black; color: white; padding: 8px;")
        bottom_layout.addWidget(self.feedback_display)

        # Controls
        self.confirm_button = QPushButton("✅ Yes, continue")
        self.retry_button   = QPushButton("🔁 Re-say answer")
        self.confirm_button.clicked.connect(self.confirm_answer)
        self.retry_button.clicked.connect(self.retry_answer)
        ctr = QHBoxLayout()
        ctr.addStretch()
        ctr.addWidget(self.confirm_button)
        ctr.addWidget(self.retry_button)
        ctr.addStretch()
        main_layout.addLayout(ctr)
        self.confirm_button.hide()
        self.retry_button.hide()

        # Footer
        footer = QHBoxLayout()
        footer.addWidget(QLabel("ANQA A.I."))
        footer.addStretch()
        for icon in ["📷", "🎙️", "➕", "🔴"]:
            footer.addWidget(QPushButton(icon))
        footer.addStretch()
        footer.addWidget(QLabel("User's Name Here"))
        main_layout.addLayout(footer)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # Speak intro and capture a "yes" before starting
        QTimer.singleShot(500, self.play_intro)

        # TTS (Coqui)
        self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")

        # LLM workers
        self._classify_worker = None
        self._followup_worker = None

    # ── Small intro ────────────────────────────────────────────────────────────
    def play_intro(self):
        self.awaiting_start_confirmation = True
        intro = (
            "Hi! We’ll go through some questions about attention and activity. "
            "When you're ready to begin, please say yes."
        )
        self.question_label.setText(intro)
        self.speak_with_coqui(intro, is_intro=False)  # not section intro; we want a 'yes' first

    # ── Utilities ──────────────────────────────────────────────────────────────
    def safe_single_shot(self, ms, func):
        QTimer.singleShot(ms, lambda: func())

    def finish_tts(self):
        QTimer.singleShot(250, self.enable_mic_capture)

    def enable_mic_capture(self):
        self.tts_busy = False
        self.allow_mic_capture = True

    # ── Video ─────────────────────────────────────────────────────────────────
    def update_frame(self):
        ret, frame = self.capture.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(rgb.data, *rgb.shape[1::-1], QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(img))

    # ── Audio/TTS ──────────────────────────────────────────────────────────────
    def speak_with_coqui(self, text, filename=None, is_intro=False):
        self.waveform_visualizer.start()
        if self.tts_busy:
            return
        self.tts_busy = True
        self.just_played_intro = is_intro
        self.allow_mic_capture = False

        sentences = text.replace('\n', ' ').replace('—', '-').split('. ')
        if not sentences:
            self.finish_tts()
            return

        for i, sentence in enumerate(sentences):
            clean = sentence.strip()
            if not clean or len(clean.split()) < 2:
                continue
            safe_filename = (filename or f"tts_out_{uuid.uuid4().hex}.wav").replace(".wav", f"_{i}.wav")
            try:
                self.tts.tts_to_file(text=clean, file_path=safe_filename)
            except Exception as e:
                print(f"[ERROR] TTS failed: {e}")
                continue

            media = QMediaContent(QUrl.fromLocalFile(safe_filename))
            self.media_player.setMedia(media)
            self.media_player.play()
            self.wait_for_end_of_media()

        QTimer.singleShot(150, self.enable_mic_capture)
        self.waveform_visualizer.stop()

    def wait_for_end_of_media(self):
        loop = QEventLoop()
        def on_status(status):
            if status == QMediaPlayer.EndOfMedia:
                self.media_player.mediaStatusChanged.disconnect(on_status)
                loop.quit()
        self.media_player.mediaStatusChanged.connect(on_status)
        loop.exec_()

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.tts_busy = False
            if self.awaiting_start_confirmation:
                QTimer.singleShot(200, self.capture_response)
                return
            if self.just_played_intro:
                self.just_played_intro = False
                def play_question_safe():
                    if self.tts_busy:
                        QTimer.singleShot(300, play_question_safe)
                    else:
                        self.ask_next_question()
                play_question_safe()
            else:
                def delayed_capture():
                    if self.tts_busy:
                        QTimer.singleShot(300, delayed_capture)
                    else:
                        self.capture_response()
                delayed_capture()

    # ── Voice capture ─────────────────────────────────────────────────────────
    def capture_response(self):
        if not self.allow_mic_capture:
            return
        self.allow_mic_capture = False
        threading.Thread(target=self.process_voice, daemon=True).start()
        self.silence_timer.start(10000)

    def process_voice(self):
        recognizer = sr.Recognizer()
        try:
            mic = sr.Microphone(device_index=self.mic_index if self.mic_index is not None else None)
        except Exception:
            self.feedback_display.setText("Microphone not available. Please check audio settings.")
            return

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.2)
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=phrase_time_limit)
                text = recognizer.recognize_google(audio).strip()
            except sr.WaitTimeoutError:
                self.feedback_display.setText("I didn’t hear anything. Want me to repeat the question?")
                self.safe_single_shot(2000, self.capture_response)
                return
            except sr.UnknownValueError:
                self.feedback_display.setText("Sorry, I didn’t catch that.")
                self.safe_single_shot(2000, self.capture_response)
                return

        self.silence_strikes = 0
        self.feedback_display.setText(f"You said: {text}")

        # Handle pre-start 'yes'
        if self.awaiting_start_confirmation:
            norm = text.lower().strip()
            affirm = ["yes", "ready", "sure", "okay", "yeah", "yep", "go ahead", "i am", "let's start", "i'm ready"]
            if any(a in norm for a in affirm):
                self.awaiting_start_confirmation = False
                self.section_intro_played = False
                intro = self.interview_sections[self.current_section_index]["intro"]
                self.speak_with_coqui(intro, is_intro=True)
            else:
                self.feedback_display.setText("Please say 'yes' or 'I'm ready' when you're ready.")
                QTimer.singleShot(2000, self.capture_response)
            return

        # Handle "repeat question?"
        if self.awaiting_repeat_reply:
            self.awaiting_repeat_reply = False
            if text.lower().startswith("y"):
                self.speak_with_coqui(self.question_label.text())
            else:
                self.ask_next_question()
            return

        # Normal routing
        self.route_answer(text)

    # ── Silence / repeat ───────────────────────────────────────────────────────
    def prompt_repeat_question(self):
        self.awaiting_repeat_reply = True
        self.speak_with_coqui("I didn’t catch a response. Would you like me to repeat the question?")

    def handle_no_response(self):
        self.prompt_repeat_question()
        if self.silence_strikes == 1:
            self.feedback_display.setText("Take your time…")
            QTimer.singleShot(4000, self.capture_response)
        else:
            self.silence_strikes = 0
            self.awaiting_repeat_reply = True
            self.speak_with_coqui(repeat_prompt_text)
            self.feedback_display.setText(repeat_prompt_text)

    # ── LLM FLOW (now async via workers) ───────────────────────────────────────
    def route_answer(self, text):
        """Evaluate the answer with the tiny NN and the LLM; decide follow-up or continue."""
        self.silence_timer.stop()
        self.awaiting_repeat_reply = False
        question = self.question_label.text()

        # 1) Fast local heuristic/NN pass (unchanged)
        traits = evaluate_answer_traits(question, text, self.participant_age, self.participant_sex)
        if traits.get("trait") == "UNKNOWN":
            traits["trait"] = "INATTENTION" if "focus" in text.lower() else "IMPULSIVITY"
            traits["completeness"] = 0.9 if len(text.split()) > 8 else 0.4

        # Log the raw response early
        self.transcript_log.append({
            "question": question,
            "response": text,
            "trait": traits.get("trait", "UNKNOWN"),
            "completeness": traits.get("completeness", 1.0)
        })

        # 2) Non-blocking LLM classification
        self.feedback_display.setText("Processing your response…")
        self.confirm_button.hide()
        self.retry_button.hide()

        self._classify_worker = LLMClassifyWorker(question, text)
        self._classify_worker.done.connect(lambda action, tag, raw: self.on_classify_done(text, traits, action, tag, raw))
        self._classify_worker.error.connect(self.on_llm_error)
        self._classify_worker.start()

    def on_classify_done(self, user_text, traits, action, tag, raw_json):
        """Handle LLM classification result."""
        # Save LLM decision into the last log entry
        if self.transcript_log:
            self.transcript_log[-1]["llm_action"] = action
            if tag:
                self.transcript_log[-1]["llm_tag"] = tag
            self.transcript_log[-1]["llm_raw"] = raw_json

        # Decide whether to ask a follow-up
        needs_followup = traits.get("completeness", 1.0) < 0.5 or action == "FOLLOW_UP"

        if needs_followup:
            self._followup_worker = LLMFollowUpWorker(self.question_label.text(), user_text)
            self._followup_worker.done.connect(self.on_followup_done)
            self._followup_worker.error.connect(self.on_llm_error)
            self._followup_worker.start()
        else:
            self.feedback_display.setText(f"You said: {user_text}\n\n(Ready to continue?)")
            self.confirm_button.show()
            self.retry_button.show()
            self.current_action = "CONTINUE"

    def on_followup_done(self, follow_up_text):
        self.current_action = "FOLLOW_UP"
        self.question_label.setText(follow_up_text)
        self.speak_with_coqui(follow_up_text)
        self.transcript_log.append({
            "question": follow_up_text,
            "response": "",
            "follow_up": True,
            "related_to": self.transcript_log[-1]["question"] if self.transcript_log else None
        })

    def on_llm_error(self, msg):
        # Graceful fallback: continue with confirm/retry
        self.feedback_display.setText("Continuing without AI follow-up. (LLM error)")
        self.confirm_button.show()
        self.retry_button.show()
        self.current_action = "CONTINUE"

    # Legacy helpers kept for debugging / fallback
    def classify_response(self, text, question):
        try:
            prompt = f"""You are helping evaluate ADHD.
Question: "{question}"
Answer: "{text}"
Decide if a follow-up is needed. Respond in JSON:
{{ "action": "FOLLOW_UP", "tag": "INATTENTION" }}"""
            raw = chat(prompt, max_tokens=128) or ""
            parsed = json.loads(raw) if raw.strip().startswith("{") else {"action": "CONTINUE"}
            return parsed.get("action", "CONTINUE")
        except Exception:
            return "ERROR"

    def generate_follow_up_question(self, question, user_answer):
        prompt = f"""Generate a better follow-up for ADHD evaluation.
Q: {question}
User: {user_answer}
Follow-up:"""
        return (chat(prompt, max_tokens=80) or "").strip()

    # ── Buttons ────────────────────────────────────────────────────────────────
    def confirm_answer(self):
        self.confirm_button.hide()
        self.retry_button.hide()
        if getattr(self, "current_action", "CONTINUE") == "FOLLOW_UP":
            self.question_label.setText("Can you tell me more?")
            self.speak_with_coqui("Can you tell me more?")
            QTimer.singleShot(4000, self.capture_response)
        else:
            self.ask_next_question()

    def retry_answer(self):
        self.confirm_button.hide()
        self.retry_button.hide()
        self.feedback_display.setText("Let's try again...")
        QTimer.singleShot(1000, self.capture_response)

    # ── Question flow ──────────────────────────────────────────────────────────
    def ask_next_question(self):
        section = self.interview_sections[self.current_section_index]
        questions = section["questions"]

        if self.current_question_index == 0:
            if not getattr(self, "section_intro_played", False):
                self.section_intro_played = True
                self.speak_with_coqui(section["intro"], is_intro=True)
                return

        if self.current_question_index < len(questions):
            q = questions[self.current_question_index]
            self.question_label.setText(q)
            self.speak_with_coqui(q, is_intro=False)
            self.current_question_index += 1
        else:
            self.current_section_index += 1
            self.current_question_index = 0
            self.section_intro_played = False
            if self.current_section_index < len(self.interview_sections):
                QTimer.singleShot(500, self.ask_next_question)
            else:
                self.question_label.setText("This concludes the interview. Thank you.")

    # ── Close / save ───────────────────────────────────────────────────────────
    def save_transcript_log(self):
        with open("adhd_interview_log.json", "w") as f:
            json.dump(self.transcript_log, f, indent=2)

    def closeEvent(self, event):
        self.capture.release()
        super().closeEvent(event)

