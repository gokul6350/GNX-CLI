# GNX CLI - AI Agent with Desktop & Mobile Control

A powerful Python-based AI agent that combines LLM reasoning with real-world automation. Uses Gemma 3 for planning and V_action vision model for precise desktop and mobile device control.

![GNX CLI Demo](./imgs/img1.png)
## Features

GNX CLI can control your computer and phone like a real person would:

- **Control Your Computer** - Take screenshots, click buttons, type text, open programs
- **Control Your Phone** - Take screenshots, tap buttons, type text, open apps  
- **Read & Write Files** - Create files, read content, edit text
- **Search the Internet** - Find information online, visit websites
- **Manage Tasks** - Create to-do lists, check them off, organize your work
- **Advanced Actions** - Wait for things to load, use keyboard shortcuts, automate workflows


## Architecture

![GNX Architecture](./imgs/architecture.png)
![GNX Sequence Flow](./imgs/sequence_flow.png)

### Workflow: User Goal → Gemma → V_action → Action Execution

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER GOAL                                                │
│    "Open calculator on desktop"                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. GEMMA ENGINE (Main LLM)                                  │
│    - Understands user intent                                │
│    - Plans action sequence                                  │
│    - Decides which tools to use                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SCREENSHOT CAPTURE                                       │
│    - Takes current screen/phone screenshot                  │
│    - Sends to V_action as context                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. V_ACTION MODEL (Vision-Language)                         │
│    - Analyzes screenshot                                    │
│    - Gets natural language instruction from Gemma          │
│    - Returns precise action + coordinates (0-1000 grid)    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. ACTION EXECUTION                                         │
│    - Click/tap at coordinates                              │
│    - Type text                                              │
│    - Press hotkeys                                          │
│    - Swipe/drag                                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. VERIFICATION LOOP                                        │
│    - Take new screenshot                                   │
│    - Check if goal achieved                                │
│    - Continue or report success                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Requirements
- Python 3.10+
- Windows/Mac/Linux
- For mobile: ADB (Android Debug Bridge) and connected Android device

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd "GNX CLI"

# Create virtual environment
python -m venv .venv

# Activate venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment
# Copy the example environment file to .env
# Windows:
copy .env.example .env
# Mac/Linux:
cp .env.example .env

---

## Usage

### Start GNX CLI

```bash
python main.py
```

### Example Commands

#### Desktop Automation
```
GNX: "Use computer use and open calculator"
```
Output:
```
✓ computer_screenshot: Screenshot captured
✓ computer_control: Click on Start button (679, 1047)
✓ computer_control: Type "calculator"
✓ computer_control: Click on Calculator app (725, 491)
✓ Task completed: Calculator opened successfully
```

#### Mobile Automation
```
GNX: "Open Settings on my phone"
```
Output:
```
✓ mobile_devices: Connected devices found
✓ mobile_connect: Connected to device RZCX904D1QV
✓ mobile_screenshot: Screen captured
✓ mobile_control: Tap on Settings icon
✓ Task completed: Settings app opened


```



#### File Operations
```
GNX: "List all Python files in src folder"
GNX: "Read the contents of main.py"
GNX: "Create a new file called notes.txt with content 'Hello World'"
```

#### Web Search
```
GNX: "Search for latest Python 3.13 features"
GNX: "Fetch the content from github.com"
```

#### Task Management
```
GNX: "Create a TODO list with: Task 1, Task 2, Task 3"
GNX: "Show my TODO list"
GNX: "Mark the first task as complete"
```

---

## Configuration

GNX CLI uses environment variables for configuration. You can set these in a `.env` file in the project root.

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | API key for Google Gemini models | Yes (if using Gemini) |
| `GROQ_API_KEY` | API key for Groq models | Yes (if using Groq) |
| `HF_TOKEN` | HuggingFace token for V_action vision model | Optional (Recommended) |
| `GNX_DEFAULT_PROVIDER` | Default LLM provider (`gemini` or `groq`) | No (Default: `gemini`) |

### Setting up .env

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your keys.

---

## Tools Reference

### Computer Control
```python
# Take screenshot
computer_screenshot()

# Execute instruction based on screen
computer_control(instruction="Click on the Start button")

# Direct text input
computer_type_text(text="hello world", press_enter=True)

# Keyboard shortcuts
computer_hotkey(keys="ctrl,c")

# Wait for UI
computer_wait(seconds=2.0)
```

### Mobile Control
```python
# Check devices
mobile_devices()

# Connect to device
mobile_connect(device_id="DEVICE_ID")

# Take screenshot
mobile_screenshot()

# Execute instruction
mobile_control(instruction="Tap on Settings icon")

# Direct interaction
mobile_tap(x=100, y=200)
mobile_swipe(direction="up")
mobile_button(button="back")
```

### File Operations
```python
# List directory
ls(path="src")

# Read file
read_file(path="main.py")

# Write file
write_file(path="test.txt", content="Hello")

# Edit file
edit_file(path="test.txt", old="Hello", new="Hi")

# Find files
glob(pattern="**/*.py")

# Search text
grep(query="import", path="src")
```

---

## ReAct Agent Architecture

GNX uses the ReAct (Reasoning + Acting) pattern:

1. **Reasoning** - Gemma thinks about the problem
2. **Acting** - Executes tools based on reasoning
3. **Observation** - Analyzes results and loops

The ReAct adapter provides intelligent tool selection and automatic retry logic.

---

## Project Structure

