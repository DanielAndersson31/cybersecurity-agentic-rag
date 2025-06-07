import os
from dotenv import load_dotenv
from pathlib import Path

print("=== Environment Variable Debug ===")

# Try different ways to load the .env file
print("1. Current working directory:", os.getcwd())

# Method 1: Load from current directory
load_dotenv()
api_key_1 = os.getenv("OPENAI_API_KEY")
print(f"Method 1 (current dir): {api_key_1[:15] if api_key_1 else 'None'}...")

# Method 2: Load with explicit path
load_dotenv(".env")
api_key_2 = os.getenv("OPENAI_API_KEY")
print(f"Method 2 (explicit .env): {api_key_2[:15] if api_key_2 else 'None'}...")

# Method 3: Load with absolute path
project_root = Path(__file__).parent
env_path = project_root / ".env"
print(f"Looking for .env at: {env_path}")
print(f".env file exists: {env_path.exists()}")

load_dotenv(env_path)
api_key_3 = os.getenv("OPENAI_API_KEY")
print(f"Method 3 (absolute path): {api_key_3[:15] if api_key_3 else 'None'}...")

# Check the actual .env file content
if env_path.exists():
    with open(env_path, 'r') as f:
        content = f.read()
        print(f"\n.env file size: {len(content)} chars")
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'OPENAI_API_KEY' in line:
                print(f"Line {i+1}: {line[:30]}...") 