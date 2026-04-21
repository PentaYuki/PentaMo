import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils import to_public_url

def test_path_normalization():
    paths = [
        "/Users/user/Documents/pentaMo/data/uploads/listings/image1.jpg",
        "C:\\Users\\user\\Documents\\pentaMo\\data\\uploads\\listings\\image2.jpg",
        "/uploads/listings/image3.jpg",
        "https://example.com/img.jpg"
    ]
    
    for p in paths:
        public = to_public_url(p)
        print(f"Original: {p}")
        print(f"Public  : {public}")
        print("-" * 20)

if __name__ == "__main__":
    test_path_normalization()
