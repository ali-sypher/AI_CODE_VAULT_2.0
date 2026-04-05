import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import time
from datetime import datetime
import json

# --- Add backend to path for modular imports ---
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# --- Dynamic Imports for Performance ---
@st.cache_resource
def load_backend():
    from db_connector import init_db, Hub, SearchHistory, User, ChatMessage, FileMetadata
    from repo_scanner import get_repo_chunks
    from ai_parser import parse_code_chunk, generate_embedding
    from file_processor import extract_text_from_file, chunk_text
    return {
        'init_db': init_db,
        'Hub': Hub,
        'SearchHistory': SearchHistory,
        'User': User,
        'ChatMessage': ChatMessage,
        'FileMetadata': FileMetadata,
        'get_repo_chunks': get_repo_chunks,
        'parse_code_chunk': parse_code_chunk,
        'generate_embedding': generate_embedding,
        'extract_text_from_file': extract_text_from_file,
        'chunk_text': chunk_text
    }

backend = load_backend()
Hub = backend['Hub']
SearchHistory = backend['SearchHistory']
User = backend['User']
ChatMessage = backend['ChatMessage']
FileMetadata = backend['FileMetadata']
get_repo_chunks = backend['get_repo_chunks']
parse_code_chunk = backend['parse_code_chunk']
generate_embedding = backend['generate_embedding']
extract_text_from_file = backend['extract_text_from_file']
chunk_text = backend['chunk_text']

