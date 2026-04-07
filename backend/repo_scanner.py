import os
import ast
import shutil
from git import Repo
import logging

def _log_debug(msg):
    """Bypasses DB logging to write to a raw system file for emergency troubleshooting."""
    log_file = "/tmp/vault_v6_debug.log"
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [INGEST_TELEMETRY] {msg}\n"
    try:
        with open(log_file, "a") as f:
            f.write(formatted)
        print(formatted.strip())
    except:
        pass

def clone_repo(repo_url, target_dir="./data/repos"):
    _log_debug(f"START: clone_repo initiated for target: {repo_url}")
    # Normalize path
    repo_url = repo_url.strip().strip('"').strip("'")
    
    # 1. ENVIRONMENT HEALTH CHECK
    git_bin = shutil.which('git')
    if not git_bin:
        _log_debug("CRITICAL: 'git' binary not found in system PATH!")
        raise Exception("System Error: Git is not installed or not in PATH.")
    else:
        _log_debug(f"INFRA: Git identified at {git_bin}")

    is_cloud = os.path.exists("/mount/src") or os.environ.get("STREAMLIT_SERVER_PORT") or os.environ.get("STREAMLIT_RUNTIME_ENV")
    if is_cloud or not os.access(".", os.W_OK):
        target_dir = "/tmp/repos"
        _log_debug(f"INFRA: Cloud/Restricted env detected. Using storage: {target_dir}")
        
    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
            _log_debug(f"INFRA: Created storage directory: {target_dir}")
        except Exception as e:
            _log_debug(f"CRITICAL: Failed to create storage dir: {e}")
            raise e

    # Write-Access Probe
    try:
        probe_file = os.path.join(target_dir, "probe.tmp")
        with open(probe_file, 'w') as f: f.write('1')
        os.remove(probe_file)
        _log_debug("INFRA: Write access verified for target_dir.")
    except Exception as e:
        _log_debug(f"CRITICAL: target_dir is NOT writable: {e}")
        raise e

    # 2. LOCAL DIR SHORT-CIRCUIT
    if os.path.isdir(repo_url):
        abs_path = os.path.abspath(repo_url)
        _log_debug(f"INGEST: Identified local directory ingestion: {abs_path}")
        return abs_path

    # 3. REMOTE CLONE LOGIC
    import hashlib
    repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:12]
    repo_path = os.path.abspath(os.path.join(target_dir, f"repo_{repo_hash}"))
    _log_debug(f"INGEST: Target repo path hashed to: {repo_path}")
    
    if os.path.exists(repo_path):
        try:
            _log_debug(f"DELTA: Repository exists. Initiating git pull...")
            repo = Repo(repo_path)
            repo.remotes.origin.pull()
            _log_debug("DELTA: Pull successful.")
            return repo_path
        except Exception as e:
            _log_debug(f"DELTA_FAIL: Failed to pull ({e}). Wiping and re-cloning...")
            shutil.rmtree(repo_path, ignore_errors=True)
    
    _log_debug(f"CLONE: Cloning remote {repo_url}...")
    import subprocess
    
    git_env = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    git_env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, repo_path],
            env=git_env,
            check=True,
            timeout=120,
            capture_output=True,
            text=True
        )
        _log_debug("CLONE: Git clone command finished successfully.")
        return repo_path
    except subprocess.CalledProcessError as e:
        err = e.stderr if e.stderr else "Unknown Git error"
        _log_debug(f"CRITICAL: Git Clone Failed: {err.strip()}")
        raise Exception(f"Git Error: {err.strip()}")
    except Exception as e:
        _log_debug(f"CRITICAL: Unexpected clone failure: {e}")
        raise e
        raise Exception(f"Ingestion Engine Error: {str(e)}")
    
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
    Parses a python file with AST and extracts functions/classes.
    FALLBACK: If not a python file, uses sliding-window.
    """
    if not filepath.endswith('.py'):
        return extract_text_chunks_generic(filepath)
        
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
    _log_debug(f"INGEST_CHAIN: Starting chunking chain for {repo_url}")
    try:
        repo_path = clone_repo(repo_url)
        _log_debug(f"INGEST_CHAIN: Clone phase complete. Path: {repo_path}")
        
        files = scan_files(repo_path)
        _log_debug(f"INGEST_CHAIN: Found {len(files)} files for analysis.")
        
        all_chunks = []
        for f in files:
            chunks = extract_functions_via_ast(f)
            all_chunks.extend(chunks)
        
        _log_debug(f"INGEST_CHAIN: Extraction complete. Total chunks generated: {len(all_chunks)}")
        return all_chunks
    except Exception as e:
        _log_debug(f"CRITICAL: Failed in get_repo_chunks loop: {e}")
        import traceback
        _log_debug(traceback.format_exc())
        raise e
