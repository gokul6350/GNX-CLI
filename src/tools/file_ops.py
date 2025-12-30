from langchain_core.tools import tool
import os

@tool
def read_file(path: str) -> str:
    """Read the contents of a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file (creates if doesn't exist)."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def edit_file(path: str, old_content: str, new_content: str) -> str:
    """Edit a file by replacing specific content."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        if old_content not in data:
            return "Error: Content to replace not found in file."
            
        new_data = data.replace(old_content, new_content)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_data)
        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error editing file: {e}"
