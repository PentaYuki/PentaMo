#!/usr/bin/env python3
import os
import re
from datetime import datetime
import json
from collections import defaultdict

# Định nghĩa pattern tìm ngày tháng
DATE_PATTERNS = [
    # Format: dd/mm/yyyy
    r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
    # Format: yyyy-mm-dd
    r'(\d{4})-(\d{1,2})-(\d{1,2})',
    # Format tiếng Việt: ngày dd tháng mm năm yyyy
    r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
    # Format với thời gian
    r'(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:SA|CH|AM|PM)?\s*(\d{1,2})/(\d{1,2})/(\d{4})',
]

# Phân loại loại tài liệu
CATEGORIES = {
    'ARCHITECTURE': ['kiến trúc', 'architecture', 'design', 'cấu trúc', 'structure', 'hệ thống'],
    'BUG_FIX': ['fix', 'bug', 'lỗi', 'sửa', 'critical', 'issue', 'vấn đề', 'redirect loop'],
    'IMPLEMENTATION': ['implementation', 'triển khai', 'code', 'endpoints', 'feature', 'tính năng'],
    'REPORT': ['report', 'báo cáo', 'status', 'trạng thái', 'summary', 'tóm tắt', 'final'],
    'MIGRATION': ['migration', 'di chuyển', 'upgrade', 'nâng cấp', 'refactor', 'tái cấu trúc'],
    'DOCUMENTATION': ['documentation', 'hướng dẫn', 'guide', 'quick start', 'reference', 'readme'],
    'CLEANUP': ['cleanup', 'dọn dẹp', 'checklist', 'kiểm tra'],
    'DEPLOYMENT': ['deployment', 'triển khai', 'production', 'staging'],
    'ANALYSIS': ['analysis', 'phân tích', 'codebase', 'diagnosis', 'chẩn đoán'],
    'TESTING': ['test', 'kiểm thử', 'testing', 'checklist'],
    'FEATURE': ['enhancement', 'nâng cao', 'feature', 'sales', 'pronoun', 'dual mode']
}

def extract_date(content, file_path):
    """Trích xuất ngày tháng từ nội dung file"""
    all_dates = []
    
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            try:
                if len(match) == 3:
                    d, m, y = match
                    if len(y) == 4 and int(m) <=12 and int(d) <=31:
                        dt = datetime(int(y), int(m), int(d))
                        all_dates.append(dt)
                elif len(match) ==4:
                    time, d, m, y = match
                    if len(y) ==4 and int(m) <=12 and int(d) <=31:
                        dt = datetime(int(y), int(m), int(d))
                        all_dates.append(dt)
            except:
                continue
    
    if all_dates:
        # Lấy ngày gần đây nhất trong file
        return max(all_dates)
    
    # Nếu không tìm thấy ngày trong nội dung thì dùng ngày sửa file
    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime)

def classify_document(content, filename):
    """Phân loại loại tài liệu"""
    text = (content + " " + filename).lower()
    
    scores = defaultdict(int)
    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in text:
                scores[category] +=1
    
    if scores:
        # Trả về category có điểm cao nhất
        return max(scores.items(), key=lambda x: x[1])[0]
    
    return 'OTHER'

def analyze_file(file_path):
    """Phân tích một file MD"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        file_date = extract_date(content, file_path)
        category = classify_document(content, os.path.basename(file_path))
        
        # Tóm tắt nội dung (dòng đầu tiên hoặc 100 ký tự đầu)
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        summary = lines[0][:150] if lines else ""
        
        return {
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'date': file_date.strftime('%d/%m/%Y'),
            'datetime_obj': file_date,
            'category': category,
            'summary': summary,
            'size_kb': round(os.path.getsize(file_path) / 1024, 2)
        }
    except Exception as e:
        return {
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'error': str(e)
        }

def main():
    print("🔍 Bắt đầu phân tích tất cả file Markdown trong dự án...")
    
    # Tìm tất cả file .md
    md_files = []
    for root, dirs, files in os.walk('.'):
        if 'venv' in root or '.pytest_cache' in root:
            continue
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    print(f"\n✅ Tìm thấy {len(md_files)} file .md hợp lệ\n")
    
    results = []
    for fp in md_files:
        res = analyze_file(fp)
        results.append(res)
    
    # Sắp xếp theo ngày giảm dần (mới nhất trước)
    results_sorted = sorted(results, key=lambda x: x.get('datetime_obj', datetime.min), reverse=True)
    
    # Nhóm theo loại phân tích
    grouped = defaultdict(list)
    for item in results_sorted:
        if 'category' in item:
            grouped[item['category']].append(item)
    
    # Xuất báo cáo
    output = []
    output.append("# BÁO CÁO PHÂN LOẠI TẤT CẢ FILE MARKDOWN")
    output.append(f"*Thời gian tạo báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*")
    output.append(f"*Tổng số file phân tích: {len(results)}*\n")
    
    output.append("---")
    
    output.append("## 📊 THỐNG KÊ THEO LOẠI TÀI LIỆU")
    for cat, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        output.append(f"- ✅ **{cat}**: {len(items)} file")
    
    output.append("\n---")
    
    output.append("## 📅 DANH SÁCH FILE THEO NGÀY (MỚI NHẤT ĐẦU)")
    output.append("| Ngày | Loại phân tích | Tên file | Tóm tắt |")
    output.append("|------|----------------|----------|---------|")
    
    for item in results_sorted:
        if 'error' in item:
            continue
        output.append(f"| {item['date']} | **{item['category']}** | `{item['filename']}` | {item['summary'][:80]}... |")
    
    output.append("\n---")
    
    output.append("## 📂 CHI TIẾT THEO LOẠI PHÂN TÍCH")
    
    for category, items in grouped.items():
        output.append(f"\n### 🔹 {category} ({len(items)} file)")
        for item in items:
            output.append(f"- `{item['date']}` : **{item['filename']}**")
            if item['summary']:
                output.append(f"  > {item['summary'][:120]}")
    
    # Lưu báo cáo ra file
    with open('MD_FILES_ANALYSIS_REPORT.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    # Lưu dữ liệu json để xử lý sau
    json_data = []
    for item in results_sorted:
        if 'datetime_obj' in item:
            del item['datetime_obj']
        json_data.append(item)
    
    with open('md_analysis_data.json', 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print("\n🎉 HOÀN THÀNH!")
    print(f"Báo cáo chi tiết đã được lưu vào: MD_FILES_ANALYSIS_REPORT.md")
    print(f"Dữ liệu JSON đã được lưu vào: md_analysis_data.json")
    
    print("\n📊 TỔNG KẾT:")
    for cat, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  - {cat}: {len(items)} file")

if __name__ == "__main__":
    main()