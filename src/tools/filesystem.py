import os
from langchain_core.tools import tool

@tool
def ls(path: str = ".") -> str:
    """List contents of a directory in the workspace."""
    try:
        # Resolve path against current working directory if needed
        # For CLI, let's trust users absolute or relative paths
        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."
        
        items = os.listdir(path)
        formatted = []
        for item in items:
            full_path = os.path.join(path, item)
            kind = "DIR " if os.path.isdir(full_path) else "FILE"
            formatted.append(f"{kind:4} {item}")
        return "\n".join(formatted)
    except Exception as e:
        return f"Error listing directory: {e}"