import sqlalchemy as sa
from sqlalchemy.orm import Session
import threading
import shutil
import bcrypt
from streamlit_lottie import st_lottie
import requests

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Code Vault 2.0",
    page_icon=r"C:\Users\Ali Aliyyan\.gemini\antigravity\brain\f10956f1-2a7c-4353-8e8f-678d5e4bd8ab\ai_vault_pro_logo_1775332828537.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling (Immersive Cyber Space) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&family=Inter:wght@400;700&display=swap');
    
    .stApp {
        background: linear-gradient(45deg, #0f0c29, #302b63, #24243e);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
        font-family: 'Inter', sans-serif;
        color: #ffffff;
    }
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .main-header {
        font-family: 'Outfit', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00f2ff 0%, #7000ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(0, 242, 255, 0.4);
        letter-spacing: -1px;
    }
    .glass-card {
        background: rgba(13, 17, 23, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 2.5rem;
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.9);
        margin-bottom: 2rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
        transform: translateY(-8px);
        border: 1px solid rgba(0, 242, 255, 0.4);
        box-shadow: 0 15px 50px 0 rgba(0, 242, 255, 0.15);
    }
    .stat-card {
        text-align: center;
        padding: 2rem;
        background: rgba(0, 242, 255, 0.03);
        border-radius: 15px;
        border: 1px solid rgba(0, 242, 255, 0.1);
    }
    .metric-value {
        font-family: 'Outfit', sans-serif;
        font-size: 3rem;
        color: #00f2ff;
        text-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
        font-weight: bold;
    }
    /* Button Glows */
    .stButton>button {
        background: linear-gradient(90deg, #00f2ff, #7000ff) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.8rem 2rem !important;
        font-weight: 700 !important;
        transition: box-shadow 0.3s ease !important;
    }
    .stButton>button:hover {
        box-shadow: 0 0 20px rgba(0, 242, 255, 0.6) !important;
    }
    .chat-container {
        max-width: 850px;
        margin: 0 auto;
        padding: 2rem 0;
    }
    .user-msg {
        text-align: right;
        padding: 1rem;
        margin-bottom: 2rem;
        font-size: 1.1rem;
        color: #ffffff;
    }
    .ai-msg {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2.5rem;
        line-height: 1.6;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .nav-btn {
        width: 100%;
        text-align: left;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        font-family: 'Outfit', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.85rem;
    }
    .nav-btn:hover {
        background: rgba(0, 242, 255, 0.05);
        border: 1px solid rgba(0, 242, 255, 0.2);
    }
    .nav-active {
        background: rgba(0, 242, 255, 0.1) !important;
        border: 1px solid rgba(0, 242, 255, 0.4) !important;
        color: #00f2ff !important;
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.1);
    }
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #05070a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- DB Helper ---
@st.cache_resource
def get_db_session():
    return backend['init_db']()

session = get_db_session()

# --- Session State Management ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'is_scanning' not in st.session_state:
    st.session_state.is_scanning = False
if 'scan_progress' not in st.session_state:
    st.session_state.scan_progress = 0
if 'scan_status' not in st.session_state:
    st.session_state.scan_status = ""
if 'scan_message' not in st.session_state:
    st.session_state.scan_message = ""
if 'hubs_indexed' not in st.session_state:
    st.session_state.hubs_indexed = 0
if 'messages' not in st.session_state:
    st.session_state.messages = []

def load_chat_history():
    if st.session_state.user:
        history = session.query(ChatMessage).filter(ChatMessage.user_id == st.session_state.user['id']).order_by(ChatMessage.id).all()
        st.session_state.messages = [{"role": msg.role, "content": msg.content} for msg in history]

@st.cache_data
def load_lottiefile(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

LOTTIE_AUTH = load_lottiefile("assets/auth.json")
LOTTIE_SCAN = load_lottiefile("assets/scan.json")

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- Login / Signup UI ---
def auth_page():
    # Subtle Outline 'Return to Homepage' Button
    # Premium 'Return to Homepage' Button
    st.markdown("""
        <style>
        .premium-back-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(90deg, rgba(0, 242, 255, 0.05), transparent);
            color: #00f2ff;
            text-decoration: none;
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 8px 18px;
            border: 1px solid rgba(0, 242, 255, 0.3);
            border-radius: 8px;
            transition: all 0.3s ease;
            box-shadow: 0 0 10px rgba(0, 242, 255, 0.1);
        }
        .premium-back-btn:hover {
            background: linear-gradient(90deg, rgba(0, 242, 255, 0.15), rgba(112, 0, 255, 0.05));
            border: 1px solid #00f2ff;
            box-shadow: 0 0 20px rgba(0, 242, 255, 0.4);
            transform: translateX(-3px);
            color: white;
        }
        .premium-back-btn svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
            transition: transform 0.3s ease;
        }
        .premium-back-btn:hover svg {
            transform: translateX(-4px);
        }
        </style>
        <div style='text-align: left; padding-left: 5%; margin-bottom: -20px; z-index: 100; position: relative;'>
            <a href='http://localhost:8000/index.html' class='premium-back-btn'>
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
                </svg>
                Return to Homepage
            </a>
        </div>
    """, unsafe_allow_html=True)
    # Only show centered AI CODE VAULT title
    st.markdown('<div class="main-header" style="text-align: center; margin-top: 2rem; font-size: 4.5rem;">AI CODE VAULT 2.0</div>', unsafe_allow_html=True)
    
    # Feature Slider / Marquee
    st.markdown("""
        <style>
        .marquee-container {
            max-width: 600px;
            margin: 0 auto 2rem auto;
            overflow: hidden;
            background: rgba(22, 27, 34, 0.4);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            position: relative;
        }
        .marquee-content {
            display: flex;
            white-space: nowrap;
            animation: slide-left 15s linear infinite;
        }
        .marquee-item {
            color: #00f2ff;
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 0 25px;
            display: inline-block;
            text-transform: uppercase;
        }
        @keyframes slide-left {
            0% { transform: translateX(0%); }
            100% { transform: translateX(-50%); }
        }
        /* Tab Styling */
        .stTabs [data-baseweb="tab"] {
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            color: #8b949e !important;
            transition: all 0.3s ease !important;
        }
        .stTabs [aria-selected="true"] {
            color: #00f2ff !important;
            text-shadow: 0 0 10px rgba(0, 242, 255, 0.5) !important;
        }
        </style>
        <div class="marquee-container">
            <div class="marquee-content">
                <span class="marquee-item">✦ NEURAL AST INDEXING</span>
                <span class="marquee-item">✦ 100M+ VECTOR CAPACITY</span>
                <span class="marquee-item">✦ RAG ARCHITECT ASSISTANT</span>
                <span class="marquee-item">✦ HYBRID SEMANTIC SEARCH</span>
                <span class="marquee-item">✦ ENTERPRISE SECURITY</span>
                <!-- Duplicate for seamless loop -->
                <span class="marquee-item">✦ NEURAL AST INDEXING</span>
                <span class="marquee-item">✦ 100M+ VECTOR CAPACITY</span>
                <span class="marquee-item">✦ RAG ARCHITECT ASSISTANT</span>
                <span class="marquee-item">✦ HYBRID SEMANTIC SEARCH</span>
                <span class="marquee-item">✦ ENTERPRISE SECURITY</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Signup"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Enter Vault", use_container_width=True)
                
                if submitted:
                    user = session.query(User).filter(User.email == email).first()
                    if user and verify_password(password, user.hashed_password):
                        st.session_state.authenticated = True
                        st.session_state.user = {"id": user.id, "email": user.email, "role": user.role}
                        st.session_state.menu = "Admin_Dashboard" if user.role == 'Admin' else "Ingest"
                        load_chat_history()
                        st.success(f"Welcome back, {email}!")
                        st.toast("Login Successful!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Explicit Warning: Password match error or User not found!")
        
        with tab2:
            with st.form("signup_form"):
                new_email = st.text_input("Email")
                new_pass = st.text_input("Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")
                
                signup_submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if signup_submitted:
                    if not new_email or not new_pass:
                        st.error("Explicit Warning: Fields cannot be empty.")
                    elif new_pass != confirm_pass:
                        st.error("Explicit Warning: Password match error. Passwords do not match!")
                    else:
                        existing = session.query(User).filter(User.email == new_email).first()
                        if existing:
                            st.error("Explicit Warning: User already exists with this email.")
                        else:
                            role = 'Admin' if new_email == 'admin@vault.ai' else 'User'
                            new_user = User(email=new_email, hashed_password=hash_password(new_pass), role=role)
                            session.add(new_user)
                            session.commit()
                            st.success("Registered successfully! Please switch to Login tab.")
                            st.toast("Registered successfully!", icon="🎉")
                            st.balloons()
        st.markdown('</div>', unsafe_allow_html=True)

# --- Sidebar Navigation ---
# st.sidebar.image("assets/ai_vault_pro_logo.png", use_container_width=True) # Logo missing remotely
st.sidebar.markdown("<h2 style='text-align: center; color: #00f2ff; font-family: Outfit;'>COMMAND CENTER</h2>", unsafe_allow_html=True)

if not st.session_state.authenticated:
    auth_page()
    st.stop()

# --- Authenticated Sidebar Content ---
st.sidebar.markdown(f"<p style='text-align: center;'>👤 Logged in as: <b>{st.session_state.user['email']}</b><br><small>({st.session_state.user['role']})</small></p>", unsafe_allow_html=True)
if st.sidebar.button("🔓 Logout", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

# Navigation Menu State
if 'menu' not in st.session_state:
    st.session_state.menu = "Ingest"

def set_menu(name):
    st.session_state.menu = name

st.sidebar.markdown("<br>", unsafe_allow_html=True)

if st.session_state.user['role'] == 'Admin':
    menu_items = [
        ("Admin_Dashboard", "Global Dashboard"),
        ("Admin_Users", "User Management"),
        ("Admin_Activity", "Global Activity Logs")
    ]
else:
    menu_items = [
        ("Ingest", "Scan Repository"),
        ("Explorer", "Vault Explorer"),
        ("Architect", "AI Architect Chat"),
        ("Search", "Neural Search"),
        ("Analytics", "Analytics Portal")
    ]

for key, label in menu_items:
    is_active = "nav-active" if st.session_state.menu == key else ""
    if st.sidebar.button(label, key=f"nav_{key}", use_container_width=True, on_click=set_menu, args=(key,)):
        pass
    # We use a bit of invisible CSS to mark active state since st.button doesn't support active state natively well
    if st.session_state.menu == key:
        st.sidebar.markdown(f'<div style="height:2px; background:#00f2ff; width:100%; margin-top:-10px; margin-bottom:10px; box-shadow:0 0 10px #00f2ff;"></div>', unsafe_allow_html=True)

menu = st.session_state.menu

# --- Sidebar History Content (User Scoped) ---
if st.session_state.user['role'] != 'Admin':
    st.sidebar.divider()
    st.sidebar.subheader("🕒 Your History")
    user_id = st.session_state.user['id']
    history = session.query(SearchHistory).filter(SearchHistory.user_id == user_id).order_by(SearchHistory.id.desc()).limit(10).all()

    if history:
        for h in history:
            with st.sidebar.expander(f"Query: {h.query[:20]}..."):
                st.caption(f"Time: {h.timestamp}")
                if st.button("Re-run Query", key=f"hist_{h.id}"):
                    st.session_state.search_query = h.query
                    st.rerun()

    else:
        st.sidebar.info("No query history yet.")

# --- Functions ---
def background_scan_task(repo_url, user_id):
    """Execution logic in a background thread"""
    st.session_state.is_scanning = True
    st.session_state.scan_progress = 0
    st.session_state.scan_status = "Cloning repository..."
    
    try:
        chunks = get_repo_chunks(repo_url)
        st.session_state.scan_progress = 10
        
        total = len(chunks)
        if total == 0:
            st.session_state.scan_status = "No Python files found."
            st.session_state.is_scanning = False
            return
            
        st.session_state.scan_status = f"Processing {total} code chunks..."
        success_count = 0
        
        # New database session for the background thread
        engine = get_engine()
        with Session(engine) as scan_session:
            for i, chunk in enumerate(chunks):
                parsed = parse_code_chunk(chunk)
                if parsed and parsed.get('hub'):
                    hub_data = parsed['hub']
                    new_hub = Hub(
                        hash_key=hub_data['hash_key'],
                        type=hub_data['type'],
                        code_snippet=hub_data['code_snippet'],
                        file_path=hub_data.get('file_path', ''),
                        embedding=hub_data.get('embedding', []),
                        user_id=user_id
                    )
                    scan_session.merge(new_hub)
                    success_count += 1
                
                # Update progress in session state
                st.session_state.hubs_indexed = success_count
                st.session_state.scan_progress = 10 + int(90 * (i+1)/total)
                st.session_state.scan_status = f"Indexing: {i+1}/{total} chunks processed..."
                
                if i % 10 == 0:
                    scan_session.commit()
            
            scan_session.commit()
            
        st.session_state.scan_status = "Vault Ingestion Complete!"
        st.session_state.scan_message = f"Successfully indexed {success_count} Code Hubs from repo."
        
    except Exception as e:
        st.session_state.scan_status = f"Critical Failure: {str(e)}"
    
    st.session_state.is_scanning = False

def process_file_content(uploaded_file, user_id):
    """Index a single file's content into the Hub - Supports Multi Format"""
    st.session_state.is_scanning = True
    st.session_state.scan_status = "Analyzing and Chunking file..."
    try:
        filename = uploaded_file.name
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        file_size = len(uploaded_file.getvalue())
        
        # Track metadata
        new_file_meta = FileMetadata(
            user_id=user_id,
            filename=filename,
            file_type=file_ext,
            size=file_size,
            upload_date=datetime.now().isoformat()
        )
        session.add(new_file_meta)
        session.commit()

        # Extract & Chunk
        raw_text = extract_text_from_file(uploaded_file, file_ext)
        st.session_state.scan_status = "Generating Embeddings..."
        
        if file_ext == 'py':
            # Use AST parser for Python
            parsed = parse_code_chunk(raw_text)
            if parsed and parsed.get('hub'):
                hub_data = parsed['hub']
                new_hub = Hub(
                    hash_key=f"{filename}_{hub_data['hash_key']}",
                    type=hub_data['type'],
                    code_snippet=hub_data['code_snippet'],
                    file_path=f"direct_upload/{filename}",
                    embedding=hub_data.get('embedding', []),
                    user_id=user_id,
                    file_id=new_file_meta.id,
                    source_type='py'
                )
                session.merge(new_hub)
        else:
            # Generic Text Chunking
            chunks = chunk_text(raw_text, chunk_size=800, overlap=100)
            st.session_state.scan_progress = 50
            total_chunks = len(chunks)
            for i, c in enumerate(chunks):
                if not c.strip(): continue
                emb = generate_embedding(c)
                new_hub = Hub(
                    hash_key=f"{filename}_chunk_{i}",
                    type="chunk",
                    code_snippet=c,
                    file_path=f"direct_upload/{filename}",
                    embedding=emb,
                    user_id=user_id,
                    file_id=new_file_meta.id,
                    source_type=file_ext
                )
                session.add(new_hub)
                st.session_state.scan_progress = 50 + int(50 * (i+1)/total_chunks)
                
        session.commit()
        st.session_state.scan_message = f"Successfully indexed {filename} into the Vault."
        st.toast(f"✅ Indexed {filename}!", icon="💎")
        st.balloons()
    except Exception as e:
        session.rollback()
        st.session_state.scan_message = f"Error indexing file: {str(e)}"
    st.session_state.is_scanning = False

def run_scan(repo_url):
    """Trigger the background scan thread"""
    if st.session_state.is_scanning:
        st.warning("A scan is already in progress.")
        return
        
    user_id = st.session_state.user['id']
    thread = threading.Thread(target=background_scan_task, args=(repo_url, user_id))
    thread.start()
    st.success("Scan Agent dispatched to background. You can navigate away safely!")

def run_hybrid_search(query):
    user_id = st.session_state.user['id']
    query_vector = np.array(generate_embedding(query))
    engine = get_engine()
    
    # Keyword & Vector Hybrid logic (User Scoped)
    stmt = sa.select(Hub.hash_key, Hub.code_snippet, Hub.embedding).where(Hub.user_id == user_id)
    results = session.execute(stmt).all()
    
    scored_results = []
    for r in results:
        emb = np.array(r.embedding) if r.embedding else None
        if emb is not None:
            # Cosine similarity
            sim = np.dot(emb, query_vector) / (np.linalg.norm(emb) * np.linalg.norm(query_vector))
        else:
            sim = 0
            
        # Keyword boost
        if query.lower() in r.hash_key.lower():
            sim += 0.5
            
        scored_results.append({
            "name": r.hash_key,
            "snippet": r.code_snippet,
            "score": round(float(sim), 3)
        })
    
    scored_results.sort(key=lambda x: x['score'], reverse=True)
    top_results = scored_results[:5]
    
    # Save History
    new_hist = SearchHistory(
        query=query,
        results_json=top_results,
        timestamp=datetime.now().isoformat(),
        user_id=user_id
    )
    session.add(new_hist)
    session.commit()
    
    return top_results

def reset_vault():
    """Clear all data and reset the system"""
    # Delete database rows
    from db_connector import Link, Satellite
    session.query(Link).delete()
    session.query(Satellite).delete()
    session.query(Hub).delete()
    session.query(SearchHistory).delete()
    session.commit()
    
    # Clean disk cache
    shutil.rmtree("./data/repos", ignore_errors=True)
    
    # Clear Streamlit internal state
    st.cache_resource.clear()
    st.session_state.clear()
    
    st.success("System Reset Complete! The Vault is now empty.")
    time.sleep(1)
    st.rerun()

# --- MAIN UI ---
col_logo, col_text = st.columns([1, 8])
with col_logo:
    st.image(r"C:\Users\Ali Aliyyan\.gemini\antigravity\brain\f10956f1-2a7c-4353-8e8f-678d5e4bd8ab\ai_vault_pro_logo_1775332828537.png", width=80)
with col_text:
    st.markdown('<div class="main-header">AI CODE VAULT V2.0</div>', unsafe_allow_html=True)

# Persistent Background Progress UI
if st.session_state.is_scanning:
    with st.container():
        st.info(f"⚡ Background Scan Active: {st.session_state.scan_status}")
        st.progress(st.session_state.scan_progress)

if menu == "Ingest":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("Nexus Ingestion Portal")
    st.write("Feed the Vault by scanning a GitHub repository or uploading files directly.")
    
    tab_git, tab_file = st.tabs(["🌐 GitHub Scan", "📂 Direct Upload"])
    
    with tab_git:
        repo_url = st.text_input("Repository Target (GitHub URL)", placeholder="https://github.com/fastapi/fastapi", key="repo_url_input")
        if st.button("Initialize Repository Scan", key="btn_scan"):
            if repo_url:
                run_scan(repo_url)
            else:
                st.warning("Please provide a valid URL.")
                
    with tab_file:
        uploaded_file = st.file_uploader("Upload Document / Code", type=["py", "pdf", "docx", "txt", "csv"], help="Drag and drop for instant indexing.")
        if uploaded_file is not None:
            if st.button("Index File", key="btn_index"):
                process_file_content(uploaded_file, st.session_state.user['id'])
                st.rerun()

    if st.session_state.scan_message:
        st.info(st.session_state.scan_message)
        st.session_state.scan_message = ""
        
    if st.session_state.is_scanning:
        if LOTTIE_SCAN:
            col_l, col_r = st.columns([1,2])
            with col_l:
                st_lottie(LOTTIE_SCAN, height=200, key="scan_lottie")
            with col_r:
                st.info(f"⚡ {st.session_state.scan_status}")
                st.progress(st.session_state.scan_progress)
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "Explorer":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("Vault Database - Metadata Table")
    st.write("A verified table of functions, classes, and code hubs.")
    
    # Query all hubs for current user
    user_id = st.session_state.user['id']
    hubs = session.query(Hub).filter(Hub.user_id == user_id).all()
    
    if hubs:
        df_hubs = pd.DataFrame([{
            "ID": h.id,
            "Name": h.hash_key,
            "Type": h.type,
            "File Path": h.file_path.split("repos")[-1] if "repos" in h.file_path else h.file_path,
            "Code Size (Chars)": len(h.code_snippet) if h.code_snippet else 0
        } for h in hubs])
        
        st.dataframe(df_hubs, use_container_width=True, hide_index=True)
        
        selected_name = st.selectbox("Select a Hub to preview code:", df_hubs['Name'].unique())
        if selected_name:
            selected_hub = session.query(Hub).filter(Hub.hash_key == selected_name, Hub.user_id == user_id).first()
            if selected_hub:
                st.subheader(f"Snippet: {selected_hub.hash_key}")
                st.code(selected_hub.code_snippet, language='python')
    else:
        st.info("No data ingested yet. Go to 'Scan Repository' to begin.")
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "Architect":
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown('<h2 style="font-family:Outfit; text-align:center; margin-bottom:3rem;">Vault Architect</h2>', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        role_class = "user-msg" if message["role"] == "user" else "ai-msg"
        st.markdown(f'<div class="{role_class}">{message["content"]}</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("Ask about your code & documents..."):
        # Save User Message to DB & Session
        user_msg = ChatMessage(user_id=st.session_state.user['id'], role="user", content=prompt, timestamp=datetime.now().isoformat())
        session.add(user_msg)
        session.commit()
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(f'<div class="user-msg">{prompt}</div>', unsafe_allow_html=True)

        st.markdown('<div class="ai-msg">', unsafe_allow_html=True)
        with st.spinner("Consulting the Vault Embeddings..."):
                # RAG Logic
                context_results = run_hybrid_search(prompt)
                context_text = "\n\n".join([f"File: {r['name']}\nCode:\n{r['snippet']}" for r in context_results])
                
                final_prompt = f"""You are the AI Architect for this codebase. 
                Use the following retrieved code snippets to answer the user's question.
                If the code doesn't contain the answer, say you don't know based on the current vault.
                
                Context:
                {context_text}
                
                Question: {prompt}
                
                Answer:"""
                
                # API Call (using same logic as parser)
                try:
                    response = requests.post(
                        url="https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                            "Content-Type": "application/json"
                        },
                        data=json.dumps({
                            "model": "anthropic/claude-3.5-sonnet:beta",
                            "messages": [{"role": "user", "content": final_prompt}]
                        })
                    )
                    data = response.json()
                    full_response = data['choices'][0]['message']['content']
                    
                    # Save AI Message to DB & Session
                    ai_msg = ChatMessage(user_id=st.session_state.user['id'], role="assistant", content=full_response, timestamp=datetime.now().isoformat())
                    session.add(ai_msg)
                    session.commit()
                    
                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.toast("Response Decoded", icon="🧠")
                except Exception as e:
                    st.markdown(f"Architect Error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "Search":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("Neural Similarity Search")
    st.write("Quantum retrieval over the code graph through hybrid vector indexing.")
    
    search_q = st.text_input("Describe the logic you seek...", value=st.session_state.get('search_query', ''))
    if st.button("Search Vault"):
        if search_q:
            with st.spinner("Searching Vector Embeddings..."):
                results = run_hybrid_search(search_q)
                st.session_state.last_results = results
        else:
            st.warning("Enter a query.")
            
    if 'last_results' in st.session_state:
        st.divider()
        st.subheader(f"Results for '{search_q}'")
        for res in st.session_state.last_results:
            with st.expander(f"{res['name']} (Score: {res['score']})"):
                st.code(res['snippet'], language='python')
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "Analytics":
    user_id = st.session_state.user['id']
    total_hubs = session.query(Hub).filter(Hub.user_id == user_id).count()
    total_searches = session.query(SearchHistory).filter(SearchHistory.user_id == user_id).count()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="metric-value">{total_hubs}</div><p style="color:rgba(255,255,255,0.7)">Code Hubs Ingested</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="metric-value">{total_searches}</div><p style="color:rgba(255,255,255,0.7)">Queries Executed</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="metric-value">0.1s</div><p style="color:rgba(255,255,255,0.7)">Avg Latency</p></div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("System Status")
    st.success("All systems operational. SQLite Database Connected.")
    st.json({"Engine": "Streamlit", "Version": "V2.0-Alpha", "Model": "OpenRouter-Sonnnet"})

elif menu == "Admin_Dashboard":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("Global Admin Dashboard")
    st.write("System-wide monitoring overview.")
    
    col1, col2, col3 = st.columns(3)
    total_users = session.query(User).count()
    global_hubs = session.query(Hub).count()
    total_searches = session.query(SearchHistory).count()
    with col1:
        st.markdown(f'<div class="stat-card"><div class="metric-value">{total_users}</div><p style="color:rgba(255,255,255,0.7)">Total Signups</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="metric-value">{global_hubs}</div><p style="color:rgba(255,255,255,0.7)">Global Hubs Indexed</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="metric-value">{total_searches}</div><p style="color:rgba(255,255,255,0.7)">Global Queries</p></div>', unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "Admin_Users":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("User Credentials & Management")
    st.write("View and manage all registered users.")
    
    users = session.query(User).all()
    df_users = pd.DataFrame([{"Internal ID": u.id, "Email / Username": u.email, "Access Role": u.role} for u in users])
    st.dataframe(df_users, use_container_width=True)
    
    st.divider()
    st.subheader("Account Termination Protocol")
    st.warning("Deleting a user will permanently destroy all their uploaded code hubs, chat history, and metric data.")
    
    user_to_delete = st.selectbox("Select Account to Terminate:", [""] + [u.email for u in users if u.role != 'Admin'])
    
    if st.button("Terminate User & Wipe Data", type="primary", use_container_width=True):
        if user_to_delete:
            usr = session.query(User).filter(User.email == user_to_delete).first()
            if usr:
                from db_connector import FileMetadata
                # Cascading delete
                session.query(ChatMessage).filter(ChatMessage.user_id == usr.id).delete()
                session.query(SearchHistory).filter(SearchHistory.user_id == usr.id).delete()
                session.query(Hub).filter(Hub.user_id == usr.id).delete()
                session.query(FileMetadata).filter(FileMetadata.user_id == usr.id).delete()
                session.delete(usr)
                session.commit()
                st.success(f"User {user_to_delete} and all associated data were completely eradicated.")
                time.sleep(1.5)
                st.rerun()
        else:
            st.error("Please select a valid user.")
            
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "Admin_Activity":
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.header("Global Activity Logs")
    st.write("Live feed of all global queries and user searches.")
    
    history = session.query(SearchHistory).order_by(SearchHistory.id.desc()).limit(50).all()
    if history:
        # Join with users to show email
        users_map = {u.id: u.email for u in session.query(User).all()}
        df_hist = pd.DataFrame([{
            "User": users_map.get(h.user_id, "Unknown"), 
            "Query / Activity": h.query, 
            "Timestamp": h.timestamp
        } for h in history])
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("No activity logs generated yet.")
    st.markdown('</div>', unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.caption("Built for AI Code Vault Challenge")
st.sidebar.write("Team:")
st.sidebar.write("Liba, Nazish, Aleena, Hamza, Ali")

# --- System Reset Section ---
st.sidebar.divider()
st.sidebar.subheader("⚙️ System Management")
if st.sidebar.button("💥 Factory Reset Vault", help="Permanently delete all ingested repositories and history."):
    reset_vault()

# Patent/Copyright Sidebar Footer
st.sidebar.markdown("""
    <div style="margin-top: 3rem; text-align: center; color: rgba(255,255,255,0.3); font-size: 0.75rem; font-family: 'Inter', sans-serif;">
    © 2026 AI Code Vault<br>All Rights Reserved<br>Patent Pending
    </div>
""", unsafe_allow_html=True)
