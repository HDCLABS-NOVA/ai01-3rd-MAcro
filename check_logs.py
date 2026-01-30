import os
import json

logs_dir = 'c:/Users/Admin/Desktop/ai01-3rd-3team-1/logs'
files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.json')])

print("=" * 80)
print("📊 로그 파일 분석 결과")
print("=" * 80)
print()

bot_count = 0
normal_count = 0

for f in files:
    filepath = os.path.join(logs_dir, f)
    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    is_bot = data.get('bot', {}).get('is_bot', False)
    bot_type = data.get('bot', {}).get('type', 'normal')
    confidence = data.get('bot', {}).get('confidence', 0)
    
    if is_bot:
        bot_count += 1
        icon = "🤖"
        label = "봇"
    else:
        normal_count += 1
        icon = "👤"
        label = "정상"
    
    print(f"{icon} {label:6s} | {bot_type:20s} | {f}")

print()
print("=" * 80)
print(f"✅ 총 {len(files)}개 파일")
print(f"   - 👤 정상: {normal_count}개")
print(f"   - 🤖 봇: {bot_count}개")
print("=" * 80)
