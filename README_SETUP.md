# ADHD Diagnostic Tool

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
python launch_adhd_app.py
```

## Files

- `launch_adhd_app.py` - Main launcher (run this)
- `adhd_app_gui.py` - GUI application  
- `gptoss_client.py` - AI server client
- `simple_server_manager.py` - Server management
- `start_server.bat` - Manual server start
- `.env` - Server credentials (edit if needed)

## Configuration

Edit `.env` file to change server settings:
```
SERVER_IP=136.243.40.162
SERVER_USERNAME=anqa
SERVER_PASSWORD=adminQAZ135!!
SERVER_API_PORT=5000
```
## How It Works

The ADHD Diagnostic Tool consists of several components working together:

1. **GUI Application** (`adhd_app_gui.py`) - Main interface for ADHD assessment
2. **AI Server Client** (`gptoss_client.py`) - Handles communication with the LLM server
3. **Server Manager** (`simple_server_manager.py`) - Automatically starts and monitors the AI server
4. **Launcher** (`launch_adhd_app.py`) - Coordinates startup of all components

## Features

- **Automated Server Management**: Automatically starts the AI server when needed
- **Secure Credentials**: Uses environment variables for server authentication
- **Real-time AI Integration**: Connects to LLM for ADHD assessment assistance
- **User-friendly GUI**: Simple interface for conducting ADHD evaluations

## Troubleshooting

### Server Connection Issues
If you see connection errors:
1. Check your `.env` file has correct server credentials
2. Verify the server is accessible at the specified IP and port
3. Try running `python simple_server_manager.py` manually to test server startup

### GUI Not Starting
If the GUI doesn't appear:
1. Make sure all dependencies are installed: `pip install -r requirements.txt`
2. Check for error messages in the console
3. Try running `python adhd_app_gui.py` directly

### Environment Variables Not Loading
If credentials aren't working:
1. Ensure `.env` file exists in the project root
2. Check file format matches the example above
3. Restart the application after making changes

## Manual Server Management

If you need to start the server manually:
```bash
# Windows
start_server.bat

# Or run the server manager directly
python simple_server_manager.py
```

## Development

### Project Structure
```
adhd-diagnostic-tool/
├── adhd_app_gui.py          # Main GUI application
├── gptoss_client.py         # AI server client
├── simple_server_manager.py # Server management
├── launch_adhd_app.py       # Application launcher
├── start_server.bat         # Manual server startup
├── .env                     # Environment configuration
├── .env.example            # Environment template
├── requirements.txt         # Python dependencies
└── README_SETUP.md         # This file
```

### Adding New Features
1. Modify the GUI in `adhd_app_gui.py`
2. Update AI interactions in `gptoss_client.py`
3. Test with `python launch_adhd_app.py`

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- The server credentials are stored in plain text in `.env` - ensure proper file permissions
- Consider using more secure authentication methods for production use

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Ensure server connectivity and credentials are correct
4. Review console output for specific error messages