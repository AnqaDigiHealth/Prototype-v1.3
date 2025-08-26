#!/usr/bin/env python3
"""
Simple Server Manager - Checks if server is ready and can start server
"""
import time
import requests
import os
import subprocess
from typing import Optional, Callable
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class SimpleServerManager:
    def __init__(self, 
                 server_ip: str = None,
                 api_port: int = None):
        # Load from environment variables with fallback defaults
        self.server_ip = server_ip or os.getenv("SERVER_IP", "136.243.40.162")
        self.api_port = api_port or int(os.getenv("SERVER_API_PORT", "5000"))
        self.username = os.getenv("SERVER_USERNAME", "anqa")
        self.ssh_process = None
        
    def wait_for_server_ready(self, callback=None, max_wait: int = 300) -> bool:
        """
        Wait for the server to be ready (up to 5 minutes)
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.is_server_ready():
                return True
            
            # Update callback if provided
            if callback:
                elapsed = int(time.time() - start_time)
                callback(f"⏳ Waiting for server... ({elapsed}s)")
            
            time.sleep(3)
        
        return False
    
    def is_server_ready(self) -> bool:
        """
        Check if server is ready to accept requests by testing the actual chat endpoint
        """
        try:
            # Test the actual chat endpoint that the app uses
            url = f"http://{self.server_ip}:{self.api_port}/chat"
            test_payload = {"message": "ping"}
            response = requests.post(url, json=test_payload, timeout=5)
            return response.status_code == 200 and response.json().get("response") is not None
        except Exception:
            return False
    
    def start_server_ssh(self, status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Start server via SSH
        Returns True if SSH process started successfully, False otherwise
        """
        try:
            if status_callback:
                status_callback("🚀 Starting server via SSH...")
            
            # SSH command to start the loader
            ssh_cmd = [
                "ssh", 
                f"{self.username}@{self.server_ip}",
                "cd ~ && source ~/oss312/bin/activate && python3 loader.py --api"
            ]
            
            self.ssh_process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if status_callback:
                status_callback("✅ SSH connection established. Server starting...")
            
            return True
        except Exception as e:
            if status_callback:
                status_callback(f"❌ Failed to start SSH: {e}")
            return False
    
    def stop_server(self):
        """Stop the SSH server process if running"""
        if self.ssh_process:
            self.ssh_process.terminate()
            self.ssh_process = None

# Test the simple server manager
if __name__ == "__main__":
    manager = SimpleServerManager()
    
    print("Checking if server is ready...")
    if manager.is_server_ready():
        print("✅ Server is already ready!")
    else:
        print("❌ Server not ready. Please start it manually.")
        print("Run: start_server.bat")
        
        def status_callback(message):
            print(message)
        
        print("Waiting for server to become ready...")
        if manager.wait_for_server_ready(status_callback):
            print("✅ Server is now ready!")
        else:
            print("❌ Server did not become ready within timeout")