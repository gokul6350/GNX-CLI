# GNX CLI - AI Agent with Desktop & Mobile Control

A powerful Python-based AI agent that combines LLM reasoning with real-world automation. Uses Gemma 3 for planning and V_action vision model for precise desktop and mobile device control.

![GNX CLI Demo](./imgs/img1.png)

## Features

### 🖥️ Computer Use Tools
- **computer_screenshot** - Capture desktop screen state
- **computer_control** - Vision-based desktop automation (click, type, interact with UI)
- **computer_type_text** - Type text at cursor position
- **computer_hotkey** - Press keyboard shortcuts
- **computer_wait** - Wait for UI elements to load

### 📱 Mobile Use Tools (via ADB)
- **mobile_devices** - List connected Android devices
- **mobile_connect** - Connect to specific device
- **mobile_screenshot** - Capture phone screen
- **mobile_control** - Vision-based mobile automation
- **mobile_tap**, **mobile_swipe**, **mobile_button** - Direct device control
- **mobile_type_text** - Type on mobile keyboard

### 📁 File System Tools
- **ls** - List directory contents
- **read_file** - Read file contents
- **write_file** - Create/write files
- **edit_file** - Edit existing files
- **glob** - Find files by pattern
- **grep** - Search text in files

### 🔍 Web & Search Tools
- **web_search** - DuckDuckGo search with summary
- **web_search_detailed** - Detailed search with URLs and snippets
- **fetch_url** - Fetch and read webpage content

### ✅ Task Management
- **write_todos** - Create TODO lists
- **read_todos** - Display TODO items
- **mark_complete** - Mark tasks as done

---

## Architecture

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

# Set Google API key (for Gemma)
export GOOGLE_API_KEY="your-api-key"

# Optional: Set HuggingFace token (for V_action model)
export HF_TOKEN="your-hf-token"
```

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

### HuggingFace Token (for V_action)
Models are accessed via HuggingFace Inference API:

```bash
export HF_TOKEN="hf_..." # Your HuggingFace API token
```

### Google API Key (for Gemma)
Set in environment:

```bash
export GOOGLE_API_KEY="AIza..."
```

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
└── hybrid_cli/            # Original implementation (reference)
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

## My Journey: From 2 Months of Struggle to 1 Day of Glory

### The Struggle (2 Months)

Two months ago, I started with an ambitious vision: build an AI agent that could understand natural language and execute real-world actions on desktop and mobile devices. Simple idea, right? Wrong.

I jumped between languages like a confused programmer on a caffeine high:

**Month 1 - The Rust Phase**
I thought, "Rust is fast, Rust is memory-safe, Rust will be perfect!" Spent 3 weeks learning Rust's borrow checker, fighting with lifetimes, and getting frustrated with the compiler. Built some basic tooling, but realized the ML ecosystem in Rust was... limited. Moved on.

**Month 1 - The C++ Interlude**
"C++ has everything!" I said confidently. Revisited pointers, memory management, and build systems. Got 2 weeks in before realizing I was spending more time fighting CMake than writing agent logic. The vision was slipping away.

**Month 2 - Node.js Adventure**
"JavaScript everywhere, right?" Tried building with TypeScript, set up the project, got halfway through tool orchestration before hitting the async/await wall and thinking about Python the entire time.

**Month 2 - Back to Python (Reluctantly)**
Finally admitted: Python is the king for this use case. LangChain, Gemini API, PIL, PyAutoGUI - everything just works. But I was burned out, thinking the project was doomed.

### The Revelation (1 Day)

Then something clicked. Instead of reinventing the wheel with different approaches in each language, I sat down with Python, pulled from what I learned in each language:

- **Rust's rigor** → Proper error handling and type hints
- **C++'s efficiency** → Optimized screenshot capture with MSS
- **Node's async mindset** → Concurrent tool execution in ReAct loop
- **Python's pragmatism** → Rapid iteration and integration

Armed with 2 months of failed attempts and lessons learned, I built the entire system in one day:

1. **computer_use.py** (2 hours) - Desktop automation with V_action integration
2. **mobile_use.py** (2 hours) - Mobile automation via ADB
3. **adapters.py updates** (1 hour) - ReAct workflow with detailed prompts
4. **Integration & testing** (1 hour) - Everything working together

By end of day:
```
GNX: "Use computer use and open calculator"
✓ Screenshot captured
✓ Start button clicked  
✓ Calculator opened
✓ SUCCESS
```

### The Reflection

Should I be proud or sad?

**The Sad Part**: Wow, I wasted 2 months on dead ends and language exploration.

**The Proud Part**: Those 2 months weren't wasted - they were *education*. Each language taught me different paradigms:
- Rust taught me to think about ownership and safety
- C++ taught me about performance and resources
- Node taught me about async patterns and event-driven architecture
- And all of that made my Python solution **better** and more thoughtful

The speed on Day 1 wasn't because Python is superior (though it is for this). It was because I had **tried and failed** in other contexts. I knew what wouldn't work. I knew the patterns that matter. I had built mental models across 4 different ecosystems.

### The Real Lesson

**Skills compound across languages.** The concepts:
- Agent architecture
- Tool orchestration
- Vision-language model integration
- Error handling
- System design

...these aren't Python-specific. I learned them through struggle in multiple languages. That struggle was the real education.

So am I sad about wasting 2 months? No. Because I didn't waste them - I *invested* them. And that investment paid off with a system built thoughtfully, quickly, and with the wisdom of 4 different programming paradigms.

To anyone reading this:
- **Don't judge yourself for switching languages** while learning
- **Each failure teaches you something** about different approaches
- **The "wasted" time is actually compound interest** in your overall skill
- **The speed comes not from the language, but from understanding the problem better**

That's why I built in 1 day what took 2 months of scattered attempts.

And honestly? That feels pretty good. 🚀

---

**Built with ❤️ and a lot of ☕**

