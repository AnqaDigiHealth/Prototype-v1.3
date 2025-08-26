import paramiko
from paramiko import AutoAddPolicy
import os
import logging
from dotenv import load_dotenv
import threading
import time

class AutoSSHManager:
    """
    Manages automatic SSH connection to remote server with environment setup and model loading.
    Handles connection, authentication, command execution, and AI model startup for the ADHD app.
    """
    
    def __init__(self):
        self.ssh_client = None
        self.connected = False
        self.error_message = ""
        self.connection_thread = None
        self.model_loading_thread = None
        
        # Model loading status
        self.model_loading = False
        self.model_ready = False
        self.model_error = ""
        self.current_status = "Initializing..."
        
        # Setup logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        env_loaded = load_dotenv()
        if env_loaded:
            self.logger.info("Environment variables loaded from .env file")
        else:
            self.logger.warning("No .env file found or failed to load")
        
        # SSH connection details from .env
        self.server_ip = os.getenv('SERVER_IP', '136.243.40.162')
        self.username = os.getenv('SERVER_USERNAME', 'anqa')
        self.password = os.getenv('SERVER_PASSWORD')
        
        # Debug: Check if credentials are loaded
        if not self.password:
            self.logger.error("No password found in environment variables!")
        else:
            self.logger.info(f"Loaded credentials for {self.username}@{self.server_ip} (password length: {len(self.password)})")
        
    def connect_and_setup(self) -> bool:
        """
        Connect via SSH and setup environment.
        Returns True if successful, False otherwise.
        """
        try:
            self.current_status = "Connecting to server..."
            
            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(AutoAddPolicy())
            
            self.logger.info(f"Attempting SSH connection to {self.username}@{self.server_ip}")
            
            # Connect to server with better parameters
            self.ssh_client.connect(
                hostname=self.server_ip,
                username=self.username,
                password=self.password,
                timeout=60,  # Longer timeout
                banner_timeout=30,
                auth_timeout=30,
                look_for_keys=False,  # Don't look for SSH keys
                allow_agent=False     # Don't use SSH agent
            )
            
            self.logger.info("SSH connection established successfully")
            self.current_status = "Setting up environment..."
            
            # Execute environment setup command
            setup_command = "cd ~ && source ~/oss312/bin/activate"
            stdin, stdout, stderr = self.ssh_client.exec_command(setup_command)
            
            # Wait for command completion
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                self.logger.info("Environment setup completed successfully")
                self.connected = True
                self.error_message = ""
                self.current_status = "Environment ready"
                
                # Check if model is already running before starting new one
                if self._test_model_api():
                    self.model_ready = True
                    self.model_loading = False
                    self.current_status = "AI model already running and ready!"
                    self.logger.info("Found existing AI model already running")
                else:
                    # Start model loading automatically after SSH connection
                    self.start_model_loading()
                return True
            else:
                error_output = stderr.read().decode('utf-8')
                self.error_message = f"Environment setup failed: {error_output}"
                self.logger.error(self.error_message)
                self.current_status = f"Environment setup failed: {error_output}"
                return False
                
        except paramiko.AuthenticationException:
            self.error_message = "SSH authentication failed - check credentials"
            self.logger.error(self.error_message)
            self.current_status = "Authentication failed"
            return False
            
        except paramiko.SSHException as e:
            self.error_message = f"SSH connection error: {str(e)}"
            self.logger.error(self.error_message)
            self.current_status = f"Connection error: {str(e)}"
            return False
            
        except Exception as e:
            self.error_message = f"Unexpected error during SSH setup: {str(e)}"
            self.logger.error(self.error_message)
            self.current_status = f"Setup error: {str(e)}"
            return False
    
    def connect_async(self):
        """
        Start SSH connection in background thread.
        """
        if self.connection_thread and self.connection_thread.is_alive():
            self.logger.warning("SSH connection already in progress")
            return
            
        self.connection_thread = threading.Thread(target=self.connect_and_setup)
        self.connection_thread.daemon = True
        self.connection_thread.start()
        self.logger.info("SSH connection started in background")
    
    def get_connection(self):
        """
        Return active SSH connection for app use.
        Returns None if not connected.
        """
        if self.connected and self.ssh_client:
            return self.ssh_client
        return None
    
    def is_connected(self) -> bool:
        """
        Check if SSH connection is active.
        """
        return self.connected and self.ssh_client is not None
    
    def get_error_message(self) -> str:
        """
        Get last error message if connection failed.
        """
        return self.error_message
    
    def start_model_loading(self):
        """
        Start AI model loading in background thread.
        """
        if self.model_loading_thread and self.model_loading_thread.is_alive():
            self.logger.warning("Model loading already in progress")
            return
            
        if not self.connected:
            self.logger.error("Cannot start model loading - SSH not connected")
            return
            
        self.model_loading_thread = threading.Thread(target=self._load_model)
        self.model_loading_thread.daemon = True
        self.model_loading_thread.start()
        self.logger.info("Model loading started in background")
    
    def _load_model(self):
        """
        Execute model loading commands on remote server and monitor actual progress.
        """
        try:
            self.model_loading = True
            self.current_status = "Starting AI model server..."
            
            # First, kill any existing loader.py processes
            kill_command = "pkill -f 'python.*loader.py' || true"
            self.ssh_client.exec_command(kill_command)
            time.sleep(2)
            
            # Start loader.py in background and redirect output to a log file
            model_command = "cd ~ && source ~/oss312/bin/activate && nohup python3 loader.py --api > loader_output.log 2>&1 &"
            
            self.logger.info("Starting AI model with loader.py --api")
            
            # Execute the command to start in background
            stdin, stdout, stderr = self.ssh_client.exec_command(model_command)
            stdout.read()  # Wait for command to complete
            
            self.current_status = "Model server starting in background..."
            
            # Monitor the log file and test API periodically
            start_time = time.time()
            timeout = 600  # 10 minutes timeout
            last_log_size = 0
            
            while time.time() - start_time < timeout:
                try:
                    # Check the log file for progress
                    log_command = "tail -n 20 ~/loader_output.log 2>/dev/null || echo 'No log yet'"
                    stdin, stdout, stderr = self.ssh_client.exec_command(log_command)
                    log_output = stdout.read().decode('utf-8')
                    
                    if log_output and log_output != 'No log yet':
                        # Parse the log output for status - check most recent status first
                        if "Serving Flask app" in log_output or "Running on" in log_output:
                            self.current_status = "API server running, testing model..."
                        elif "Starting API server" in log_output:
                            self.current_status = "Starting Flask API server..."
                        elif "vLLM Server is ready" in log_output or "✅" in log_output:
                            self.current_status = "vLLM server ready, starting API..."
                        elif "Server not ready yet" in log_output or "⏳" in log_output:
                            self.current_status = "Loading model weights (this may take several minutes)..."
                        elif "Server starting with PID" in log_output:
                            self.current_status = "vLLM server process started, loading model..."
                        elif "Starting vLLM server" in log_output:
                            self.current_status = "Starting vLLM server..."
                        
                        # Check for errors in log
                        if "error" in log_output.lower() or "failed" in log_output.lower():
                            self.model_error = f"Model loading error found in log"
                            self.logger.error(f"Error in log: {log_output}")
                            self.current_status = "Model loading failed"
                            self.model_loading = False
                            return
                    
                    # Test if API is actually responding
                    if self._test_model_api():
                        self.model_ready = True
                        self.model_loading = False
                        self.current_status = "AI model ready and tested!"
                        self.logger.info("AI model is fully ready and tested")
                        return
                    
                    # Check if process is still running
                    check_process = "pgrep -f 'python.*loader.py' || echo 'not running'"
                    stdin, stdout, stderr = self.ssh_client.exec_command(check_process)
                    process_check = stdout.read().decode('utf-8').strip()
                    
                    if process_check == 'not running':
                        # Process died, check log for errors
                        self.model_error = "Model process stopped unexpectedly"
                        self.current_status = "Model process failed"
                        self.model_loading = False
                        self.logger.error("Model process is not running")
                        return
                    
                except Exception as e:
                    self.logger.warning(f"Error checking model status: {str(e)}")
                
                time.sleep(5)  # Check every 5 seconds
            
            # If we get here, model loading timed out
            self.model_error = "Model loading timed out after 10 minutes"
            self.current_status = "Model loading timed out (check server manually)"
            self.model_loading = False
            self.logger.warning("Model loading timed out")
            
        except Exception as e:
            self.model_error = f"Error during model loading: {str(e)}"
            self.logger.error(self.model_error)
            self.current_status = f"Model loading error: {str(e)}"
            self.model_loading = False
    
    def _test_model_api(self):
        """
        Test if the model API is actually working by checking status endpoint.
        """
        try:
            # Check the status endpoint
            status_command = "curl -s --connect-timeout 5 http://localhost:5000/status"
            stdin, stdout, stderr = self.ssh_client.exec_command(status_command)
            status_response = stdout.read().decode('utf-8').strip()
            
            # Check if we got a valid status response
            if status_response and '"ready":true' in status_response:
                self.logger.info(f"Model API is ready: {status_response}")
                return True
            elif status_response and 'connection' not in status_response.lower():
                self.logger.info(f"Model API responding but not ready: {status_response}")
                return False
            else:
                self.logger.info("Model API not responding yet")
                return False
                
        except Exception as e:
            self.logger.warning(f"Model API test error: {str(e)}")
            return False
    
    def is_model_ready(self) -> bool:
        """
        Check if AI model is ready for use.
        """
        return self.model_ready
    
    def is_model_loading(self) -> bool:
        """
        Check if AI model is currently loading.
        """
        return self.model_loading
    
    def get_current_status(self) -> str:
        """
        Get current status message for UI display.
        """
        return self.current_status
    
    def get_model_error(self) -> str:
        """
        Get model loading error message if any.
        """
        return self.model_error
    
    def disconnect(self):
        """
        Close SSH connection gracefully.
        """
        if self.ssh_client:
            try:
                self.ssh_client.close()
                self.logger.info("SSH connection closed")
            except Exception as e:
                self.logger.error(f"Error closing SSH connection: {str(e)}")
            finally:
                self.ssh_client = None
                self.connected = False
    
    def stop_model_and_disconnect(self):
        """
        Stop the AI model and disconnect SSH gracefully.
        """
        if self.connected and self.ssh_client:
            try:
                # Kill the loader.py process to unload the model
                self.logger.info("Stopping AI model...")
                kill_command = "pkill -f 'python.*loader.py'"
                self.ssh_client.exec_command(kill_command)
                time.sleep(2)  # Give it time to stop
                self.logger.info("AI model stopped")
            except Exception as e:
                self.logger.error(f"Error stopping model: {str(e)}")
        
        self.disconnect()
    
    def __del__(self):
        """
        Cleanup SSH connection on object destruction.
        """
        self.disconnect()