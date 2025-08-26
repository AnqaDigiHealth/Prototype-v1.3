# vLLM Loader.py - Beginner's Guide

## What is this file?
`loader.py` is a Python script that makes it easy to run and chat with AI models using vLLM (a fast inference engine). It handles all the complex setup and gives you two ways to use it: interactive chat or as a web API.

## Prerequisites
Before using this script, make sure you have:
- Python 3.8+ installed
- vLLM library installed (`pip install vllm`)
- Flask library installed (`pip install flask`)
- Sufficient system resources (the script is configured for large models)

## Two Ways to Use It

### Method 1: Interactive Chat (Beginner Friendly)
This starts a chat interface directly in your terminal.

```bash
# Make the file executable
chmod +x loader.py

# Start interactive chat
python3 loader.py
```

**What happens:**
1. The script starts a vLLM server in the background
2. Waits for the AI model to load (this can take 2-5 minutes)
3. Opens a chat interface where you can type messages
4. Type your questions and get AI responses

**Chat Commands:**
- Type your message and press Enter
- Type `/stream` to toggle streaming mode on/off
- Type `quit`, `exit`, or press Ctrl+C to stop

### Method 2: API Server (For Remote Access)
This creates a web API that other programs can use.

```bash
python3 loader.py --api
```

**What this does:**
- Starts the AI model server
- Creates a web API on port 5000
- Other applications can send HTTP requests to get AI responses

## Understanding the Output

When you start the script, you'll see messages like:
```
🚀 vLLM Server - Interactive Mode
Starting vLLM server...
Server starting with PID: 12345
⏳ Server not ready yet, waiting...
✅ vLLM Server is ready!
```

## Configuration Settings

The script uses these default settings (in the code):
- **Model**: `openai/gpt-oss-20b` (20 billion parameter model)
- **Max Length**: 32,000 tokens
- **Memory**: Uses 80% of available system memory
- **Server Port**: 8002 (for vLLM)
- **API Port**: 5000 (for web access)

## Common Issues & Solutions

### "Server failed to start"
- **Cause**: Not enough system memory or missing dependencies
- **Solution**: Install vLLM (`pip install vllm`) or use a smaller model

### "Server not ready yet, waiting..."
- **Cause**: Model is still loading (normal for large models)
- **Solution**: Wait patiently, can take 2-5 minutes

### Connection errors
- **Cause**: Firewall blocking ports or insufficient resources
- **Solution**: Check that ports 8002 and 5000 are available

## Using the API (Advanced)

If you're running in API mode, you can send requests like:

```bash
# Send a chat message
curl -X POST http://your-server-ip:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# Check if server is ready
curl http://your-server-ip:5000/status
```

## Stopping the Server

The script will automatically clean up when you:
- Press Ctrl+C
- Type `quit` or `exit` in interactive mode
- Send a SIGTERM signal

## Memory Requirements

This script is configured for a 20B parameter model which requires:
- **System Memory**: At least 16GB (preferably 24GB+)
- **RAM**: 8GB+ system memory
- **Storage**: 40GB+ free space for model weights

## Customization

To modify the script for your needs, look for these sections in the code:
- Change the model name in the `start_server()` method
- Adjust memory settings (`--memory-utilization`)
- Modify ports in the `__init__` method

## Getting Help

If you encounter issues:
1. Check the terminal output for error messages
2. Ensure all dependencies are installed
3. Verify you have sufficient system memory
4. Try with a smaller model first

## Support

If you face any problems just email me: **artaservices2021@gmail.com**

Hussain Nazary