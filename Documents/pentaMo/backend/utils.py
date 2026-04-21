import os
from pathlib import Path

from typing import Optional

# Root của project (adjust nếu cần)
PROJECT_ROOT = str(Path(__file__).parent.parent)

def to_public_url(absolute_path: str) -> Optional[str]:
    """Convert absolute disk path → public /uploads/... URL"""
    if not absolute_path:
        return None
    
    path = Path(absolute_path)
    parts = path.parts
    
    try:
        # Tìm phần "data" và "uploads" liên tiếp trong đường dẫn
        for i in range(len(parts) - 1):
            if parts[i] == "data" and parts[i+1] == "uploads":
                # Tạo URL từ phần còn lại sau "data/uploads"
                rel_path = Path(*parts[i+2:])
                return "/uploads/" + str(rel_path).replace("\\", "/")
    except (ValueError, IndexError):
        pass
        
    # Fallback: trả về tên file nếu không tìm được marker mong muốn
    return "/uploads/" + path.name

def safe_public_url(path_str: str) -> str:
    """Kiểm tra file tồn tại trên đĩa trước khi trả về URL, nếu không trả placeholder"""
    if not path_str:
        return "/static/img/placeholder.png"
    
    path = Path(path_str)
    try:
        if not path.exists() or path.stat().st_size == 0:
            return "/static/img/placeholder.png"
    except Exception:
        return "/static/img/placeholder.png"
        
    return to_public_url(path_str) or "/static/img/placeholder.png"
