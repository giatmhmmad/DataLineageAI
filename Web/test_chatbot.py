"""
Test Script untuk Chatbot - Verifikasi semua fitur
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_lineage.settings')
sys.path.insert(0, 'D:/ODP-IT Mandiri/OJT/V2/data-lineage/Web')
django.setup()

# Import views
from main.chatbot_views import chatbot_ask
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

factory = RequestFactory()

def make_request(question, history=None):
    """Buat mock request ke chatbot_ask"""
    data = {
        'question': question,
        'history': json.dumps(history or [])
    }
    request = factory.post('/chatbot/ask/', data=json.dumps(data), content_type='application/json')

    # Add session middleware
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()

    return request

def test_case(num, question, history=None):
    """Jalankan satu test case"""
    print(f"\n{'='*60}")
    print(f"TEST {num}: {question}")
    print(f"{'='*60}")

    request = make_request(question, history)
    response = chatbot_ask(request)
    result = json.loads(response.content)

    print(f"\nIntent: {result.get('intent')}")
    print(f"Mentioned Job: {result.get('mentioned_job')}")
    print(f"\nJawaban:")
    print("-" * 40)
    print(result.get('answer', ''))
    print("-" * 40)

    # Check if response has HTML tables
    if '<table' in result.get('answer', ''):
        print("[OK] HTML TABLE DETECTED")
    else:
        print("[ERROR] NO HTML TABLE")

    return result

# ============================================================
# TEST 1 - Percakapan normal
# ============================================================
print("\n" + "="*70)
print("TEST 1 - PERCAKAPAN NORMAL")
print("="*70)

history = []
r1 = test_case(1, "halo", history)
history.append({'role': 'user', 'content': 'halo'})
history.append({'role': 'assistant', 'content': r1.get('answer', '')})

r2 = test_case(2, "oke keren", history)
history.append({'role': 'user', 'content': 'oke keren'})
history.append({'role': 'assistant', 'content': r2.get('answer', '')})

r3 = test_case(3, "mau tanya nih", history)
history.append({'role': 'user', 'content': 'mau tanya nih'})
history.append({'role': 'assistant', 'content': r3.get('answer', '')})

# ============================================================
# TEST 2 - Detail job dan context carry-over
# ============================================================
print("\n" + "="*70)
print("TEST 2 - DETAIL JOB DAN CONTEXT CARRY-OVER")
print("="*70)

history = []
r4 = test_case(4, "detail job DMT_WHL_DDMAST_ORA_DLY_H1", history)
history.append({'role': 'user', 'content': 'detail job DMT_WHL_DDMAST_ORA_DLY_H1'})
history.append({'role': 'assistant', 'content': r4.get('answer', '')})

r5 = test_case(5, "source tablenya apa", history)
history.append({'role': 'user', 'content': 'source tablenya apa'})
history.append({'role': 'assistant', 'content': r5.get('answer', '')})

r6 = test_case(6, "target tablenya apa", history)
history.append({'role': 'user', 'content': 'target tablenya apa'})
history.append({'role': 'assistant', 'content': r6.get('answer', '')})

r7 = test_case(7, "tampilkan source table, target table, dan relasinya sekaligus", history)
history.append({'role': 'user', 'content': 'tampilkan source table, target table, dan relasinya sekaligus'})
history.append({'role': 'assistant', 'content': r7.get('answer', '')})

r8 = test_case(8, "oke", history)
history.append({'role': 'user', 'content': 'oke'})
history.append({'role': 'assistant', 'content': r8.get('answer', '')})

# ============================================================
# TEST 3 - Data lengkap tidak terpotong
# ============================================================
print("\n" + "="*70)
print("TEST 3 - DATA LENGKAP TIDAK TERPOTONG")
print("="*70)

history = []
r9 = test_case(9, "detail job RDBMS_CDP_NEW_RMTOOLS_DLY_H1", history)
history.append({'role': 'user', 'content': 'detail job RDBMS_CDP_NEW_RMTOOLS_DLY_H1'})
history.append({'role': 'assistant', 'content': r9.get('answer', '')})

r10 = test_case(10, "tampilkan semua source tablenya", history)
history.append({'role': 'user', 'content': 'tampilkan semua source tablenya'})
history.append({'role': 'assistant', 'content': r10.get('answer', '')})

# Count source tables
if '<table' in r10.get('answer', ''):
    import re
    tr_count = len(re.findall(r'<tr>', r10.get('answer', '')))
    print(f"\n>>> TOTAL TABLE ROWS: {tr_count} (seharusnya > 90 untuk 97 tabel)")

# ============================================================
# TEST 4 - Impact analysis
# ============================================================
print("\n" + "="*70)
print("TEST 4 - IMPACT ANALYSIS")
print("="*70)

history = []
r11 = test_case(11, "dampak jika CDP_DMT_WHL_EALCO_DLY_H0 gagal", history)
history.append({'role': 'user', 'content': 'dampak jika CDP_DMT_WHL_EALCO_DLY_H0 gagal'})
history.append({'role': 'assistant', 'content': r11.get('answer', '')})

print("\n" + "="*70)
print("SEMUA TEST SELESAI")
print("="*70)