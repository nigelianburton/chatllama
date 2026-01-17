# ChatLlama Automation Mode - User Guide

## Overview

ChatLlama now supports **automation mode** for testing and batch processing of messages. This feature allows you to programmatically send messages to the LLM and automatically close the application based on special markers in an input file.

## Purpose

Automation mode enables:
- **Automated Testing**: Run the app with predefined test inputs, verify responses through logs
- **Batch Processing**: Process multiple questions in a single session
- **CI/CD Integration**: Integrate ChatLlama testing into development pipelines
- **Log Verification**: All interactions are logged to timestamped session files for analysis

## Usage

### Basic Command

```powershell
conda activate chatllama
python chat.py --input-file test_input.txt
```

### Alternative Syntax

You can also use `--test-file` instead of `--input-file`:

```powershell
python chat.py --test-file test_input.txt
```

## Input File Format

Create a text file where each line is a message to send to the model:

```
# Comments start with # and are ignored
# Empty lines are also ignored

What is Python?
Explain machine learning
How do transformers work?
EXIT
```

### Special Markers

- **`EXIT`** - Triggers automatic application shutdown after the model responds to the previous message
- **`#EXIT`** - Same as EXIT (allows commenting the exit marker)
- **`QUIT`** - Synonym for EXIT
- **`#QUIT`** - Commented exit marker

### Comment Syntax

- Lines starting with `#` are treated as comments and ignored
- Empty lines are skipped
- Whitespace is preserved in messages

## Example Input File

### `test_input.txt`
```
# Basic functionality test
# Test 1: Simple greeting
Hello, how are you?

# Test 2: Knowledge question
What is the capital of France?

# Test 3: Explanation request
Explain the concept of recursion in programming

# All tests complete, exit after response
EXIT
```

## Logging and Verification

All automation mode interactions are logged in three places:

### 1. **Main Log** (`chatllama.log`)
Cumulative log of all sessions - useful for long-term tracking

### 2. **Session Log** (`logs/session_YYYY-MM-DD_HH-MM-SS.log`)
Per-session detailed log with precise timestamp
- Shows when each message was sent
- Shows when model responses were received
- Shows exit marker detection
- Perfect for debugging individual test runs

Example session log:
```
2024-01-15 14:32:05,123 - INFO - ============================================================
2024-01-15 14:32:05,124 - INFO - ChatLlama started at 2024-01-15 14:32:05
2024-01-15 14:32:05,124 - INFO - Session log: logs/session_2024-01-15_14-32-05.log
2024-01-15 14:32:05,125 - INFO - ============================================================
2024-01-15 14:32:07,456 - INFO - Automation mode: loaded 3 messages from test_input.txt
2024-01-15 14:32:10,789 - INFO - Automation: sending message: What is Python?...
2024-01-15 14:32:15,234 - INFO - Automation: received exit marker, closing application
2024-01-15 14:32:17,567 - INFO - Application closing
```

### 3. **Console Output**
Real-time log output to the terminal while the app runs

## How It Works

1. **Startup**
   - Chat.py is launched with `--input-file` argument
   - Messages are loaded from the file and parsed
   - UI is built and displayed (you can watch the chat happen)
   - Default model is loaded

2. **Message Processing**
   - After 2 seconds (UI ready), first message is sent
   - Model processes and responds
   - Response appears in chat history
   - Automatically scrolls to show new content

3. **Next Message**
   - After response completes, next message is sent after 1 second delay
   - Process repeats for each message in file
   - Each message and response is logged

4. **Exit Detection**
   - When `EXIT`, `#EXIT`, `QUIT`, or `#QUIT` is encountered
   - Application closes gracefully after 2 seconds
   - All threads and processes are cleaned up
   - Logs are flushed to disk

## Real-World Example

### Scenario: Testing Model Knowledge