```
GNX CLI/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── src/
│   ├── gnx_engine/
│   │   ├── engine.py      # Main GNX engine
│   │   └── adapters.py    # ReAct adapter for tool orchestration
│   ├── tools/
│   │   ├── base.py        # Base tool utilities
│   │   ├── computer_use.py     # Desktop automation ✨ NEW
│   │   ├── mobile_use.py       # Mobile automation ✨ NEW
│   │   ├── file_ops.py    # File operations
│   │   ├── filesystem.py  # Directory listing
│   │   ├── system.py      # System utilities
│   │   ├── search.py      # File search
│   │   ├── todos.py       # TODO management
│   │   └── web_search.py  # Web search
│   ├── ui/
│   │   └── display.py     # Rich terminal UI
│   └── utils/
│       └── token_counter.py # Token usage tracking
├── .env.example           # Environment variables template (copy to .env)
└── imgs/
    ├── img1.png           # Demo image
    ├── architecture.png   # ReAct architecture diagram
    ├── sequence_flow.png  # Sequence/loop workflow diagram
    └── LAMx.png           # LAMx project logo
```


## Environment Template

The `.env.example` file documents the configurable keys that GNX CLI reads at runtime. Copy it to `.env`, replace the placeholders with your actual API keys, and store the file alongside the project root (it is ignored by Git).

```text
# GNX CLI Environment Variables
# Copy this file to .env and fill in your API keys

# Google Gemini API Key (for Gemini models)
GOOGLE_API_KEY=your_google_api_key_here

# Groq API Key (for Llama, Mixtral, and other Groq-hosted models)
GROQ_API_KEY=your_groq_api_key_here

# HuggingFace Token (for V_action vision model in computer_use)
HF_TOKEN=your_huggingface_token_here

# Default provider: "gemini" or "groq"
GNX_DEFAULT_PROVIDER=gemini

# Default model names (optional - will use defaults if not set)
# GEMINI_MODEL=gemma-3-27b-it
# GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```


---

## Key Technologies

- **Gemma 3** - LLM for reasoning and planning (27B-IT model)
- **V_action (Qwen3-VL)** - Vision-Language model for precise coordinate detection
- **LangChain** - Agent framework and tool management
- **Rich** - Beautiful terminal UI
- **PyAutoGUI** - Desktop automation
- **MSS** - Screenshot capture
- **ADB** - Mobile device control (via subprocess)
- **Google Generative AI** - Gemma API access

---

## Troubleshooting

### Issue: "Could not import ddgs python package"
```bash
pip install -U ddgs duckduckgo-search
```

### Issue: Mobile screenshot fails with path error
- Ensure workspace path doesn't have special characters
- Or use quotes: `"C:\Users\...\GNX CLI"`

### Issue: Computer screenshot not working
- Ensure no display scaling or use appropriate resolution settings
- Check pyautogui.FAILSAFE is disabled

### Issue: ADB not found
```bash
# Install Android SDK
# Add ADB to PATH
# Or specify full path in mobile_use.py

ADB_EXE = "C:\\path\\to\\adb.exe"
```

---

## Future Roadmap

- [ ] Support for more LLMs (Claude, GPT-4V, etc.)
- [ ] Browser automation (Selenium integration)
- [ ] Video recording of actions
- [ ] Multi-device coordination
- [ ] Custom action recording and playback
- [ ] Web UI dashboard
- [ ] Docker containerization
- [ ] Performance optimization and caching

---

## Contributing

Contributions welcome! Areas for improvement:
- Better error handling and recovery
- Additional action types (drag, scroll, etc.)
- Support for more devices and platforms
- Performance optimization

---

## License

MIT License - Feel free to use and modify

---

## My Journey: The Real Story

I was trying to build this AI agent for the last 2 months. Kept switching between different languages - Rust, Python, C++, Node.js. Finally came back to Python and accomplished everything that took 2 months of work... in literally a single day.

### What Happened

I don't know if I should be proud of my skills or be sad about how easy it was. Like, I spent 2 months on this. But nah, I'm not going to be sad. I'm taking it as experience - that's why I was able to do it in a single day.

### The Reality

Two months of switching languages, struggling with different ecosystems, hitting dead ends. Then one day, with Python and LangChain, everything just clicked:

- `computer_use.py` - boom, desktop automation done
- `mobile_use.py` - boom, mobile control done  
- Updated the ReAct adapter with proper instructions
- Integrated everything

```
GNX: "Use computer use and open calculator"
✓ Screenshot captured
✓ Start button clicked  
✓ Calculator opened
✓ SUCCESS
```

In one day.

### The Truth

Two months wasn't wasted. It was experience. Every failed attempt in Rust, every CMake fight in C++, every async confusion in Node.js - all of that taught me what works and what doesn't. When I sat down with Python, I already knew the patterns. I already understood the problem.

That's why it was so fast.

I took those 2 months of experience and built something in a day. That's not stupid. That's just how it works when you finally know what you're doing.

---


## 🔗 Part of LAMx Project

GNX CLI is a rewritten and evolved version of **[Axolot OS](https://github.com/gokul6350/Axolot-os)**, now optimized as a core component of the **LAMx** project - an integrated ecosystem for General AI-powered intelligence.



![LAMx Logo](./imgs/LAMx.png)

GNX CLI is a core component of the **LAMx** project - an integrated ecosystem for General AI-powered intelligence.

---

**Built with ❤️ after a lot of 💔**
