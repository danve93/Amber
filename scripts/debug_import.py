import sys
import os

# Add src to path
sys.path.append(os.getcwd())

try:
    from src.api.routes import documents
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
