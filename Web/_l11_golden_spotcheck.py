import os, json, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_lineage.settings')
django.setup()

from django.test import Client

c = Client()

def ask(question, active_context=None, history=None):
    payload = {'question': question}
    if active_context is not None:
        payload['active_context'] = active_context
    if history is not None:
        payload['history'] = json.dumps(history)
    t0 = time.time()
    resp = c.post('/chatbot/ask/', data=json.dumps(payload), content_type='application/json')
    elapsed = time.time() - t0
    try:
        return resp.status_code, resp.json(), elapsed
    except Exception:
        return resp.status_code, {'raw': resp.content[:500]}, elapsed

ACTIVE_CTX = {
    "last_job_name": "DPK_H0_KLN", "last_table_name": None, "last_relationship": None,
    "last_upload_log": None, "last_list_job": None, "last_list_table": None,
    "pending_clarification": None,
}

results = {"pass": 0, "fail": 0}
def check(label, question, expected_intent, active_context=None, extra_check=None):
    status, body, el = ask(question, active_context=active_context)
    intent = body.get('intent')
    ok = intent == expected_intent
    extra_ok = True
    extra_note = ""
    if extra_check:
        extra_ok, extra_note = extra_check(body)
        ok = ok and extra_ok
    results["pass" if ok else "fail"] += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {question!r} -> intent={intent!r} (expected={expected_intent!r}) elapsed={el:.2f}s")
    if extra_note:
        print(f"       {extra_note}")
    return body

print("=" * 70)
print("GOLDEN REGRESSION SPOT-CHECK (reconstructed from PROJECT_MEMORY.md bug history)")
print("=" * 70)

check("Bug S (no job name)", "saya mau lihat job", "general")
check("Fase1I casual afirmasi", "iya", "casual")
check("Fase1I casual", "oke makasih", "casual")
check("Fase1I casual standalone particle", "coba job itu ya", "casual")
check("Bug C job-switch", "job lain", "list_data", active_context=ACTIVE_CTX)
check("Lanjutan5 list_kw show", "show jobs", "list_data")
check("Audit intent detection - 'hasil' substring trap", "job DPK_H0_KLN sudah berhasil atau belum", "job_status")
check("Temuan#3 'done' keyword", "yang udah done uploadnya apa aja", "job_status")
check("Temuan#4 Bagian A methodology_meta", "bagaimana cara anda menganalisa dampaknya", "methodology_meta")

body = check("Temuan#4 Bagian C coherence complaint (context preserved)",
             "kenapa tidak nyambung dengan chat sebelumnya?", "meta_coherence_complaint",
             active_context=ACTIVE_CTX,
             extra_check=lambda b: (
                 (b.get('active_context') or {}).get('last_job_name') == "DPK_H0_KLN",
                 f"last_job_name preserved: {(b.get('active_context') or {}).get('last_job_name')!r}"
             ))

check("Bug GG off-topic fresh session", "anda tahu indonesia itu apa", "out_of_scope_redirect")
check("Dangling-reference exemption (active job)", "yang ini gimana?", "job_detail", active_context=ACTIVE_CTX)
check("False-positive ETL_DOMAIN_KW - 'apa itu ETL'", "apa itu ETL", "general")
check("Bug HH 'apa aja' variant", "job apa aja yang ada saya mau lihat", "list_data")
check("Bug GG casual elongation 'okee'", "okee", "casual")

print()
print("=" * 70)
print(f"RINGKASAN GOLDEN SPOT-CHECK: PASS={results['pass']} FAIL={results['fail']}")
print("=" * 70)
