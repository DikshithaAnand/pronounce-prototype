import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️  WARNING: Supabase keys are missing in .env file!")

# Fallback defaults
DEFAULT_LANGUAGE = "en"