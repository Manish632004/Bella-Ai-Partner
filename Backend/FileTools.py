import os
import fnmatch
from Backend.Chatbot import client

def resolve_path(path_str):
    """
    Resolve shorthand paths like 'user', 'desktop', 'documents', 'downloads' to actual paths.
    """
    if not path_str or path_str == ".":
        return "."
    path_lower = path_str.lower().strip()
    if path_lower in ("user", "home"):
        return os.path.expanduser("~")
    elif path_lower == "desktop":
        return os.path.join(os.path.expanduser("~"), "Desktop")
    elif path_lower == "documents":
        return os.path.join(os.path.expanduser("~"), "Documents")
    elif path_lower == "downloads":
        return os.path.join(os.path.expanduser("~"), "Downloads")
    elif path_lower in ("project", "workspace", "here"):
        return "."
    
    # If it's a drive like D: or D:\, normalize it
    if len(path_str) == 2 and path_str[1] == ":":
        return path_str + "\\"
        
    return path_str

def find_file(name, search_path=None):
    """
    Search the filesystem for files and folders matching a name/pattern.
    Returns a list of matching full absolute paths prefixed with [FILE] or [DIR].
    """
    if not search_path:
        search_path = "."
        
    search_path = resolve_path(search_path)
    if not os.path.isdir(search_path):
        project_path = os.path.join(".", search_path)
        if os.path.isdir(project_path):
            search_path = project_path
        else:
            search_path = "."
            
    has_wildcards = "*" in name or "?" in name
    if not has_wildcards:
        words = name.lower().split()
    else:
        pattern = name.lower()
        
    matches = []
    
    # Exclude directories that are massive, system, or library dependency folders
    exclude_dirs = {
        "node_modules", "__pycache__", ".venv", "venv", ".git", ".idea", ".vscode",
        "system volume information", "$recycle.bin", "appdata", "program files",
        "program files (x86)", "windows", "msocache", "recovery"
    }
    
    try:
        for root, dirnames, filenames in os.walk(search_path):
            # Prune directories so walk doesn't recurse into them
            pruned_dirnames = []
            for d in dirnames:
                if d.startswith(".") or d.lower() in exclude_dirs:
                    continue
                pruned_dirnames.append(d)
                
            # Match directories
            for dirname in pruned_dirnames:
                matched = False
                if has_wildcards:
                    if fnmatch.fnmatch(dirname.lower(), pattern):
                        matched = True
                else:
                    if all(word in dirname.lower() for word in words):
                        matched = True
                if matched:
                    full_path = os.path.abspath(os.path.join(root, dirname))
                    matches.append(f"[DIR] {full_path}")
                    if len(matches) >= 50:
                        matches.append("... (Too many matches, truncated to first 50 results)")
                        return matches
                        
            # Keep dirnames updated for os.walk recursion
            dirnames[:] = pruned_dirnames
            
            # Match files
            for filename in filenames:
                matched = False
                if has_wildcards:
                    if fnmatch.fnmatch(filename.lower(), pattern):
                        matched = True
                else:
                    if all(word in filename.lower() for word in words):
                        matched = True
                        
                if matched:
                    full_path = os.path.abspath(os.path.join(root, filename))
                    matches.append(f"[FILE] {full_path}")
                    if len(matches) >= 50:
                        matches.append("... (Too many matches, truncated to first 50 results)")
                        return matches
    except Exception as e:
        return [f"Error searching path '{search_path}': {e}"]
        
    return matches

def read_file(path):
    """
    Read and return file contents as a string. Handles UTF-8 and falls back to Latin-1.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file (decoding failed): {e}"
    except Exception as e:
        return f"Error reading file: {e}"

def list_directory(path=None):
    """
    List contents of a directory, distinguishing between files and folders.
    """
    if not path:
        path = "."
    try:
        items = os.listdir(path)
        dirs = []
        files = []
        for item in items:
            # Skip hidden items by default
            if item.startswith("."):
                continue
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                dirs.append(item)
            else:
                files.append(item)
        
        result = f"Contents of directory '{os.path.abspath(path)}':\n"
        if dirs:
            result += "Directories:\n" + "\n".join([f"  - [DIR] {d}" for d in sorted(dirs)]) + "\n"
        if files:
            result += "Files:\n" + "\n".join([f"  - [FILE] {f}" for f in sorted(files)]) + "\n"
        if not dirs and not files:
            result += "  (Empty directory)\n"
        return result.strip()
    except Exception as e:
        return f"Error listing directory: {e}"

def debug_code(file_path, error_message=None):
    """
    Read the specified code file and use the Groq client to diagnose the bug and suggest a fix.
    """
    code = read_file(file_path)
    if code.startswith("Error reading file"):
        return code

    system_prompt = (
        "You are an expert software engineer specializing in code review, troubleshooting, and debugging. "
        "Your task is to analyze the provided code, find any bugs or syntax/logic errors, and suggest corrections. "
        "Return the suggested fix clearly formatted as a markdown code block along with a concise explanation."
    )
    
    user_prompt = f"File: {file_path}\n\nCode:\n```\n{code}\n```"
    if error_message:
        user_prompt += f"\n\nError Message / Context:\n{error_message}"

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2048
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error calling debug API: {e}"
