#!/bin/bash

# =================================================================
# PentaMo V3.1 - Auto Setup Script
# Tự động cài đặt môi trường và các mô hình AI
# =================================================================

# Màu sắc
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   🚀 PentaMo V3.1 - Khởi tạo hệ thống tự động${NC}"
echo -e "${BLUE}============================================================${NC}"

# 1. Kiểm tra Python
echo -e "\n${YELLOW}1. Kiểm tra Python...${NC}"
if ! command -v python3 &> /dev/null
then
    echo -e "${RED}❌ Lỗi: Không tìm thấy Python3. Vui lòng cài đặt Python 3.10+ trước.${NC}"
    exit 1
fi
python3 --version | grep -E "3\.(10|11|12)" > /dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️ Cảnh báo: Khuyên dùng Python 3.10 trở lên.${NC}"
fi
echo -e "${GREEN}✅ OK: Python đã sẵn sàng.${NC}"

# 2. Thiết lập Môi trường ảo (venv)
echo -e "\n${YELLOW}2. Thiết lập Virtual Environment...${NC}"
if [ ! -d "venv" ]; then
    echo "Đang tạo venv mới..."
    python3 -m venv venv
else
    echo "Môi trường ảo (venv) đã tồn tại."
fi
source venv/bin/activate
echo -e "${GREEN}✅ OK: Đã kích hoạt venv.${NC}"

# 3. Cài đặt thư viện
echo -e "\n${YELLOW}3. Cài đặt các thư viện (requirements)...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ OK: Cài đặt thư viện thành công.${NC}"

# 4. Cấu hình Environment (.env)
echo -e "\n${YELLOW}4. Cấu hình file .env...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ Đã tạo file .env từ .env.example.${NC}"
else
    echo "File .env đã tồn tại."
fi

# 5. Khởi tạo Database
echo -e "\n${YELLOW}5. Khởi tạo Cơ sở dữ liệu (SQLite)...${NC}"
python scripts/seed_database.py
echo -e "${GREEN}✅ OK: Database đã sẵn sàng.${NC}"

# 6. Kiểm tra & Tải Ollama Models
echo -e "\n${YELLOW}6. Kiểm tra cấu hình AI (Ollama)...${NC}"
if ! command -v ollama &> /dev/null
then
    echo -e "${RED}❌ Không tìm thấy lệnh 'ollama'.${NC}"
    echo -e "${YELLOW}👉 Vui lòng cài đặt Ollama từ: https://ollama.com${NC}"
    echo -e "${YELLOW}Sau khi cài đặt xong, hãy chạy kịch bản này lại để tự động tải mô hình AI.${NC}"
else
    echo -e "${GREEN}✅ Đã tìm thấy Ollama.${NC}"
    
    echo -e "${BLUE}Đang tải Model A (Acree-Vylinh)...${NC}"
    ollama pull vuongnguyen2212/Acree-Vylinh
    
    echo -e "${BLUE}Đang tải Model B (LFM-Thinking)...${NC}"
    ollama pull lfm2.5-thinking:1.2b
    
    echo -e "${GREEN}✅ OK: Các mô hình AI đã được tải về.${NC}"
fi

echo -e "\n${BLUE}============================================================${NC}"
echo -e "${GREEN}✨ CHÚC MỪNG! HỆ THỐNG PENTAMO ĐÃ SẴN SÀNG!${NC}"
echo -e "Anh có thể chạy hệ thống bằng lệnh: ${YELLOW}./run.sh${NC}"
echo -e "${BLUE}============================================================${NC}"
