import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from services.faiss_memory import get_faiss_memory
    
    def seed_classifier():
        print("--- Seeding Mode Classifier with Clean Samples ---")
        
        # Initialize mode classifier
        clf = get_faiss_memory(index_name="mode_classifier")
        
        # 1. Consultant Samples (General knowledge, advice, greetings)
        consultant_samples = [
            "Chào em, anh muốn tìm hiểu về xe máy",
            "Kinh nghiệm mua xe cũ là gì vậy em?",
            "Nên mua Vision hay Lead cho nữ đi làm?",
            "Xe 50cc có cần bằng lái không?",
            "Cách bảo dưỡng xe máy định kỳ như thế nào?",
            "Em giới thiệu cho anh các dòng xe tay ga mới nhất",
            "Xe côn tay đi phố có mỏi không em?",
            "Anh muốn hỏi về thủ tục sang tên xe máy",
            "PentaMo là gì vậy em?",
            "Chào bạn, mình cần tư vấn về xe máy cũ"
        ]
        
        # 2. Trader Samples (Buying, selling, pricing, checking inventory, viewing cars)
        trader_samples = [
            "Anh muốn mua xe Honda SH màu đỏ",
            "Bên mình có chiếc Winner X nào không em?",
            "Con Vision này giá bao nhiêu vậy?",
            "Anh muốn đăng bán xe của mình",
            "Cho anh lịch qua xem xe trực tiếp nhé",
            "Xe này có bớt được thêm không em?",
            "Anh muốn xem ảnh thật của chiếc Lead đời 2023",
            "Có xe nào biển số Hà Nội không em?",
            "Anh chốt con xe này, làm thủ tục thế nào?",
            "Có hỗ trợ trả góp không em?",
            "Anh muốn đổi xe bù tiền được không?",
            "Tìm cho anh xe tay ga dưới 20 triệu với"
        ]
        
        # Clear existing metadata if any (handled by being a fresh index after reset, 
        # but the class doesn't have a clear() method yet, so we just add)
        
        print(f"Adding {len(consultant_samples)} consultant samples...")
        for s in consultant_samples:
            clf.add(s, "Intent: Consultation", "consultant")
            
        print(f"Adding {len(trader_samples)} trader samples...")
        for s in trader_samples:
            clf.add(s, "Intent: Trading/Buying/Selling", "trader")
            
        print(f"✅ Mode classifier seeded. Stats: {clf.get_stats()}")

    if __name__ == "__main__":
        seed_classifier()

except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
