# GNX Tool Testing Guide

Test each tool individually by using these prompts in the GNX CLI.

## 1. **ls** - List directory contents
```
List all files in the current directory
```
or
```
Show me what's in the src folder
```
Expected: Shows files and folders in specified directory.

---

## 2. **read_file** - Read file contents
```
Read the contents of main.py
```
or
```
Show me the code in requirements.txt
```
Expected: Displays the content of the specified file.

---

## 3. **write_file** - Create/write to a file
```
Create a new file called test_file.txt with the content "Hello World from GNX"
```
Expected: Creates test_file.txt with specified content.

---

## 4. **edit_file** - Edit existing file
```
Edit test_file.txt and replace "Hello World" with "Updated Content"
```
Expected: Modifies test_file.txt with the replacement.

---

## 5. **glob** - Find files by pattern
```
Find all Python files in this project
```
Expected: Lists all .py files.

---

## 6. **grep** - Search text in files
```
Search for the word "import" in all Python files
```
Expected: Shows all lines containing "import" in .py files.

---

## 7. **capture_screen** - Take a screenshot
```
Take a screenshot of the current desktop
```
Expected: Captures and saves a screenshot.

---

## 8. **write_todos** - Create TODO list
```
Create a TODO list with: Test ls tool, Test read_file tool, Test write_file tool
```
Expected: Creates a TODO list with the items.

---

## 9. **read_todos** - Read TODO list
```
Show me the current TODO list
```
Expected: Displays all pending TODO items.

---

## 10. **mark_complete** - Mark TODO as done
```
Mark the first TODO item as complete
```
Expected: Marks item as completed in the TODO list.

---

## 11. **web_search** - Quick web search
```
Search the web for latest Python 3.13 features
```
or
```
What is LangChain and how does it work?
```
Expected: Returns a summary of search results from DuckDuckGo.

---

## 12. **web_search_detailed** - Detailed web search with URLs
```
Search for top AI news today and give me the links
```
or
```
Find detailed information about React 19 new features
```
Expected: Returns detailed results with URLs, titles, and snippets.

---

## Notes
- All file paths are relative to the workspace root
- Check app0.log for detailed execution logs
- The ReAct adapter handles tool execution automatically

---

# Computer Use & Mobile Use Tools

## Enabling the Tools

To use computer/desktop or mobile control tools, start GNX with flags:

```bash
# Enable computer use only
python main.py --computer-use
python main.py -c

# Enable mobile use only
python main.py --mobile-use
python main.py -m

# Enable all tools
python main.py --all-tools
python main.py -a
```

---

## Computer Use Tools

### **computer_screenshot** - Capture desktop screenshot
```
Take a screenshot of my desktop
```
Expected: Captures current screen state, saves to desktop_screenshot.png

### **computer_control** - Vision-based computer control
```
Click on the Start button
```
```
Open calculator by clicking on it
```
```
Click on the Chrome icon
```
Expected: Uses V_action vision model to identify and click UI elements.

### **computer_type_text** - Type text
```
Type "hello world" 
```
Expected: Types text at current cursor position.

### **computer_hotkey** - Press keyboard shortcuts
```
Press ctrl+c
```
```
Press alt+tab
```
Expected: Executes the keyboard shortcut.

### **computer_wait** - Wait for UI
```
Wait 3 seconds
```
Expected: Pauses execution for specified time.

---

## Mobile Use Tools (Requires ADB)

### **mobile_devices** - List connected devices
```
List connected Android devices
```
Expected: Shows all devices connected via ADB.

### **mobile_connect** - Connect to device
```
Connect to my phone
```
Expected: Connects to first available or specified device.

### **mobile_screenshot** - Capture phone screen
```
Take a screenshot of my phone
```
Expected: Captures phone screen via ADB.

### **mobile_control** - Vision-based mobile control
```
Tap on the Settings app
```
```
Open WhatsApp
```
```
Tap on the search bar
```
Expected: Uses V_action to identify and tap UI elements.

### **mobile_type_text** - Type on phone
```
Type "hello" on my phone
```
Expected: Types text on the mobile device.

### **mobile_swipe** - Swipe gestures
```
Swipe up to scroll
```
```
Swipe down
```
Expected: Performs swipe gesture.

### **mobile_button** - Press system buttons
```
Press the back button
```
```
Press home
```
Expected: Presses specified system button.

---

## Example Workflows

### Open Calculator on Desktop
```
1. Take a screenshot of the desktop
2. Click on the Start button
3. Type "calculator"
4. Click on Calculator app
```

### Open Settings on Phone
```
1. List connected devices
2. Connect to my phone
3. Take a screenshot
4. Tap on Settings icon
```
