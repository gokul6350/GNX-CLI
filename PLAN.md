# VL Agent Integration & Auto-Switching Plan

## Overview
Currently, vision capabilities are hidden inside the `computer_control` tool, creating an opaque dependency and limiting the system's flexibility. The goal is to implement a **Sub-Agent Architecture** where the Main Agent (Text/Orchestrator) explicitly hands off visual tasks to a specialized **Vision Agent**. 

This plan also focuses on **Modularization** to reduce file complexity by splitting monolithic files into smaller modules managed in dedicated directories.

## Objectives
1.  **Decouple Vision Logic**: Remove hidden VLM calls from execution tools.
2.  **Modularize Codebase**: Split large files into focused modules (folders/files).
3.  **Create `VisionAgent`**: A dedicated agent loop powered by VLM.
4.  **Implement Handoff**: `activate_vision_agent` tool.
5.  **Refactor Tools**: Convert "Magic" tools into atomic, single-purpose tools.

## Architecture & Modularization

### 1. New Vision Client Package: `src/vision_client/`
Move and refactor `src/gnx_engine/vl_provider.py` into a proper package:
-   `src/vision_client/__init__.py`: Exports.
-   `src/vision_client/client.py`: `VisionModelClient` class (generic, no tool logic).
-   `src/vision_client/types.py`: `ActionResult` and data structures.
-   `src/vision_client/config.py`: Configuration loading (config.py/env vars).

### 2. New Vision Agent Package: `src/agents/vision/`
Implementation of the sub-agent loop:
-   `src/agents/vision/__init__.py`: Exports `VisionAgent`.
-   `src/agents/vision/core.py`: The `VisionAgent` class and loop logic.
-   `src/agents/vision/prompts.py`: System prompts for Desktop and Mobile modes.
-   `src/agents/vision/parser.py`: Output parsing logic (JSON -> Action).

### 3. Refactor Desktop Tools: `src/tools/desktop/`
Split `src/tools/computer_use.py` into atomic modules:
-   `src/tools/desktop/__init__.py`: Exports tool list `DESKTOP_TOOLS`.
-   `src/tools/desktop/screenshot.py`: `computer_screenshot` and capture logic.
-   `src/tools/desktop/mouse.py`: `desktop_click`, `desktop_drag`, `desktop_scroll`.
-   `src/tools/desktop/keyboard.py`: `desktop_type`, `computer_hotkey`.
-   **Change**: Tools will accept explicit coordinates/text, no AI reasoning inside.

### 4. Refactor Mobile Tools: `src/tools/mobile/`
Split `src/tools/mobile_use.py` into atomic modules:
-   `src/tools/mobile/__init__.py`: Exports tool list `MOBILE_TOOLS`.
-   `src/tools/mobile/screenshot.py`: `mobile_screenshot` and capture logic.
-   `src/tools/mobile/touch.py`: `mobile_tap`, `mobile_swipe`.
-   `src/tools/mobile/keyboard.py`: `mobile_type`.
-   `src/tools/mobile/system.py`: `mobile_home`, `mobile_back`, `mobile_connect`, `mobile_devices`.
-   **Change**: Pure execution, no internal loop.

### 5. Handoff Tool: `src/tools/handoff/`
-   `src/tools/handoff/vision.py`:
    -   Tool `activate_vision_agent(task, mode)`.
    -   Imports `VisionAgent` from `src/agents/vision/`.

### 6. Update Engine: `src/gnx_engine/engine.py`
-   Register new tool imports from `src/tools/desktop/`, `src/tools/mobile/`, `src/tools/handoff/`.
-   Remove old file references.

## Implementation Steps

1.  **Create Directories**: Set up the new folder structure.
2.  **Migrate Vision Client**: Move `vl_provider` logic to `src/vision_client/`.
3.  **Refactor Desktop Tools**: specific files for mouse/keyboard/screen.
4.  **Refactor Mobile Tools**: specific files for touch/keyboard/system.
5.  **Build Vision Agent**: Implement `src/agents/vision/` using `src/vision_client`.
6.  **Create Handoff**: Connect Main Agent to Vision Agent.
7.  **Integration**: Update `engine.py` to use new paths.
8.  **Cleanup**: Delete old `vl_provider.py`, `computer_use.py`, `mobile_use.py`.