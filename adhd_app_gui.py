import sys
import threading
import time
import subprocess
import platform
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QRadioButton, QButtonGroup, QLineEdit, QTextEdit, QSizePolicy,
    QMessageBox, QProgressDialog, QFrame, QScrollArea, QSplitter, QStatusBar
)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject, QThread, Qt
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor
from gptoss_client import chat
from settings_window import SettingsWindow 
from simple_server_manager import SimpleServerManager





# Load the local model (make sure the path and file match)



class ServerStartupSignals(QObject):
    """Signals for server startup communication"""
    status_update = pyqtSignal(str)
    startup_complete = pyqtSignal(bool)

class ServerConnectionWorker(QThread):
    """Worker thread for handling server connection asynchronously"""
    status_update = pyqtSignal(str, str)  # message, status_type
    connection_ready = pyqtSignal(bool)  # True if connected, False if failed
    server_startup_needed = pyqtSignal()  # Signal when server startup options should be shown
    
    def __init__(self, server_manager):
        super().__init__()
        self.server_manager = server_manager
        self.should_stop = False
        
    def run(self):
        """Run server connection check in background"""
        try:
            self.status_update.emit("🔍 Checking server connection...", "info")
            
            # First quick check if server is already ready
            if self.server_manager.is_server_ready():
                self.status_update.emit("✅ Server is already connected!", "success")
                self.connection_ready.emit(True)
                return
            
            # Server not ready, offer startup options
            self.status_update.emit("❌ Server not detected. Would you like to start it?", "warning")
            self.server_startup_needed.emit()
            
        except Exception as e:
            if not self.should_stop:
                self.status_update.emit(f"❌ Server connection error: {str(e)}", "error")
                self.connection_ready.emit(False)
    
    def stop(self):
        """Stop the connection worker"""
        self.should_stop = True

class ServerStartupWorker(QThread):
    """Worker thread for starting server via SSH"""
    status_update = pyqtSignal(str, str)  # message, status_type
    startup_complete = pyqtSignal(bool)  # True if successful, False if failed
    
    def __init__(self, server_manager):
        super().__init__()
        self.server_manager = server_manager
        self.should_stop = False
        
    def run(self):
        """Start server and wait for it to be ready"""
        try:
            # Start server via SSH
            def status_callback(message):
                if not self.should_stop:
                    self.status_update.emit(message, "info")
            
            if not self.server_manager.start_server_ssh(status_callback):
                self.startup_complete.emit(False)
                return
            
            # Wait for server to become ready
            self.status_update.emit("⏳ Waiting for server to start (this may take 2-5 minutes)...", "info")
            
            start_time = time.time()
            max_wait = 300  # 5 minutes timeout
            
            while not self.should_stop and (time.time() - start_time) < max_wait:
                if self.server_manager.is_server_ready():
                    self.status_update.emit("✅ Server started successfully!", "success")
                    self.startup_complete.emit(True)
                    return
                
                elapsed = int(time.time() - start_time)
                self.status_update.emit(f"⏳ Server starting... ({elapsed}s elapsed)", "info")
                time.sleep(5)
            
            # Timeout reached
            if not self.should_stop:
                self.status_update.emit("❌ Server startup timeout. Please check server manually.", "error")
                self.startup_complete.emit(False)
                
        except Exception as e:
            if not self.should_stop:
                self.status_update.emit(f"❌ Server startup error: {str(e)}", "error")
                self.startup_complete.emit(False)
    
    def stop(self):
        """Stop the startup worker"""
        self.should_stop = True
        if hasattr(self.server_manager, 'stop_server'):
            self.server_manager.stop_server()


