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
        
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_path = os.path.abspath(os.path.join(target_dir, repo_name))
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    if os.path.exists(repo_path):
        # Clean up existing dir for a fresh clone
        shutil.rmtree(repo_path, ignore_errors=True)
    
    print(f"Cloning {repo_url} into {repo_path}...")
    Repo.clone_from(repo_url, repo_path)
    return repo_path

def scan_files(repo_path, ext=".py"):
    filepaths = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(ext):
                filepaths.append(os.path.join(root, file))
    return filepaths

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
        return chunks
    except Exception as e:
        print(f"Failed to parse AST for {filepath}: {e}")
        return []

def get_repo_chunks(repo_url):
    repo_path = clone_repo(repo_url)
    files = scan_files(repo_path)
    
    all_chunks = []
    for f in files:
        all_chunks.extend(extract_functions_via_ast(f))
    
    return all_chunks
