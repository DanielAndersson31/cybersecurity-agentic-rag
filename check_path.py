# check_path.py
import sys
import os

print("Python Executable:", sys.executable)
print("sys.path:")
for p in sys.path:
    print(f"  {p}")

try:
    import streamlit
    print(f"\nSuccessfully imported streamlit (version {streamlit.__version__})")
    print(f"Streamlit located at: {os.path.dirname(streamlit.__file__)}")
except ImportError as e:
    print(f"\nFailed to import streamlit: {e}")