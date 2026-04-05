import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    role = Column(String(50), default='User') # 'User' or 'Admin'
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

def get_engine():
    # SQLite default for easy local testing, but supports MySQL
    db_url = os.getenv("DATABASE_URL", "sqlite:///./code_vault.db")
    return create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})

def run_migrations(db_url):
    """Raw, aggressive migration to ensure columns exist and prevent OperationalError"""
    if not db_url.startswith("sqlite:///"):
        return
    db_path = db_url.split("sqlite:///")[-1]
    if not os.path.exists(db_path):
        return
        
    import sqlite3
    try:
        # Give a generous timeout to acquire locks
        conn = sqlite3.connect(db_path, timeout=10.0)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = [row[1] for row in cur.fetchall()]
        
        if cols and 'scan_status' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN scan_status VARCHAR(255) DEFAULT ''")
        if cols and 'scan_progress' not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN scan_progress INTEGER DEFAULT 0")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print("CRITICAL: Migration failed ->", e)

def init_db():
    engine = get_engine()
    db_url = os.getenv("DATABASE_URL", "sqlite:///./code_vault.db")
    run_migrations(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

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
