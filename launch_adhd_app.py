#!/usr/bin/env python3
"""
ADHD App Launcher - Launches UI immediately with automatic SSH setup
"""
import sys
from PyQt5.QtWidgets import QApplication
from auto_ssh_manager import AutoSSHManager

class ADHDLauncher:
    def __init__(self):
        # Create shared SSH manager instance
        self.ssh_manager = AutoSSHManager()
    
    def launch(self):
        """Launch UI immediately with background SSH setup"""
        app = QApplication(sys.argv)
        
        # Start SSH connection in background thread during app startup
        self.ssh_manager.connect_async()
        
        # Import and start the main app immediately without waiting for SSH
        from adhd_app_gui import ADHDApp
        
        # Create and show the main window - pass SSH manager for shared access
        window = ADHDApp(ssh_manager=self.ssh_manager)
        window.show()
        
        return app.exec_()
    
    def get_ssh_manager(self):
        """Make SSH connection available to main app through shared instance"""
        return self.ssh_manager

if __name__ == "__main__":
    launcher = ADHDLauncher()
    sys.exit(launcher.launch())