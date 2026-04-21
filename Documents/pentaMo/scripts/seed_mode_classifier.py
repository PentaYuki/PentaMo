#!/usr/bin/env python
"""
Seed FAISS mode classifier with samples
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from services.faiss_memory import get_faiss_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Representative samples for classification
MODE_SAMPLES = [
    # Consultant (An) - Advice, Knowledge, Comparison
    ("Xe ga loại nào bền nhất?", "consultant"),
    ("So sánh Vision và Lead", "consultant"),
    ("Nên mua xe 50cc nào cho học sinh?", "consultant"),
    ("Kinh nghiệm mua xe cũ không bị lừa", "consultant"),
    ("Xe Honda có tốt hơn Yamaha không?", "consultant"),
    ("Cách bảo dưỡng xe máy định kỳ", "consultant"),
    ("Xe tay ga 150cc mẫu nào đẹp?", "consultant"),
    ("Tư vấn xe máy cho người thấp", "consultant"),
    ("Nên mua xe ga hay xe số đi làm xa?", "consultant"),
    ("Ưu nhược điểm của xe côn tay", "consultant"),
    
    # Trader - Price, Buy/Sell, Negotiation, Booking
    ("Bao nhiêu tiền chiếc SH này?", "trader"),
    ("Tôi muốn đặt lịch xem xe vào sáng mai", "trader"),
    ("Giá xe Vision 2022 cũ hiện nay?", "trader"),
    ("Thủ tục sang tên đổi chủ mất bao lâu?", "trader"),
    ("Có bớt giá thêm được không em?", "trader"),
    ("Xe này còn bảo hành không?", "trader"),
    ("Tôi muốn bán xe Wave Alpha 2021", "trader"),
    ("Địa chỉ xem xe ở đâu?", "trader"),
    ("Hình thức thanh toán như thế nào?", "trader"),
    ("Có hỗ trợ trả góp không?", "trader"),
    ("Đăng tin bán xe như thế nào?", "trader"),
    ("Cần kiểm định xe này gấp", "trader"),
]

def seed_mode_classifier():
    logger.info("Initializing Mode Classifier index...")
    memory = get_faiss_memory(index_name="mode_classifier")
    
    added = 0
    for question, mode in MODE_SAMPLES:
        try:
            # We don't need 'answer' for classification, but 'add' requires it
            memory.add(question, f"Mode classification sample: {mode}", mode)
            added += 1
        except Exception as e:
            logger.error(f"Failed to add sample: {e}")
            
    logger.info(f"✓ Seeded {added} samples for mode classifier")

if __name__ == "__main__":
    seed_mode_classifier()
