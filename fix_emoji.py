# -*- coding: utf-8 -*-
import sys
import io

# ตั้งค่า encoding สำหรับ Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# อ่านไฟล์
with open('utils_moss.py', 'r', encoding='utf-8') as f:
    content = f.read()

# แทนที่ emoji ทั้งหมด
replacements = [
    ('📊', ''),
    ('🌬️', ''),
    ('🔍', ''),
    ('🏛️', ''),
    ('🗺️', ''),
    ('📍', ''),
    ('🏷️', ''),
    ('🌟', ''),
    ('❌', ''),
    ('✅', ''),
    ('⚠️', ''),
    ('🏆', ''),
    ('📈', ''),
    ('🥇', 'GOLD'),
    ('🥈', 'SILVER'),
    ('🥉', 'BRONZE'),
    ('🟢', 'GREEN'),
    ('🟡', 'YELLOW'),
    ('🟠', 'ORANGE'),
    ('🔴', 'RED'),
    ('⚫', 'BLACK'),
    ('💡', ''),
    ('🏨', ''),
    ('🍽️', ''),
    ('🛍️', ''),
    (' API calls ที่ใช้ไป:', ' API calls used:'),
    (' API Usage:', ' API Usage:')
]

for old, new in replacements:
    content = content.replace(old, new)

# เขียนไฟล์กลับ
with open('utils_moss.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed emoji issues successfully')
