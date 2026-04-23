import sys
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.ERROR)  # Tắt log thừa để dễ nhìn

from backend.database import SessionLocal
from services.faiss_memory import get_faiss_memory
from services.llm_client import set_review_llm
from db.models import FAISSPendingReview

def run_test():
    print("========================================")
    print("🚀 BẮT ĐẦU TEST FAISS GATE LLM")
    print("========================================\n")
    
    db = SessionLocal()
    memory = get_faiss_memory()
    
    # =========================================================
    # KỊCH BẢN 1: CÓ GATE LLM (Gemini hoạt động bình thường)
    # =========================================================
    print("✅ KỊCH BẢN 1: ĐI QUA GATE LLM (Gemini bật)")
    set_review_llm("gemini")
    
    q1 = "có xe nào tầm 15 củ không shop"
    a1 = "Tôi hiện tại không thấy chiếc nào giá 15 triệu trong hệ thống. Khách muốn đổi hãng khác không?" # Xưng hô tôi/khách
    
    print(f"  👉 Câu hỏi gốc : {q1}")
    print(f"  👉 Trả lời gốc : {a1}")
    print("  ⏳ Đang gọi Gemini duyệt...")
    
    res1 = memory.gate_and_add(q1, a1, mode="consultant", db_session=db)
    
    print(f"  🎯 Kết quả Gate: {res1.get('gate')} / Trạng thái: {res1.get('status')}")
    print(f"  ✨ Câu trả lời đã sửa và lưu FAISS: {res1.get('answer')}")
    print("-" * 50 + "\n")
    
    # =========================================================
    # KỊCH BẢN 2: KHÔNG CÓ GATE LLM (Gemini bị lỗi / tắt)
    # =========================================================
    print("❌ KỊCH BẢN 2: KHÔNG QUA GATE LLM (Gemini mất kết nối/tắt)")
    set_review_llm("none") # Tắt LLM kiểm duyệt
    
    q2 = "shop ở đâu vậy qua coi xe được không"
    a2 = "Tao ở Sài Gòn nè, qua thì báo trước." # Câu trả lời thô lỗ
    
    print(f"  👉 Câu hỏi gốc : {q2}")
    print(f"  👉 Trả lời gốc : {a2}")
    print("  ⏳ Bắt đầu duyệt...")
    
    res2 = memory.gate_and_add(q2, a2, mode="consultant", db_session=db)
    
    print(f"  🎯 Trạng thái: {res2.get('status')} (Lý do: {res2.get('reason')})")
    print(f"  📥 Hệ thống xử lý: Đã đẩy vào DB chờ Admin duyệt.")
    print("-" * 50 + "\n")
    
    # =========================================================
    # KỂM TRA DATABASE (Hàng đợi của Admin)
    # =========================================================
    print("🗄️  KIỂM TRA HÀNG ĐỢI DUYỆT TAY CỦA ADMIN (Database)")
    pending = db.query(FAISSPendingReview).filter(FAISSPendingReview.status == "PENDING").all()
    if pending:
        for p in pending:
            print(f"  📝 [Pending ID: {p.id[-6:]}] Q: {p.question} | Original A: {p.answer_original}")
    else:
        print("  Không có mục nào cần duyệt.")
        
    db.close()
    print("\n========================================")
    print("🏁 HOÀN THÀNH TEST")
    print("========================================")

if __name__ == "__main__":
    run_test()
