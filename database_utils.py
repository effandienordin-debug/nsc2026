import streamlit as st
import bcrypt
import json
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone

# --- PENGGUNAAN URL SUPABASE ---
DB_URL = st.secrets["DATABASE_URL"]

# Tambah parameter pooler khusus untuk Supabase (jika guna port 6543)
@st.cache_resource
def get_engine():
    return create_engine(
        DB_URL, 
        pool_size=10, 
        max_overflow=20, 
        pool_pre_ping=True
    )

engine = get_engine()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try: 
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except: 
        return False

def get_malaysia_time():
    my_tz = timezone(timedelta(hours=8))
    return datetime.now(my_tz).strftime('%Y-%m-%d %H:%M:%S')

def delete_item(table, item_id):
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": item_id})
    st.cache_resource.clear()
    st.toast(f"Item berjaya dipadam dari {table}")
    st.rerun()

# --- INIT DATABASE STRUKTUR NSC 2026 ---
@st.cache_resource
def init_db():
    with engine.begin() as conn:
        # 1. Admin Users
        conn.execute(text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(255) UNIQUE, full_name VARCHAR(255), password_hash VARCHAR(255), role VARCHAR(50))"))
        
        # 2. Juries (Ganti nama Reviewers)
        conn.execute(text("CREATE TABLE IF NOT EXISTS juries (id SERIAL PRIMARY KEY, username VARCHAR(255) UNIQUE, full_name VARCHAR(255), password_hash VARCHAR(255))"))
        
        # 3. Teams (100 Teams - Ganti Applicants)
        # Menambah ruangan school, stake, group_category (A, B, C, D) dan archive_link
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY, 
                name VARCHAR(255) UNIQUE, 
                school VARCHAR(255),
                stake TEXT,
                archive_link TEXT,
                group_category VARCHAR(10)
            )
        """))
        
        # 4. Evaluations (Ganti Reviews - Simpan rekod markah)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id SERIAL PRIMARY KEY, 
                jury_username VARCHAR(255), 
                team_name VARCHAR(255), 
                responses TEXT,  -- Simpan JSON skala 1-5 yang juri klik
                report_score FLOAT DEFAULT 0, 
                video_score FLOAT DEFAULT 0,
                total_score FLOAT DEFAULT 0,
                final_recommendation VARCHAR(50), 
                overall_justification TEXT, 
                submitted_at TIMESTAMP, 
                updated_at TIMESTAMP, 
                is_final BOOLEAN DEFAULT FALSE
            )
        """))
        
        # 5. Assignments (Juri ditugaskan ke Pasukan mana)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS team_assignments (
                id SERIAL PRIMARY KEY,
                team_name VARCHAR(255),
                jury_username VARCHAR(255),
                UNIQUE(team_name, jury_username)
            )
        """))

        # Tambah dalam init_db()
conn.execute(text("""
    CREATE TABLE IF NOT EXISTS group_assignments (
        id SERIAL PRIMARY KEY,
        group_category VARCHAR(10), -- A, B, C, atau D
        jury_username VARCHAR(255),
        UNIQUE(group_category, jury_username)
    )
"""))
        
        # Masukkan Master Admin default jika belum ada
        res = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        if res == 0:
            conn.execute(text("INSERT INTO users (username, full_name, role, password_hash) VALUES ('admin', 'Master Admin', 'Admin', :pw)"), 
                         {"pw": hash_password("Admin123!")})
    return True
