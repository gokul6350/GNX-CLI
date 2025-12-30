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

## Notes
- All file paths are relative to the workspace root
- Check app0.log for detailed execution logs
- The ReAct adapter handles tool execution automatically
