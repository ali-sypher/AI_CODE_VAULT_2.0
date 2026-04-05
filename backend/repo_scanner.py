import os
import ast
import shutil
from git import Repo

def clone_repo(repo_url, target_dir="./data/repos"):
    # Detect Streamlit Cloud to circumvent read-only directory policies
    is_cloud = os.path.exists("/mount/src") or os.environ.get("STREAMLIT_SERVER_PORT") or os.environ.get("STREAMLIT_RUNTIME_ENV")
    
    try:
        is_writable = os.access(".", os.W_OK)
    except Exception:
        is_writable = False
        
    if is_cloud or not is_writable:
        target_dir = "/tmp/repos"
        
    # Use a stable hash of the URL to avoid path collisions and ensure consistency
    import hashlib
    repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:12]
    repo_path = os.path.abspath(os.path.join(target_dir, f"repo_{repo_hash}"))
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    if os.path.exists(repo_path):
        # Clean up existing dir for a fresh clone
        shutil.rmtree(repo_path, ignore_errors=True)
    
    print(f"Cloning {repo_url} into {repo_path}...")
    import subprocess
    
    # 1. Force Headless Git: Disable interactive prompts for credentials (prevents "hang" at 0%)
    git_env = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    git_env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

    try:
        # Using subprocess with depth=1 and fixed environment
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, repo_path],
            env=git_env,
            check=True,
            timeout=120,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except subprocess.TimeoutExpired:
        raise Exception("Git Clone Interrupted: Operation timed out after 120s. Repository may be too large or the network is throttled.")
    except subprocess.CalledProcessError as e:
        # Capture precise error from the git terminal (e.g., Repository Not Found)
        err = e.stderr.decode() if e.stderr else "Unknown Git error"
        if "Authentication failed" in err or "not found" in err.lower():
            raise Exception(f"Git Access Denied: {err.strip()}")
        raise Exception(f"Git Error: {err.strip()}")
    except Exception as e:
        raise Exception(f"Repository Ingestion Engine Error: {str(e)}")
    
    return repo_path

def scan_files(repo_path, extensions=['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.md', '.json', '.sql']):
    filepaths = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepaths.append(os.path.join(root, file))
    return filepaths

def extract_text_chunks_generic(filepath, chunk_size=1500, overlap=200):
    """
    Fallback chunking for non-Python files that don't support AST.
    Uses sliding window text chunking.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
            
        chunks = []
        # Basic chunking by character count with overlap
        for i in range(0, len(source), chunk_size - overlap):
            snippet = source[i:i + chunk_size]
            chunks.append({
                "name": f"{os.path.basename(filepath)}#chunk{len(chunks)}",
                "type": "code_snippet",
                "code": snippet,
                "file_path": filepath
            })
        return chunks
    except Exception as e:
        print(f"Failed to chunk {filepath}: {e}")
        return []

def extract_functions_via_ast(filepath):
    """
    Parses a python file with AST and extracts functions/classes
    to reduce the token payload to the LLM.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
            
        tree = ast.parse(source)
        chunks = []
        
        # Super simplified ast chunking
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                chunks.append({
                    "name": node.name,
                    "type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "code": ast.get_source_segment(source, node),
                    "file_path": filepath
                })
        # If no AST chunks found but file has content, fallback to generic
        if not chunks and len(source) > 50:
            return extract_text_chunks_generic(filepath)
            
        return chunks
    except Exception as e:
        # If AST fails (e.g. syntax error), fallback to generic
        return extract_text_chunks_generic(filepath)

def get_repo_chunks(repo_url):
    repo_path = clone_repo(repo_url)
    files = scan_files(repo_path)
    
    all_chunks = []
    for f in files:
        if f.endswith('.py'):
            all_chunks.extend(extract_functions_via_ast(f))
        else:
            all_chunks.extend(extract_text_chunks_generic(f))
    
    return all_chunks
