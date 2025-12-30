# GNX Tool Testing Guide

Test each tool individually by using these prompts in the GNX CLI.

## 1. **ls** - List directory contents
```
GNX: List all files in the current directory
```
Expected: Shows files and folders in current workspace directory.

---

## 2. **read_file** - Read file contents
```
GNX: Read the contents of main.py
```
Expected: Displays the content of main.py file.

---

## 3. **write_file** - Create/write to a file
```
GNX: Create a new file called test_file.txt with the content "Hello World from GNX"
```
Expected: Creates test_file.txt with specified content.

---

## 4. **edit_file** - Edit existing file
```
GNX: Edit test_file.txt and replace "Hello World" with "Updated Content"
```
Expected: Modifies test_file.txt with the replacement.

---

## 5. **glob** - Find files by pattern
```
GNX: Find all Python files (*.py) in the src directory
```
Expected: Lists all .py files in src folder.

---

## 6. **grep** - Search text in files
```
GNX: Search for the text "import" in all Python files in the src directory
```
Expected: Shows all lines containing "import" in .py files.

---

## 7. **capture_screen** - Take a screenshot
```
GNX: Take a screenshot of the current desktop
```
Expected: Captures and saves a screenshot.

---

## 8. **write_todos** - Create TODO list
```
GNX: Create a TODO list with these items:
1. Test the ls tool
2. Test the read_file tool
3. Test the write_file tool
4. Test the edit_file tool
```
Expected: Creates a TODO list with 4 items.

---

## 9. **read_todos** - Read TODO list
```
GNX: Show me the current TODO list
```
Expected: Displays all pending TODO items.

---

## 10. **mark_complete** - Mark TODO as done
```
GNX: Mark the first TODO item as complete
```
Expected: Marks item 1 as completed in the TODO list.

---

## Testing Strategy

Run these prompts sequentially to verify each tool works correctly:

1. Start with simple tools (ls, read_file)
2. Test file creation (write_file)
3. Test file modification (edit_file)
4. Test search tools (glob, grep)
5. Test system tools (capture_screen)
6. Test TODO management (write_todos, read_todos, mark_complete)

## Notes
- All file paths should be relative to the workspace root
- Some tools may require specific directory context
- Check app0.log for detailed execution logs
