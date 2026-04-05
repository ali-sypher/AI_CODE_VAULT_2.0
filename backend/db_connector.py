import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(120), nullable=False)
    role = Column(String(20), default='User')
    session_token = Column(String(255), nullable=True) # New: Persistent session support
    scan_status = Column(String(255), default="")
    scan_progress = Column(Integer, default=0)

class Hub(Base):
    __tablename__ = 'hubs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    hash_key = Column(String(255), index=True) # Usually function/class/chunk name
    type = Column(String(50)) # 'function', 'class', 'chunk'
    code_snippet = Column(Text)
    file_path = Column(String(255))
    user_id = Column(Integer, ForeignKey('users.id')) 
    embedding = Column(JSON) 
    file_id = Column(Integer, ForeignKey('file_metadata.id')) # Link to specific file
    source_type = Column(String(50)) # 'git' or 'doc'

class Link(Base):
    __tablename__ = 'links'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_hash = Column(String(255), ForeignKey('hubs.hash_key'))
    target_hash = Column(String(255), ForeignKey('hubs.hash_key'))
    relationship_type = Column(String(50)) # 'calls', 'inherits', etc.

class Satellite(Base):
    __tablename__ = 'satellites'
    id = Column(Integer, primary_key=True, autoincrement=True)
    hub_hash = Column(String(255), ForeignKey('hubs.hash_key'))
    metrics = Column(JSON) # e.g. {"lines_of_code": 10, "parameters": ["a", "b"]}

class SearchHistory(Base):
    __tablename__ = 'searches'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    query = Column(String(500))
    results_json = Column(JSON)
    timestamp = Column(String(50))

class ChatMessage(Base):
    __tablename__ = 'chat_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    role = Column(String(50)) # 'user' or 'assistant'
    content = Column(Text)
    timestamp = Column(String(50))

class FileMetadata(Base):
    __tablename__ = 'file_metadata'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    filename = Column(String(255))
    file_type = Column(String(50)) # 'pdf', 'docx', 'csv', 'txt', 'py'
    size = Column(Integer) # in bytes
    upload_date = Column(String(50))

class KeyPool(Base):
    __tablename__ = 'key_pool'
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50)) # 'GROQ', 'OPENROUTER'
    key_value = Column(String(255))
    name = Column(String(100), default="Primary")
    is_active = Column(Integer, default=1) # 1=Active, 0=Disabled

def get_engine():
    import shutil
    import tempfile
    
    # 1. Authoritative Cloud & Environment Detection
    # On Streamlit Cloud, the root repo directory is almost always read-only for SQLite operations.
    is_cloud = (
        os.path.exists("/mount/src") or 
        os.environ.get("STREAMLIT_SERVER_PORT") is not None or 
        os.environ.get("STREAMLIT_RUNTIME_ENV") is not None or
        "codespaces" in os.environ.get("USER", "").lower()
    )
    
    # Authoritative Write-Test (Probe)
    test_file = "vault_write_probe.tmp"
    can_write = False
    try:
        with open(test_file, 'w') as f:
            f.write('probe')
        os.remove(test_file)
        can_write = True
    except Exception:
        can_write = False
        
    # 2. Nuclear Fallback: If it's Cloud OR it's not writable, we MUST use /tmp/.
    if is_cloud or not can_write:
        db_path = "/tmp/vault_v4.db"
        force_tmp = True
    else:
        db_path = "./vault_v4.db"
        force_tmp = False
    
    # 3. URL Construction with Cloud Overwrite:
    # We enforce exactly 4 slashes for absolute /tmp paths: sqlite:////tmp/vault_v4.db
    env_db_url = os.getenv("DATABASE_URL")
    if force_tmp:
        db_url = f"sqlite:////{db_path.lstrip('/')}"
    elif not env_db_url:
        protocol = "sqlite:////" if db_path.startswith("/") else "sqlite:///"
        db_url = f"{protocol}{db_path.lstrip('/') if db_path.startswith('/') else db_path}"
    else:
        db_url = env_db_url

    # 4. Mandatory DB Migration:
    if force_tmp and os.path.exists("./vault_v4.db") and not os.path.exists("/tmp/vault_v4.db"):
        try:
            shutil.copy2("./vault_v4.db", "/tmp/vault_v4.db")
        except Exception:
            pass
        
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    if "sqlite" in db_url:
        connect_args["timeout"] = 60 # Handle locks during background scans
        
    engine = create_engine(db_url, connect_args=connect_args)
    
    # Enable WAL mode for high-concurrency read/write
    if "sqlite" in db_url:
        from sqlalchemy import event
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
            
    return engine

def run_migrations(engine):
    """Iron-Clad Raw SQL migrations with Auto-Recovery for 'Poisoned' DBs"""
    from sqlalchemy import text
    import os
    
    db_file = str(engine.url).replace("sqlite:////", "/").replace("sqlite:///", "")
    
    try:
        with engine.begin() as conn:
            # 1. session_token (New: Persistent Auth)
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN session_token VARCHAR(255)"))
                print("VAULT_DEBUG: Migrated 'session_token'")
            except Exception: pass
                
            # 2. scan_status (Background Ops)
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN scan_status VARCHAR(255) DEFAULT ''"))
            except Exception: pass

            # 3. scan_progress (Background Ops)
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN scan_progress INTEGER DEFAULT 0"))
            except Exception: pass
            
        # --- Integrity Check: Can we actually see the column now? ---
        with engine.connect() as conn:
            conn.execute(text("SELECT session_token FROM users LIMIT 1"))
            
    except Exception as e:
        # --- NUCLEAR RESET: If the DB is 'Poisoned' and won't accept ALTER TABLE ---
        if "no such column: session_token" in str(e).lower() or "readonly" in str(e).lower():
            if os.path.exists(db_file):
                try:
                    import time
                    os.rename(db_file, f"{db_file}.bak_{int(time.time())}")
                    print(f"VAULT_DEBUG: NUCLEAR RESET - Corrupted DB renamed. Refreshing schema...")
                    # Re-create all tables
                    Base.metadata.create_all(engine)
                except Exception as reset_err:
                    print(f"VAULT_DEBUG: Nuclear reset failed: {reset_err}")
    
    # Final Table Provisioning
    try:
        Base.metadata.create_all(engine)
    except:
        pass

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    run_migrations(engine)
    return sessionmaker(bind=engine)

def bulk_insert_hubs(hubs_data):
    if not hubs_data: return
    engine = get_engine()
    df = pd.DataFrame(hubs_data)
    # Using 'append' to push to SQL directly via pandas. If duplicates exist, this might throw an error. 
    # Real-world usage requires an 'upsert' logic, but this is a V2 prototype
    try:
        df.to_sql('hubs', con=engine, if_exists='append', index=False)
    except Exception as e:
        print("Error inserting hubs:", e)

def bulk_insert_links(links_data):
    if not links_data: return
    engine = get_engine()
    df = pd.DataFrame(links_data)
    try:
        df.to_sql('links', con=engine, if_exists='append', index=False)
    except Exception as e:
        print("Error inserting links:", e)

def bulk_insert_satellites(sats_data):
    if not sats_data: return
    engine = get_engine()
    df = pd.DataFrame(sats_data)
    try:
        df.to_sql('satellites', con=engine, if_exists='append', index=False)
    except Exception as e:
        print("Error inserting satellites:", e)
