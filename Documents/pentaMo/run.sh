#!/bin/bash

# =================================================================
# PentaMo V3.1 - Run Script
# Khởi chạy Backend và phục vụ Frontend
# =================================================================

# Màu sắc
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Đang khởi chạy hệ thống PentaMo...${NC}"

# Kích hoạt venv
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✅ Đã kích hoạt môi trường ảo.${NC}"
else
    echo -e "${YELLOW}⚠️ Cảnh báo: Không tìm thấy thư mục venv. Hãy chạy ./setup.sh trước.${NC}"
fi

# Thiết lập PYTHONPATH để nhận diện các module ở thư mục gốc
export PYTHONPATH=$PYTHONPATH:.

# Force offline mode for SentenceTransformers to avoid hub timeouts
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
export HF_HUB_ETAG_TIMEOUT=120
export OMP_NUM_THREADS=1

python backend/main.py
