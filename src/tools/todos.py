from langchain_core.tools import tool
import os
import json

TODO_FILE = "todos.json"

@tool
def write_todos(todos: str) -> str:
    """Create a TODO list. Input should be a JSON string or newline separated list."""
    # Reset/Overwrite todos
    todo_list = []
    try:
        # Try parsing as JSON first
        data = json.loads(todos)
        if isinstance(data, list):
            todo_list = [{"task": t, "completed": False} if isinstance(t, str) else t for t in data]
        else:
             # Fallback to splitting lines
            lines = todos.strip().split('\n')
            todo_list = [{"task": line.strip(), "completed": False} for line in lines if line.strip()]
    except:
        lines = todos.strip().split('\n')
        todo_list = [{"task": line.strip(), "completed": False} for line in lines if line.strip()]

    try:
        with open(TODO_FILE, 'w') as f:
            json.dump(todo_list, f, indent=2)
        return "TODO list created."
    except Exception as e:
        return f"Error writing todos: {e}"

@tool
def read_todos() -> str:
    """Read the current TODO list."""
    if not os.path.exists(TODO_FILE):
        return "No TODO list found."
    try:
        with open(TODO_FILE, 'r') as f:
            todo_list = json.load(f)
        
        output = []
        for i, item in enumerate(todo_list):
            status = "[x]" if item.get("completed") else "[ ]"
            output.append(f"{i}. {status} {item.get('task')}")
        return "\n".join(output)
    except Exception as e:
        return f"Error reading todos: {e}"

@tool
def mark_complete(index: int) -> str:
    """Mark a TODO item as complete by index."""
    if not os.path.exists(TODO_FILE):
        return "No TODO list found."
    try:
        with open(TODO_FILE, 'r') as f:
            todo_list = json.load(f)
        
        if 0 <= index < len(todo_list):
            todo_list[index]['completed'] = True
            with open(TODO_FILE, 'w') as f:
                json.dump(todo_list, f, indent=2)
            return f"Marked item {index} as complete."
        else:
            return "Index out of range."
    except Exception as e:
        return f"Error marking complete: {e}"
