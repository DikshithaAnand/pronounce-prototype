import streamlit as st
from supabase import create_client, Client
import os
# Initialize Client (Using st.secrets is better, but hardcoding for dev is okay)
# COPY YOUR KEYS FROM backend/app/.env HERE
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def get_auth_client():
    """
    Returns a cached Supabase client for Authentication.
    """
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Auth Client Error: {e}")
        return None

def login(email, password):
    supabase = get_auth_client()
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def signup(email, password):
    supabase = get_auth_client()
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        return response.user, None
    except Exception as e:
        return None, str(e)

def logout():
    supabase = get_auth_client()
    supabase.auth.sign_out()
    st.session_state["user"] = None
    st.rerun()