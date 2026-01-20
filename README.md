# GNX CLI - AI Agent with Desktop & Mobile Control

![Banner](./imgs/banner.jpeg)

## Essential Project Badges
[![Stars](https://img.shields.io/github/stars/gokul6350/GNX-CLI?style=social)](https://github.com/gokul6350/GNX-CLI)
[![Forks](https://img.shields.io/github/forks/gokul6350/GNX-CLI?style=social)](https://github.com/gokul6350/GNX-CLI)
[![Issues](https://img.shields.io/github/issues/gokul6350/GNX-CLI)](https://github.com/gokul6350/GNX-CLI/issues)

## AI Agent Theme Badges
[![GNX-CLI](https://img.shields.io/badge/GNX-CLI-8A2BE2?style=for-the-badge&logo=robot&logoColor=white)]()
[![AI Agent](https://img.shields.io/badge/AI_Agent-Next%20Gen-blueviolet?style=flat&logo=spark&logoColor=yellow)]()
[![Platforms](https://img.shields.io/badge/Desktop%20%26%20Android-E91E63?style=flat&logo=android&logoColor=white)]()

## Status & Tech Badges
[![License](https://img.shields.io/github/license/gokul6350/GNX-CLI)](https://github.com/gokul6350/GNX-CLI/blob/main/LICENSE)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
[![Discussions](https://img.shields.io/badge/Discussions-007ACC?style=flat&logo=github&logoColor=white)](https://github.com/gokul6350/GNX-CLI/discussions)

**GNX CLI** is a next-generation AI agent capable of perceiving and manipulating real-world interfaces. Built on a modular architecture, it combines **Native Tool Calling** (Llama 4 Scout/Groq) for rapid logic with a specialized **Vision Agent** (Qwen3-VL/Novita) for high-fidelity UI automation on both desktop and mobile. Developed by **Gokulbarath**.

## 📱 Mobile Demo


https://github.com/user-attachments/assets/42a5fde6-f226-480d-ab10-94136493f4ac

This clip shows GNX CLI running a full mobile automation sequence from the latest build.

## 🖥️ Computer Demo


https://github.com/user-attachments/assets/bec3e8a0-30ce-4096-829c-8e6ca0fb33cd



## 🚀 Key Features

- **🧠 Hybrid Intelligence:** Fast orchestrator LLM (Llama 4, Gemini, or GLM) plus specialized VLM (Qwen3-VL) for sight.
- **👁️ Autonomous Vision Agent:** Sub-agent loop that can see screens, reason about UI, and act (click, swipe, type).
- **🔌 MCP Support:** Works with the Model Context Protocol (GitHub, Filesystem, Memory servers).
- **📱 Mobile Automation:** Deep ADB integration for taps, swipes, and text input.
- **💻 Desktop Automation:** Mouse/keyboard control via PyAutoGUI with visual feedback loops.
- **📁 Modular Tooling:** Atomic tools for file ops, web search, system control, and UI automation.


## 🏗️ Architecture

![GNX Architecture](./imgs/architecture.png)
![GNX Sequence Flow](./imgs/sequence_flow.png)




### High-Level Routing

```mermaid
graph TD;
	 User[User Input] --> Engine[GNX Engine];
	 Engine -->|Selects Tool| Router{Tool Router};
    
	 subgraph "Standard Tools"
	 Router -->|File Ops| Files[FileSystem / Search];
	 Router -->|Web| Web[DuckDuckGo / Jina];
	 Router -->|MCP| MCP[MCP Servers];
	 end
    
	 subgraph "Automation & Vision"
	 Router -->|Simple| Atomic[Atomic Actions];
	 Atomic --> Desktop[Desktop Control];
	 Atomic --> Mobile[Mobile/ADB];
    
	 Router -->|Complex UI Tasks| Handoff[activate_vision_agent];
	 Handoff --> VisionLoop((Vision Agent Loop));
	 end
    
	 Files --> Output[Result];
	 Web --> Output;
	 MCP --> Output;
	 Desktop --> Output;
	 Mobile --> Output;
	 VisionLoop --> Output;
    
	 Output --> Engine;
	 Engine --> User;
```

#### Vision Agent Loop
When `activate_vision_agent` is called, the system switches to a VLM-driven feedback loop:

```mermaid
graph TD;
	 Start([Task Received]) --> Capture[Capture High-Res Screenshot];
	 Capture --> VLM[Qwen3-VL Analysis];
    
	 VLM -->|Reasoning + JSON| Decision{Decision};
    
	 Decision -->|Action| Executor[Execute Action];
	 Executor -->|Wait for UI| Capture;
    
	 Decision -->|Terminate| Success([Task Complete]);
	 Decision -->|Error| Fail([Report Failure]);
```

## 🛠️ Installation

### Requirements
- Python 3.10+
- Windows/Mac/Linux
- For mobile: ADB (Android Debug Bridge) and a connected Android device

### Setup

```bash
git clone https://github.com/Gokulbarath/GNX-CLI.git
cd "GNX CLI"

python -m venv .venv
.venv\Scripts\activate  # Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt

# Configure environment
copy .env.example .env  # Mac/Linux: cp .env.example .env
```

## 💻 Usage

Start the CLI:

```bash
python main.py
```

### Example Commands

1. General reasoning & files
	- "List all python files in src/tools and tell me what they do."
2. Web search
	- "Search for the latest features in Python 3.13."
3. Vision Agent (mobile)
	- Ensure your Android device is connected via ADB.
	- "Open Settings, find 'Display', and turn on Dark Mode." (Agent navigates, scrolls, and taps based on visual cues.)
4. Vision Agent (desktop)
	- "Open Calculator, calculate 55 * 12, and tell me the result."






## 📂 Project Structure

```
GNX CLI/
├── main.py                     # Entry point
├── requirements.txt            # Dependencies
├── README.md                   # This file
├── imgs/                       # Assets (demo, architecture, LAMx)
├── src/
│   ├── agents/
│   │   └── vision/             # Vision agent loop & prompts
│   ├── gnx_engine/             # Orchestrator, adapters, prompts
│   ├── mcp/                    # Model Context Protocol client
│   ├── tools/
│   │   ├── desktop/            # Mouse/keyboard/screenshot
│   │   ├── mobile/             # ADB/touch/system
│   │   ├── handoff/            # Sub-agent triggers
│   │   ├── file_ops.py         # File operations
│   │   ├── filesystem.py       # Directory listing
│   │   ├── system.py           # System utilities
│   │   ├── search.py           # File search
│   │   ├── todos.py            # TODO management
│   │   ├── web_search.py       # Web search
│   │   └── ui_automation.py    # UI automation helpers
│   ├── ui/                     # Display utilities
│   ├── utils/                  # Logging, token counting
│   └── vision_client/          # VLM API client and types
└── .env.example                # Environment template
```

## 🧾 Environment Template

```text
# GNX CLI Environment Variables

# Groq API Key (primary orchestrator)
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Key (fallback/alternative)
GOOGLE_API_KEY=your_google_api_key_here

# HuggingFace Token (for V_action vision model)
HF_TOKEN=your_huggingface_token_here

# ZhipuAI API Key (GLM-4.5 text-only series)
ZHIPUAI_API_KEY=your_zhipuai_api_key_here

# Default provider: glm | groq | gemini
GNX_DEFAULT_PROVIDER=glm

# Optional model overrides
# GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
# GEMINI_MODEL=gemini-1.5-flash
# GLM_MODEL=glm-4.5
```


## 🗺️ Future Roadmap

- [ ] Web UI dashboard
- [ ] Performance optimization and caching
- [ ] Personalization

## 🔗 Part of LAMx Project

GNX CLI is a rewritten and evolved version of **[Axolot OS](https://github.com/gokul6350/Axolot-os)**, now optimized as a core component of the **LAMx** project—an integrated ecosystem for general AI-powered intelligence.

![LAMx Logo](./imgs/LAMx.png)

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a PR.

## 📜 License

MIT License — see the LICENSE file for details.

---

**Built with ❤️ after a lot of 💔**
