import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.utils import to_public_url
    
    # Test absolute path
    test_path = str(PROJECT_ROOT / "data" / "uploads" / "listings" / "test_image.jpg")
    url = to_public_url(test_path)
    print(f"Path: {test_path}")
    print(f"URL:  {url}")
    
    if url == "/uploads/listings/test_image.jpg":
        print("✓ to_public_url test passed!")
    else:
        print("✗ to_public_url test failed!")
except Exception as e:
    print(f"Error: {e}")
