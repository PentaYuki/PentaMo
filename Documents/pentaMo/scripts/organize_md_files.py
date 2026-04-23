#!/usr/bin/env python3
import os
import shutil
import json

def main():
    print("🔍 Bắt đầu tổ chức tất cả file MD vào thư mục documentation/ ...")
    
    # Đọc dữ liệu phân tích đã tạo
    with open('md_analysis_data.json', 'r', encoding='utf-8') as f:
        md_files = json.load(f)
    
    # Tạo thư mục gốc documentation và các thư mục con theo loại
    base_dir = 'documentation'
    os.makedirs(base_dir, exist_ok=True)
    
    categories = list(set(item['category'] for item in md_files if 'category' in item))
    
    # Tạo thư mục con cho từng loại
    for cat in categories:
        cat_dir = os.path.join(base_dir, cat)
        os.makedirs(cat_dir, exist_ok=True)
        print(f"✅ Đã tạo thư mục: {cat_dir}/")
    
    print()
    
    moved_count = 0
    
    # Di chuyển từng file
    for item in md_files:
        if 'error' in item or 'category' not in item:
            continue
            
        src_path = item['file_path']
        category = item['category']
        filename = item['filename']
        
        if not os.path.exists(src_path):
            continue
            
        # Không di chuyển file báo cáo phân tích này
        if filename == 'MD_FILES_ANALYSIS_REPORT.md':
            continue
        
        dest_path = os.path.join(base_dir, category, filename)
        
        # Kiểm tra nếu file đã ở đúng vị trí rồi
        if os.path.abspath(src_path) == os.path.abspath(dest_path):
            continue
            
        try:
            shutil.move(src_path, dest_path)
            moved_count +=1
            print(f"✅ Di chuyển: {src_path:60} → {dest_path}")
        except Exception as e:
            print(f"❌ Lỗi di chuyển {src_path}: {e}")
    
    print(f"\n🎉 HOÀN THÀNH!")
    print(f"Đã tổ chức và di chuyển {moved_count} file Markdown vào thư mục documentation/")
    print(f"Các file được phân loại vào các thư mục con theo loại phân tích:")
    for cat in categories:
        count = len([f for f in md_files if f.get('category') == cat])
        print(f"  - {cat}/ : {count} file")

if __name__ == "__main__":
    main()