**Input file (`knowledge_test.txt`):**
```
# Knowledge Test Suite for ChatLlama

# Question 1: Programming
What are the three main principles of object-oriented programming?

# Question 2: History
What year did World War II end?

# Question 3: Science
Explain photosynthesis in one sentence

# Question 4: Logic puzzle
If John is taller than Mary, and Mary is taller than Sarah, who is the tallest?

EXIT
```

**Run the test:**
```powershell
python chat.py --input-file knowledge_test.txt
```

**Verify results:**
```powershell
# Check the session log for completeness
Get-Content logs/session_2024-01-15_14-32-05.log | Select-String "Automation"

# Check all responses were captured
Get-Content logs/session_2024-01-15_14-32-05.log | Select-String "Assistant"
```

## Implementation Details

### Code Changes

1. **argparse Integration**
   - Added `--input-file` and `--test-file` command-line arguments
   - Helps with CI/CD integration and batch processing

2. **Automation Mode Methods**
   - `_load_input_file()` - Parses input file, handles comments and exit markers
   - `_process_next_automation_message()` - Sends next message from queue
   - `_schedule_shutdown()` - Gracefully closes app with cleanup
   - `closeEvent()` - Proper cleanup of threads and subprocesses

3. **Signal Integration**
   - Chat completion signals now trigger next message in automation mode
   - Non-blocking architecture preserved (workers/threads still used)
   - UI remains responsive (can watch messages being processed)

4. **Logging Integration**
   - Session-specific logs capture automation events
   - Timestamps show when each message was processed
   - Perfect for post-test analysis

## Troubleshooting

### Messages Not Being Sent
- Ensure model is loaded (wait for "Ready" status in UI)
- Check that input file exists and is readable
- Verify file format (one message per line)
- Check `chatllama.log` for errors

### App Doesn't Exit
- Ensure EXIT marker is present in input file
- Make sure model finishes responding (wait for response in UI)
- Check logs for shutdown messages

### Empty Responses
- Model may not be responding (check status in UI)
- Check llama-server is running or model loaded successfully
- Review `chatllama.log` for model loading errors

### Log Files Not Created
- Ensure `logs/` directory exists (created automatically)
- Check file permissions on the logs directory
- Verify disk space is available

## Advanced Usage

### Integration with Testing Frameworks

You can call ChatLlama from test frameworks:

```python
import subprocess
import sys
from pathlib import Path

def test_chatllama_batch():
    """Test ChatLlama with batch input."""
    test_file = Path("test_input.txt")
    
    # Create input file
    test_file.write_text("""
What is Python?
Explain recursion
EXIT
""")
    
    # Run ChatLlama in automation mode
    result = subprocess.run(
        [sys.executable, "chat.py", "--input-file", str(test_file)],
        timeout=60,
        capture_output=True,
        text=True
    )
    
    # Verify success (exit code should be 0)
    assert result.returncode == 0, f"ChatLlama failed: {result.stderr}"
    
    # Verify logs contain expected content
    session_logs = list(Path("logs").glob("session_*.log"))
    assert len(session_logs) > 0, "No session logs found"
    
    latest_log = max(session_logs)
    log_content = latest_log.read_text()
    
    assert "What is Python?" in log_content
    assert "Automation: received exit marker" in log_content
    
    print(f"✓ Test passed. Session log: {latest_log}")
```

## Performance Considerations

- **Model Loading**: Takes time, use same model for multiple tests
- **Response Time**: Depends on model size and GPU (see in UI during run)
- **Log File Size**: Each message/response is logged (session logs grow with input size)
- **Memory**: Single model loaded, threads cleaned up after each response

## Future Enhancements

Potential improvements to automation mode:
- [ ] Parallel message processing
- [ ] Response validation/assertions in input file
- [ ] Expected output format specifications
- [ ] Performance metrics collection
- [ ] Report generation (HTML, JSON)
- [ ] Retry logic for failed responses
- [ ] Custom timeout per message
