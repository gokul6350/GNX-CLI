from langchain_core.tools import tool
import glob as glob_module
import os

@tool
def glob(pattern: str) -> str:
    """Find files matching a pattern (e.g., **/*.py)."""
    try:
        files = glob_module.glob(pattern, recursive=True)
        return "\n".join(files)
    except Exception as e:
        return f"Error in glob: {e}"

@tool
def grep(pattern: str, file_pattern: str = "**/*") -> str:
    """Search for text/pattern in files."""
    results = []
    try:
        files = glob_module.glob(file_pattern, recursive=True)
        for filepath in files:
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if pattern in line:
                                results.append(f"{filepath}:{i+1}: {line.strip()}")
                except:
                    # Ignore binary files or read errors
                    continue
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error in grep: {e}"