class ChatWorker(QThread):
    """Worker thread for handling chat responses without blocking UI"""
    response_ready = pyqtSignal(str)
    response_chunk = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, message):
        super().__init__()
        self.message = message
        
    def run(self):
        try:
            # Simulate streaming by getting response and sending it in chunks
            response = chat(self.message, max_tokens=256)
            if not response:
                response = "(no response received)"
            
            # Simulate streaming effect by sending response in chunks
            words = response.split()
            current_text = ""
            
            for i, word in enumerate(words):
                current_text += word + " "
                self.response_chunk.emit(current_text.strip())
                time.sleep(0.05)  # Small delay for streaming effect
                
            self.response_ready.emit(response.strip())
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class ADHDApp(QWidget):
    asrs_questions = [
    "How often do you have trouble wrapping up the final details of a project?",
    "How often do you have difficulty getting things in order when you have to do a task that requires organization?",
    "How often do you have problems remembering appointments or obligations?",
    "When you have a task that requires a lot of thought, how often do you avoid or delay getting started?",
    "How often do you make careless mistakes when you have to work on a boring or difficult project?",
    "How often do you have difficulty keeping your attention when you are doing boring or repetitive work?",
    "How often do you have difficulty concentrating on what people are saying to you, even when they are speaking to you directly?",
    "How often do you have trouble doing things that require sustained mental effort?",
    "How often do you lose things necessary for tasks and activities (keys, glasses, paperwork, etc.)?",
    "How often are you easily distracted by extraneous stimuli when you are doing something?",
    "How often do you forget to do things that you need to do?",
    "How often do you make impulsive decisions or show impulsive behavior?",
    "How often do you have difficulty awaiting your turn in situations when waiting is required?",
    "How often do you interrupt others when they are busy?",
    "How often do you blurt out answers before questions have been completed?",
    "How often do you have difficulty resisting temptations or opportunities?",
    "How often do you feel restless or fidgety?",
    "How often do you feel overwhelmed by your responsibilities?",
    ]

    def __init__(self, ssh_manager=None):
        super().__init__()
        
        self.setWindowTitle("🧠 ADHD Diagnostic Tool")
        self.setGeometry(100, 100, 1200, 750)  # Slightly taller for status bar
        
        # Set up modern styling
        self.setup_styling()
        
        # Store SSH manager reference for server operations
        self.ssh_manager = ssh_manager
        
        # Initialize server manager but don't connect yet
        self.server_manager = SimpleServerManager()
        self.server_ready = False
        self.server_connection_worker = None
        self.chat_worker = None
        self.current_response_text = ""
        
        # Initialize UI immediately - no server dependencies
        self.init_main_ui()
        
        # Start server connection asynchronously after UI is loaded
        QTimer.singleShot(500, self.start_async_server_connection)
        

        
        # Start SSH status monitoring
        self.ssh_status_timer = QTimer()
        self.ssh_status_timer.timeout.connect(self.update_ssh_status)
        self.ssh_status_timer.start(2000)  # Update every 2 seconds
        
        # Track previous model ready state to detect changes
        self.previous_model_ready = False
    
    def setup_styling(self):
        """Set up modern UI styling"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QRadioButton {
                font-size: 13px;
                padding: 5px;
                color: #444;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
                font-size: 13px;
                line-height: 1.4;
            }
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)

    def start_async_server_connection(self):
        """Start server connection asynchronously after UI is loaded"""
        # Show initial status in chat
        self.add_chat_message("🔍 Starting server connection check...", "system")
        
        # Start server connection worker
        self.server_connection_worker = ServerConnectionWorker(self.server_manager)
        self.server_connection_worker.status_update.connect(self.on_server_status_update)
        self.server_connection_worker.connection_ready.connect(self.on_server_connection_ready)
        self.server_connection_worker.server_startup_needed.connect(self.show_server_startup_options)
        self.server_connection_worker.start()
        
        # Start continuous monitoring for server availability
        self.start_continuous_server_monitoring()
    
    def on_server_status_update(self, message, status_type):
        """Handle server status updates from background worker"""
        self.add_chat_message(message, "system")
    
    def on_server_connection_ready(self, connected):
        """Handle server connection result"""
        self.server_ready = connected
        self.update_server_status()
        self.update_chat_input_state()
        
        if connected:
            self.add_chat_message("🎉 Chat features are now available! Ask me anything about ADHD.", "system")
        else:
            self.add_chat_message("ℹ️ Chat is disabled, but you can still complete the ADHD assessment.", "system")
    
    def show_server_startup_options(self):
        """Show server startup options in the chat interface"""
        startup_message = """
        <div style='background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 10px 0;'>
        <strong>🚀 Server Startup Options</strong><br><br>
        
        The AI server is not currently running. You have the following options:<br><br>
        
        <strong>Option 1: Automatic Startup (Recommended)</strong><br>
        • Click "Start Server" to automatically start the AI server<br>
        • This will take 2-5 minutes to complete<br>
        • Requires SSH access to be configured<br><br>
        
        <strong>Option 2: Manual Startup</strong><br>
        • Run the server manually using start_server.bat<br>
        • Or start it directly on your server<br><br>
        
        <strong>Option 3: Continue Offline</strong><br>
        • Use the ADHD assessment without AI chat features<br>
        • All assessment functionality works offline<br>
        </div>
        """
        
        self.add_chat_message(startup_message, "system")
        
        # Add server startup buttons to the chat interface
        self.add_server_startup_buttons()
    
    def add_server_startup_buttons(self):
        """Add server startup buttons to the chat interface"""
        from PyQt5.QtWidgets import QHBoxLayout, QWidget
        
        # Create button container
        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        
        # Start Server button
        start_server_btn = QPushButton("🚀 Start Server")
        start_server_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        start_server_btn.clicked.connect(self.start_server_automatically)
        
        # Wait for Manual button
        wait_manual_btn = QPushButton("⏳ Wait for Manual Start")
        wait_manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        wait_manual_btn.clicked.connect(self.wait_for_manual_server)
        
        # Continue Offline button
        offline_btn = QPushButton("📱 Continue Offline")
        offline_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        offline_btn.clicked.connect(self.continue_offline)
        
        button_layout.addWidget(start_server_btn)
        button_layout.addWidget(wait_manual_btn)
        button_layout.addWidget(offline_btn)
        
        # Add buttons to chat display
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText("\n")
        
        # Store reference to remove later
        self.server_startup_buttons = button_widget
        
        # Insert the widget into the chat display
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.End)
        self.chat_display.setTextCursor(cursor)
        
        # Add some spacing and the buttons
        self.add_chat_message("Choose an option:", "system")
    
    def start_server_automatically(self):
        """Start server automatically via SSH"""
        self.add_chat_message("🚀 Starting server automatically...", "system")
        
        # Remove startup buttons
        if hasattr(self, 'server_startup_buttons'):
            delattr(self, 'server_startup_buttons')
        
        # Start server startup worker
        self.server_startup_worker = ServerStartupWorker(self.server_manager)
        self.server_startup_worker.status_update.connect(self.on_server_status_update)
        self.server_startup_worker.startup_complete.connect(self.on_server_startup_complete)
        self.server_startup_worker.start()
    
    def wait_for_manual_server(self):
        """Wait for manual server startup"""
        self.add_chat_message("⏳ Waiting for manual server startup...", "system")
        self.add_chat_message("Please run start_server.bat or start the server manually on your remote machine.", "system")
        
        # Remove startup buttons
        if hasattr(self, 'server_startup_buttons'):
            delattr(self, 'server_startup_buttons')
        
        # Start monitoring for server availability
        self.start_server_monitoring()
    
    def continue_offline(self):
        """Continue with offline features only"""
        self.add_chat_message("📱 Continuing in offline mode. ADHD assessment is fully available!", "system")
        self.add_chat_message("You can start the server later if you want to use AI chat features.", "system")
        
        # Remove startup buttons
        if hasattr(self, 'server_startup_buttons'):
            delattr(self, 'server_startup_buttons')
        
        # Mark as offline mode
        self.server_ready = False
        self.update_server_status()
        self.update_chat_input_state()
    
    def start_server_monitoring(self):
        """Start monitoring for server availability"""
        # Create a simple monitoring worker
        class ServerMonitorWorker(QThread):
            server_detected = pyqtSignal()
            
            def __init__(self, server_manager):
                super().__init__()
                self.server_manager = server_manager
                self.should_stop = False
            
            def run(self):
                while not self.should_stop:
                    if self.server_manager.is_server_ready():
                        self.server_detected.emit()
                        return
                    time.sleep(5)
            
            def stop(self):
                self.should_stop = True
        
        self.server_monitor_worker = ServerMonitorWorker(self.server_manager)
        self.server_monitor_worker.server_detected.connect(self.on_manual_server_detected)
        self.server_monitor_worker.start()
    
    def on_manual_server_detected(self):
        """Handle when server is detected after manual startup"""
        self.add_chat_message("✅ Server detected! Connecting...", "system")
        self.server_ready = True
        self.update_server_status()
        self.update_chat_input_state()
        self.add_chat_message("🎉 Chat features are now available! Ask me anything about ADHD.", "system")
    
    def on_server_startup_complete(self, success):
        """Handle server startup completion"""
        if success:
            self.server_ready = True
            self.update_server_status()
            self.update_chat_input_state()
            self.add_chat_message("🎉 Server started successfully! Chat features are now available.", "system")
        else:
            self.add_chat_message("❌ Server startup failed. You can try manual startup or continue offline.", "system")
            self.add_chat_message("To try again, you can run start_server.bat manually.", "system")
    
    def start_continuous_server_monitoring(self):
        """Start continuous monitoring for server availability changes"""
        self.server_monitor_timer = QTimer()
        self.server_monitor_timer.timeout.connect(self.check_server_availability)
        self.server_monitor_timer.start(10000)  # Check every 10 seconds
    
    def check_server_availability(self):
        """Check server availability and update status if changed"""
        if not self.server_ready:  # Only check if we think server is not ready
            if self.server_manager.is_server_ready():
                self.server_ready = True
                self.update_server_status()
                self.update_chat_input_state()
                self.add_chat_message("✅ Server connection established! Chat features are now available.", "system")
    
    def check_server_after_model_ready(self):
        """Check server connection after model becomes ready"""
        if self.server_manager.is_server_ready():
            self.server_ready = True
            self.update_server_status()
            self.update_chat_input_state()
            self.add_chat_message("✅ Server API is ready! Chat features are now available.", "system")
        else:
            self.add_chat_message("⏳ Model loaded but API not responding yet. Will keep checking...", "system")
    

    
    def init_status_bar(self):
        """Initialize the status bar"""
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border: none;
                border-radius: 0;
                padding: 8px;
                margin: 0;
            }
            QLabel {
                color: white;
                font-size: 12px;
                padding: 2px 8px;
            }
        """)
        
        status_layout = QHBoxLayout()
        self.status_bar.setLayout(status_layout)
        
        # SSH/Model status (new)
        self.ssh_status_label = QLabel("🔄 SSH: Connecting...")
        status_layout.addWidget(self.ssh_status_label)
        
        # Separator
        separator0 = QLabel("|")
        separator0.setStyleSheet("color: #7f8c8d;")
        status_layout.addWidget(separator0)
        
        # Server status
        self.server_status_label = QLabel("🔴 Server: Disconnected")
        status_layout.addWidget(self.server_status_label)
        
        # Separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #7f8c8d;")
        status_layout.addWidget(separator1)
        
        # System info
        system_info = f"💻 {platform.system()} {platform.machine()}"
        self.system_label = QLabel(system_info)
        status_layout.addWidget(self.system_label)
        
        # Add stretch to push everything to the left
        status_layout.addStretch()
        
        # Update initial statuses
        self.update_server_status()
        self.update_ssh_status()
    
    def update_server_status(self):
        """Update server status in status bar"""
        if hasattr(self, 'server_status_label'):
            if self.server_ready:
                self.server_status_label.setText("🟢 Server: Connected")
                self.server_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            else:
                self.server_status_label.setText("🔴 Server: Disconnected")
                self.server_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
    

    def update_ssh_status(self):
        """Update SSH/Model status in status bar and trigger server detection when model becomes ready"""
        if hasattr(self, 'ssh_status_label') and self.ssh_manager:
            current_model_ready = self.ssh_manager.is_model_ready()
            
            # Check if model just became ready
            if current_model_ready and not self.previous_model_ready:
                self.previous_model_ready = True
                # Model just became ready, trigger server detection
                self.add_chat_message("🎉 AI Model loaded! Testing server connection...", "system")
                QTimer.singleShot(2000, self.check_server_after_model_ready)
            elif not current_model_ready:
                self.previous_model_ready = False
            
            if current_model_ready:
                self.ssh_status_label.setText("🟢 AI Model: Ready")
                self.ssh_status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.ssh_status_label.setToolTip("AI model is loaded and ready for use")
            elif self.ssh_manager.is_model_loading():
                self.ssh_status_label.setText("🔄 AI Model: Loading...")
                self.ssh_status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                status = self.ssh_manager.get_current_status()
                self.ssh_status_label.setToolTip(f"Status: {status}")
            elif self.ssh_manager.is_connected():
                self.ssh_status_label.setText("🟡 SSH: Connected")
                self.ssh_status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                self.ssh_status_label.setToolTip("SSH connected, preparing to load AI model")
            else:
                status = self.ssh_manager.get_current_status()
                if "error" in status.lower() or "failed" in status.lower():
                    self.ssh_status_label.setText("🔴 SSH: Error")
                    self.ssh_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    self.ssh_status_label.setText("🔄 SSH: Connecting...")
                    self.ssh_status_label.setStyleSheet("color: #3498db; font-weight: bold;")
                self.ssh_status_label.setToolTip(f"Status: {status}")
        elif hasattr(self, 'ssh_status_label'):
            self.ssh_status_label.setText("🔴 SSH: Not configured")
            self.ssh_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.ssh_status_label.setToolTip("SSH manager not available")
    
    def update_chat_input_state(self):
        """Update chat input and send button state based on server readiness"""
        if hasattr(self, 'chat_input') and hasattr(self, 'send_button'):
            if self.server_ready:
                self.chat_input.setEnabled(True)
                self.send_button.setEnabled(True)
                self.chat_input.setPlaceholderText("Ask me anything about ADHD...")
                self.send_button.setText("Send")
            else:
                self.chat_input.setEnabled(False)
                self.send_button.setEnabled(False)
                self.chat_input.setPlaceholderText("Chat disabled - server not connected")
                self.send_button.setText("Server Required")
    
    def init_main_ui(self):
        """Initialize the main UI after server is ready"""
        self.current_question = 0
        self.responses = []

        # Create main layout with status bar
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        
        # Create content splitter
        content_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)
        
        # Create frames for better visual separation
        self.screening_frame = QFrame()
        self.chat_frame = QFrame()
        
        self.init_screening_ui()
        self.init_chat_ui()
        
        splitter.addWidget(self.screening_frame)
        splitter.addWidget(self.chat_frame)
        splitter.setSizes([400, 600])  # Set initial sizes
        
        content_layout.addWidget(splitter)
        main_layout.addLayout(content_layout)
        
        # Add status bar
        self.init_status_bar()
        main_layout.addWidget(self.status_bar)
        
        # Set the main widget as the central widget
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(main_widget)
    
    def closeEvent(self, event):
        """Handle application close event - cleanup resources"""
        try:
            # Stop timers
            if hasattr(self, 'ssh_status_timer'):
                self.ssh_status_timer.stop()
            if hasattr(self, 'server_monitor_timer'):
                self.server_monitor_timer.stop()
            
            # Stop worker threads
            if hasattr(self, 'server_connection_worker') and self.server_connection_worker:
                self.server_connection_worker.stop()
                self.server_connection_worker.wait(3000)  # Wait up to 3 seconds
            
            if hasattr(self, 'server_startup_worker') and hasattr(self.server_startup_worker, 'stop'):
                self.server_startup_worker.stop()
                self.server_startup_worker.wait(3000)
            
            if hasattr(self, 'server_monitor_worker') and hasattr(self.server_monitor_worker, 'stop'):
                self.server_monitor_worker.stop()
                self.server_monitor_worker.wait(3000)
            
            # Stop and unload AI model
            if self.ssh_manager:
                self.add_chat_message("🔄 Stopping AI model...", "system")
                self.ssh_manager.stop_model_and_disconnect()
                self.add_chat_message("✅ AI model stopped and SSH disconnected.", "system")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Accept the close event
        event.accept()

    def init_screening_ui(self):
        self.left_layout = QVBoxLayout()
        self.screening_frame.setLayout(self.left_layout)

        # Title with better styling
        title_label = QLabel("🧠 ADHD Screening Assessment")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        self.left_layout.addWidget(title_label)

        # Progress indicator
        self.progress_label = QLabel("Question 1 of 18")
        self.progress_label.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            padding: 5px;
        """)
        self.left_layout.addWidget(self.progress_label)

        # Question display
        self.question_label = QLabel()
        self.question_label.setStyleSheet("""
            font-size: 15px;
            color: #2c3e50;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            margin: 10px 0;
        """)
        self.question_label.setWordWrap(True)
        self.left_layout.addWidget(self.question_label)

        # Radio buttons with better spacing
        self.button_group = QButtonGroup(self)
        self.radio_buttons = []
        
        options_frame = QFrame()
        options_layout = QVBoxLayout()
        options_frame.setLayout(options_layout)
        options_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 10px;
                margin: 5px 0;
            }
        """)
        
        for option in ['Never', 'Rarely', 'Sometimes', 'Often', 'Very Often']:
            rb = QRadioButton(option)
            rb.setStyleSheet("""
                QRadioButton {
                    font-size: 14px;
                    padding: 8px;
                    color: #2c3e50;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            options_layout.addWidget(rb)
            self.button_group.addButton(rb)
            self.radio_buttons.append(rb)
        
        self.left_layout.addWidget(options_frame)

        # Next button with better styling
        self.next_button = QPushButton("Next Question →")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                font-size: 15px;
                padding: 12px 25px;
                margin: 15px 0;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.next_button.clicked.connect(self.next_question)
        self.left_layout.addWidget(self.next_button)
        
        # Add stretch to push everything to top
        self.left_layout.addStretch()
        
        # Show the first question immediately
        self.show_question(self.asrs_questions[self.current_question])
    


    def init_chat_ui(self):
        self.right_layout = QVBoxLayout()
        self.chat_frame.setLayout(self.right_layout)

        # Chat title
        chat_title = QLabel("💬 AI Assistant")
        chat_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 8px;
            margin-bottom: 10px;
        """)
        self.right_layout.addWidget(chat_title)

        # Chat display with better styling
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        
        # Add welcome message with system status
        welcome_msg = f"""
        <div style='color: #7f8c8d; font-style: italic; margin-bottom: 10px;'>
        👋 Welcome! I'm here to help with your ADHD assessment. 
        
        <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #17a2b8;'>
        <strong>Getting Started:</strong><br>
        📋 ADHD Assessment: ✅ Ready (works offline)<br>
        💬 AI Chat: 🔍 Connecting to server...<br>
        🔗 Connection Status: 🔍 Checking...
        </div>
        
        <div style='background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 3px solid #28a745;'>
        <strong>✅ You can start the ADHD assessment immediately!</strong><br>
        The assessment works offline and doesn't require server connection.
        </div>
        
        Once connected, feel free to ask questions about:
        <ul>
        <li>ADHD symptoms and diagnosis</li>
        <li>The screening questions</li>
        <li>Treatment options</li>
        <li>Coping strategies</li>
        </ul>
        </div>
        """
        self.chat_display.setHtml(welcome_msg)
        
        self.right_layout.addWidget(self.chat_display)

        # Input area with send button
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Chat disabled - server connecting...")
        self.chat_input.setEnabled(False)  # Start disabled until server is ready
        self.chat_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 14px;
                border-radius: 8px;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        self.send_button = QPushButton("Server Required")
        self.send_button.setEnabled(False)  # Start disabled until server is ready
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                padding: 12px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #666666;
            }
        """)
        self.send_button.clicked.connect(self.send_chat_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_button)
        
        # GPU refresh button removed
        
        self.right_layout.addLayout(input_layout)
        
        # GPU monitoring removed
    
    def update_streaming_response(self, partial_text):
        """Update the AI response as it streams in"""
        # Simple implementation - just show the partial text
        pass
    


    def send_chat_message(self):
        # Don't allow sending if server is not ready
        if not self.server_ready:
            self.add_chat_message("⚠️ Chat is disabled until server connection is established.", "system")
            return
            
        user_message = self.chat_input.text().strip()
        if not user_message:
            return

        # Prevent sending while another message is processing
        if self.chat_worker and self.chat_worker.isRunning():
            self.add_chat_message("⏳ Please wait for the current response to complete...", "system")
            return

        # Disable input while processing
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.send_button.setText("Sending...")

        # Show the user message
        self.add_chat_message(user_message, "user")
        self.chat_input.clear()

        # Start AI response in background thread
        self.chat_worker = ChatWorker(user_message)
        self.chat_worker.response_chunk.connect(self.update_streaming_response)
        self.chat_worker.response_ready.connect(self.on_response_complete)
        self.chat_worker.error_occurred.connect(self.on_response_error)
        self.chat_worker.start()
        
        # Show "AI is typing..." indicator
        self.add_chat_message("🤔 AI is thinking...", "ai_typing")

    def add_chat_message(self, message, sender_type):
        """Add a formatted message to the chat display"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        if sender_type == "user":
            html = f"""
            <div style='margin: 10px 0; padding: 10px; background-color: #e3f2fd; 
                        border-radius: 10px; border-left: 4px solid #2196f3;'>
                <strong style='color: #1976d2;'>👤 You:</strong><br>
                <span style='color: #333;'>{message}</span>
            </div>
            """
        elif sender_type == "ai":
            html = f"""
            <div style='margin: 10px 0; padding: 10px; background-color: #f1f8e9; 
                        border-radius: 10px; border-left: 4px solid #4caf50;'>
                <strong style='color: #388e3c;'>🤖 AI Assistant:</strong><br>
                <span style='color: #333;'>{message}</span>
            </div>
            """
        elif sender_type == "ai_typing":
            html = f"""
            <div id='typing_indicator' style='margin: 10px 0; padding: 10px; background-color: #fff3e0; 
                        border-radius: 10px; border-left: 4px solid #ff9800;'>
                <strong style='color: #f57c00;'>🤖 AI Assistant:</strong><br>
                <span style='color: #666; font-style: italic;'>{message}</span>
            </div>
            """
        else:  # system
            # Determine system message type based on content
            if "✅" in message or "connected" in message.lower() or "ready" in message.lower():
                # Success message
                html = f"""
                <div style='margin: 10px 0; padding: 10px; background-color: #e8f5e8; 
                            border-radius: 8px; border-left: 3px solid #28a745;'>
                    <span style='color: #155724; font-size: 13px;'><strong>System:</strong> {message}</span>
                </div>
                """
            elif "❌" in message or "error" in message.lower() or "failed" in message.lower():
                # Error message
                html = f"""
                <div style='margin: 10px 0; padding: 10px; background-color: #f8d7da; 
                            border-radius: 8px; border-left: 3px solid #dc3545;'>
                    <span style='color: #721c24; font-size: 13px;'><strong>System:</strong> {message}</span>
                </div>
                """
            elif "⚠️" in message or "warning" in message.lower() or "disabled" in message.lower():
                # Warning message
                html = f"""
                <div style='margin: 10px 0; padding: 10px; background-color: #fff3cd; 
                            border-radius: 8px; border-left: 3px solid #ffc107;'>
                    <span style='color: #856404; font-size: 13px;'><strong>System:</strong> {message}</span>
                </div>
                """
            elif "🔍" in message or "checking" in message.lower() or "connecting" in message.lower():
                # Info/loading message
                html = f"""
                <div style='margin: 10px 0; padding: 10px; background-color: #d1ecf1; 
                            border-radius: 8px; border-left: 3px solid #17a2b8;'>
                    <span style='color: #0c5460; font-size: 13px;'><strong>System:</strong> {message}</span>
                </div>
                """
            else:
                # Default system message
                html = f"""
                <div style='margin: 10px 0; padding: 10px; background-color: #f8f9fa; 
                            border-radius: 8px; border-left: 3px solid #6c757d;'>
                    <span style='color: #495057; font-size: 13px;'><strong>System:</strong> {message}</span>
                </div>
                """
        
        cursor.insertHtml(html)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def update_streaming_response(self, partial_text):
        """Update the AI response as it streams in"""
        # Remove the typing indicator and replace with streaming response
        html_content = self.chat_display.toHtml()
        if 'typing_indicator' in html_content:
            # Remove typing indicator
            lines = html_content.split('\n')
            filtered_lines = []
            skip_until_div_end = False
            
            for line in lines:
                if 'typing_indicator' in line:
                    skip_until_div_end = True
                    continue
                if skip_until_div_end and '</div>' in line:
                    skip_until_div_end = False
                    continue
                if not skip_until_div_end:
                    filtered_lines.append(line)
            
            self.chat_display.setHtml('\n'.join(filtered_lines))
        
        # Add streaming response
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        streaming_html = f"""
        <div id='streaming_response' style='margin: 10px 0; padding: 10px; background-color: #f1f8e9; 
                    border-radius: 10px; border-left: 4px solid #4caf50;'>
            <strong style='color: #388e3c;'>🤖 AI Assistant:</strong><br>
            <span style='color: #333;'>{partial_text}<span style='animation: blink 1s infinite;'>|</span></span>
        </div>
        """
        
        # Remove previous streaming response if exists
        html_content = self.chat_display.toHtml()
        if 'streaming_response' in html_content:
            lines = html_content.split('\n')
            filtered_lines = []
            skip_until_div_end = False
            
            for line in lines:
                if 'streaming_response' in line:
                    skip_until_div_end = True
                    continue
                if skip_until_div_end and '</div>' in line:
                    skip_until_div_end = False
                    continue
                if not skip_until_div_end:
                    filtered_lines.append(line)
            
            self.chat_display.setHtml('\n'.join(filtered_lines))
        
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(streaming_html)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def on_response_complete(self, final_response):
        """Handle completion of AI response"""
        # Remove streaming response and add final formatted response
        html_content = self.chat_display.toHtml()
        if 'streaming_response' in html_content:
            lines = html_content.split('\n')
            filtered_lines = []
            skip_until_div_end = False
            
            for line in lines:
                if 'streaming_response' in line:
                    skip_until_div_end = True
                    continue
                if skip_until_div_end and '</div>' in line:
                    skip_until_div_end = False
                    continue
                if not skip_until_div_end:
                    filtered_lines.append(line)
            
            self.chat_display.setHtml('\n'.join(filtered_lines))
        
        # Add final response
        self.add_chat_message(final_response, "ai")
        
        # Re-enable input based on server status
        self.update_chat_input_state()
        if self.server_ready:
            self.chat_input.setFocus()

    def on_response_error(self, error_message):
        """Handle AI response error"""
        # Remove typing/streaming indicators
        html_content = self.chat_display.toHtml()
        for indicator_id in ['typing_indicator', 'streaming_response']:
            if indicator_id in html_content:
                lines = html_content.split('\n')
                filtered_lines = []
                skip_until_div_end = False
                
                for line in lines:
                    if indicator_id in line:
                        skip_until_div_end = True
                        continue
                    if skip_until_div_end and '</div>' in line:
                        skip_until_div_end = False
                        continue
                    if not skip_until_div_end:
                        filtered_lines.append(line)
                
                self.chat_display.setHtml('\n'.join(filtered_lines))
        
        self.add_chat_message(f"❌ Error: {error_message}", "system")
        
        # Re-enable input based on server status
        self.update_chat_input_state()
        if self.server_ready:
            self.chat_input.setFocus()



    def show_question(self, question):
        self.question_label.setText(question)
        self.progress_label.setText(f"Question {self.current_question + 1} of {len(self.asrs_questions)}")
        
        # Clear previous selections
        for rb in self.radio_buttons:
            rb.setAutoExclusive(False)
            rb.setChecked(False)
            rb.setAutoExclusive(True)

    def next_question(self):
        # Check if an option is selected
        selected = self.button_group.checkedButton()
        if not selected:
            QMessageBox.warning(
                self,
                "Selection Required",
                "Please select an option before continuing to the next question."
            )
            return
        
        # Save the response
        self.responses.append(selected.text())
        
        # Move to next question or show results
        self.current_question += 1
        
        if self.current_question >= len(self.asrs_questions):
            self.show_results()
        else:
            self.show_question(self.asrs_questions[self.current_question])
            
            # Update button text for last question
            if self.current_question == len(self.asrs_questions) - 1:
                self.next_button.setText("Complete Assessment →")

    def show_results(self):
        score_map = {"Never": 0, "Rarely": 1, "Sometimes": 2, "Often": 3, "Very Often": 4}
        total_score = sum(score_map.get(resp, 0) for resp in self.responses)

        # 🧠 Interpret the total score
        if total_score >= 18:
            interpretation = "High positive (likely ADHD)"
        elif total_score >= 14:
            interpretation = "Low positive (possible ADHD)"
        elif total_score >= 10:
            interpretation = "High negative (unlikely ADHD)"
        else:
            interpretation = "Low negative (unlikely ADHD)"

        # 📝 Display score and interpretation
        self.question_label.setText(f"✅ Screening Complete!\nTotal Score: {total_score}\n{interpretation}")
        
        # Hide old UI elements
        for rb in self.radio_buttons:
            rb.hide()
        self.next_button.hide()

        # ⚡ If positive score, offer to continue
        if total_score >= 14:
            self.diagnosis_button = QPushButton("👉 Proceed to Diagnosis")
            self.diagnosis_button.clicked.connect(self.start_diagnosis_phase)
            self.left_layout.addWidget(self.diagnosis_button)
        else:
            self.left_layout.addWidget(QLabel("🟢 No further action needed. You may close the app."))

    def restart_assessment(self):
        """Restart the ADHD assessment"""
        self.current_question = 0
        self.responses = []
        
        # Show all UI elements again
        self.progress_label.show()
        for rb in self.radio_buttons:
            rb.show()
            rb.setChecked(False)
        
        self.next_button.show()
        self.next_button.setText("Next Question →")
        
        # Remove result buttons if they exist
        if hasattr(self, 'diagnosis_button'):
            self.diagnosis_button.deleteLater()
        if hasattr(self, 'restart_button'):
            self.restart_button.deleteLater()
        
        # Show first question
        self.show_question(self.asrs_questions[self.current_question])

    # ─── adhd_app_gui.py ────────────────────────────────────────────────
    def start_diagnosis_phase(self):
        self.settings_window = SettingsWindow()
        self.settings_window.show()
    
    def closeEvent(self, event):
        """Clean up when app closes"""
        # Stop background workers
        if self.server_connection_worker and self.server_connection_worker.isRunning():
            self.server_connection_worker.stop()
            self.server_connection_worker.wait(1000)  # Wait up to 1 second
        
        # GPU worker cleanup removed
        
        if self.chat_worker and self.chat_worker.isRunning():
            self.chat_worker.terminate()
            self.chat_worker.wait(1000)
        
        event.accept()
    
if __name__ == "__main__":
    print("Starting ADHD App...")
    app = QApplication(sys.argv)
    print("QApplication created")
    window = ADHDApp()
    print("ADHDApp window created")
    window.show()
    print("Window shown, starting event loop...")
    sys.exit(app.exec_())