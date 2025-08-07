import os
from ctypes import cdll

def test_gclib_dll():
    """Test if gclib.dll can be loaded."""
    dll_path = os.path.abspath("gclib.dll")
    print(f"Looking for gclib.dll at: {dll_path}")

    try:
        cdll.LoadLibrary(dll_path)
        print("✔ gclib.dll loaded successfully.")
        return True
    except Exception as e:
        print(f"❌ Failed to load gclib.dll: {e}")
        return False

if __name__ == "__main__":
    test_gclib_dll()
