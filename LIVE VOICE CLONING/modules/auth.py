import os
import json
import hashlib
import streamlit as st

USERS_FILE = "data/users.json"

def init_users_db():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": hash_password("admin123"),
            "demo": hash_password("demo123")
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f, indent=4)

def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        b'ai_translator_pro_salt_2026',
        100000
    ).hex()

def load_users() -> dict:
    init_users_db()
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user(username: str, password_hash: str):
    users = load_users()
    users[username] = password_hash
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def render_auth_module():
    """
    Renders Authentication & User Management Interface
    """
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    st.markdown('<h2 class="orbitron-text">SECURITY ACCESS PORTAL</h2>', unsafe_allow_html=True)
    st.write("Authenticate or create a new user profile to access neural voice translation capabilities.")

    tab1, tab2 = st.tabs(["🔒 LOGIN", "📝 REGISTER"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submit_btn = st.form_submit_button("AUTHENTICATE SYSTEM")

            if submit_btn:
                users = load_users()
                hashed = hash_password(password)
                if username in users and users[username] == hashed:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.success(f"Welcome back, Commander {username}!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password Credentials.")

    with tab2:
        with st.form("register_form"):
            reg_user = st.text_input("New Username", key="reg_user")
            reg_pass = st.text_input("New Password", type="password", key="reg_pass")
            reg_pass_confirm = st.text_input("Confirm Password", type="password", key="reg_pass_conf")
            reg_btn = st.form_submit_button("REGISTER ACCOUNT")

            if reg_btn:
                users = load_users()
                if not reg_user or not reg_pass:
                    st.warning("Please fill in all fields.")
                elif reg_user in users:
                    st.error("Username already registered.")
                elif reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match.")
                else:
                    save_user(reg_user, hash_password(reg_pass))
                    st.success("Account created successfully! You can now log in.")

    st.markdown('</div>', unsafe_allow_html=True)
