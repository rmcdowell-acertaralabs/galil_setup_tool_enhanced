import os
from ctypes import cdll

dll_path = os.path.abspath("gclib.dll")
print(f"Looking for gclib.dll at: {dll_path}")

try:
    cdll.LoadLibrary(dll_path)
    print("✔ gclib.dll loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load gclib.dll: {e}")
