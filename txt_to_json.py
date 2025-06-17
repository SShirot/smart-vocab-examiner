import json
import re

def convert_txt_to_json(txt_file, json_file):
    vocab_list = []

    with open(txt_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Ví dụ: pen (n): cây viết
            match = re.match(r"(.+?)\s+\((.+?)\)\s*:\s*(.+)", line.strip())
            if match:
                word = match.group(1).strip()
                word_type = match.group(2).strip()
                meaning = match.group(3).strip()
                vocab_list.append({
                    "word": word,
                    "type": word_type,
                    "meaning": meaning
                })

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(vocab_list, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã tạo {json_file} thành công.")

# Dùng
convert_txt_to_json("vocab.txt", "vocab.json")
