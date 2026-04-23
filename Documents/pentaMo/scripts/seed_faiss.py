#!/usr/bin/env python
"""
Seed FAISS memory with initial Q&A pairs
Run this once to populate the FAISS index with common questions and answers

Usage:
    python scripts/seed_faiss.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from services.faiss_memory import get_faiss_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Q&A data for both modes
SAMPLES = [
    # ========== CONSULTANT MODE ==========
    ("Xe ga nào tốt dưới 30 triệu?",
     "Xe ga tầm giá này nên chọn Vision cũ (2018-2019) hoặc Lead mới. Vision nhẹ nhàng, tiết kiệm xăng. "
     "Lead bền máy và có bảo hành. Ngoài ra còn SH mode i, Air blade là những lựa chọn tốt.",
     "consultant"),
    
    ("Honda SH dòng nào tốt nhất?",
     "SH có 2 dòng: SH Mode (125cc, trang trí đẹp) và SH đời mới (160cc, mạnh hơn, giá cao). "
     "Nếu chạy thành phố, SH Mode đủ dùng. Nếu muốn mạnh và bền, chọn SH 160cc đời mới.",
     "consultant"),
    
    ("Nên mua xe cũ hay mới?",
     "Xe mới: bảo hành, an toàn, nhưng mất giá nhanh. Xe cũ: rẻ hơn, nhưng cần kiểm tra kỹ máy móc, "
     "giấy tờ pháp lý. PentaMo hỗ trợ kiểm định độc lập để bạn an tâm khi mua.",
     "consultant"),
    
    ("Xe máy nào tiết kiệm xăng?",
     "Các dòng xe ga nhỏ (Vision, Lead, SH mode) tiết kiệm 45-55 km/l. Xe côn tay 125cc (Exciter, Raider) "
     "khoảng 40-45 km/l. Yếu tố tiết kiệm: thói quen lái, tải trọng, bảo dưỡng đều.",
     "consultant"),
    
    ("Bảo hành xe máy mấy năm?",
     "Hãng chính hãng thường bảo hành 1-2 năm toàn bộ xe, 3-5 năm cho động cơ. "
     "Nên mua từ đại lý chính để đảm bảo quyền lợi bảo hành.",
     "consultant"),
    
    ("Xe tay ga như Yamaha Jog hay Suzuki Sepia tốt không?",
     "Cả hai đều là dòng xe ga cổ điển. Yamaha Jog bền và tiết kiệm, Suzuki Sepia đơn giản. "
     "Nếu mua cũ, chú ý kiểm tra thân vỏ, rửa động cơ và áp lực pô.",
     "consultant"),
    
    # ========== TRADER MODE ==========
    ("Tôi muốn mua xe Honda SH 2020, giá khoảng bao nhiêu?",
     "SH 2020 hiện tại dao động 70-85 triệu tùy tình trạng xe (số km, bảo dưỡng, tình trạng ngoài). "
     "Bạn có thể xem các bài đăng trên PentaMo để so sánh. Kiểm tra kỹ giấy tờ và xem trực tiếp trước khi mua.",
     "trader"),
    
    ("Bán xe máy cũ thủ tục thế nào?",
     "Bước 1: Chuẩn bị giấy tờ (đăng ký, cavet, chứng thực bán). "
     "Bước 2: Chụp ảnh xe (4 góc độ). Bước 3: Đăng tin lên PentaMo. "
     "Bước 4: Kết nối người mua, thương lượng giá. Bước 5: Làm thủ tục sang tên.",
     "trader"),
    
    ("Nên khởi điểm giá bao nhiêu khi đăng bán xe?",
     "Khởi điểm giá cao hơn giá thực tế 5-10% để có khoảng thương lượng. "
     "Tham khảo các xe tương tự trên PentaMo để xác định giá hợp lý. "
     "Xe càng mới, bảo dưỡng tốt, giấy tờ rõ ràng thì giá càng cao.",
     "trader"),
    
    ("Có nên mua xe bằng góp không?",
     "Mua góp: vay ngân hàng hoặc công ty tài chính, lãi suất 8-12%/năm. "
     "Ưu: sở hữu xe ngay. Nhược: phải trả lãi, rủi ro nợ. "
     "Đánh giá tài chính cẩn thận trước khi quyết định.",
     "trader"),
    
    ("Làm sao để bán xe nhanh?",
     "1. Chụp ảnh chất lượng (ánh sáng tốt, sạch sẽ). 2. Mô tả đầy đủ (hãng, dòng, km, tình trạng). "
     "3. Giá hợp lý (so sánh thị trường). 4. Hỗ trợ kiểm định độc lập (tăng tin tưởng). "
     "5. Liên hệ nhanh, chuyên nghiệp với người quan tâm.",
     "trader"),
    
    ("Tôi cần mua xe tầm 5-7 triệu, có gợi ý không?",
     "Tầm giá này có thể tìm: Yamaha Jog cũ 2015-2018, Suzuki Sepia cũ, Honda Vision cũ 2014-2016. "
     "Nên xem kỹ số km, bảo dưỡng, giấy tờ. Có nên đặt lịch xem trực tiếp và kiểm định.",
     "trader"),
    
    ("Cách nhận biết xe bị ngập nước?",
     "Dấu hiệu: xì xào khi nổ máy, mùi ẩm trong yên xe, cuộn dây điện bị rỉ sét, chạy không êm, "
     "pin yếu. Nên gọi kỹ sư kiểm định để chắc chắn trước khi quyết định mua.",
     "trader"),
]


def seed_faiss():
    """Seed FAISS with sample data using batch encoding (5-10x faster)."""
    logger.info("Initializing FAISS and seeding with sample data (batch mode)...")

    memory = get_faiss_memory()

    initial_count = memory.index.ntotal
    logger.info(f"Index size before seed: {initial_count}")

    # add_batch() handles deduplication internally — safe to re-run
    added = memory.add_batch(SAMPLES)

    stats = memory.get_stats()
    logger.info(
        f"\nFAISS Memory Stats after seed:\n"
        f"  Total pairs     : {stats['total_pairs']}\n"
        f"  Consultant mode : {stats['consultant_count']}\n"
        f"  Trader mode     : {stats['trader_count']}\n"
        f"  Added this run  : {added}"
    )


if __name__ == "__main__":
    seed_faiss()
    logger.info("\n✓ FAISS seeding completed!")
