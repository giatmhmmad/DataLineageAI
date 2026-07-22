"""
Chatbot Views - Django Views for AI Chatbot
"""
import json
import logging
import traceback
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


def get_groq_api_key():
    """
    Helper function untuk mendapatkan GROQ_API_KEY dengan validasi.
    Coba dari settings terlebih dahulu, lalu dari environment variable.
    """
    from django.conf import settings
    import os

    # Coba dari settings
    api_key = getattr(settings, 'GROQ_API_KEY', None)

    # Jika tidak ada di settings, coba dari environment
    if not api_key:
        api_key = os.environ.get('GROQ_API_KEY')

    # Logging untuk debugging
    logger.info(
        f"GROQ_API_KEY exists={bool(api_key)} "
        f"length={len(api_key) if api_key else 0}"
    )

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing or empty. "
            "Please set GROQ_API_KEY in .env file or environment variable."
        )

    return api_key


def get_groq_client():
    """
    Helper function to create Groq client with proper error handling.
    This handles compatibility issues between groq library versions.
    """
    from groq import Groq

    api_key = get_groq_api_key()

    try:
        client = Groq(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Groq client initialization error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def build_html_table(title, columns, rows):
    if not rows:
        return "<p>Tidak ada data untuk " + title + ".</p>"
    html = "<h6><strong>" + title + "</strong></h6>"
    html += "<div style='overflow-x:auto; margin-bottom:16px'>"
    html += "<table class='table table-bordered table-striped table-sm table-hover'>"
    html += "<thead><tr>"
    # Selalu tambahkan kolom No di header
    html += "<th style='background-color:#0d6efd;color:white;width:50px'>No</th>"
    for col in columns:
        html += f"<th style='background-color:#0d6efd;color:white'>{col}</th>"
    html += "</tr></thead><tbody>"
    for i, row in enumerate(rows):
        html += "<tr>"
        # Kolom No otomatis dari index
        html += f"<td>{i+1}</td>"
        # VALIDASI: jika row adalah string bukan tuple/list
        if isinstance(row, str):
            html += f"<td><code style='background:none;color:#212529'>{row}</code></td>"
        else:
            for val in row:
                html += f"<td><code style='background:none;color:#212529'>{val}</code></td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html


def build_detail_table(title, field_value_pairs):
    """
    field_value_pairs: list of (field_name, value) tuples
    Contoh: [('Developer', 'GLORIA'), ('Total Source', '17')]
    """
    html = "<h6><strong>" + title + "</strong></h6>"
    html += "<div style='overflow-x:auto; margin-bottom:16px'>"
    html += "<table class='table table-bordered table-sm' style='max-width:600px'>"
    html += "<thead><tr>"
    html += "<th style='background-color:#0d6efd;color:white;width:200px'>Field</th>"
    html += "<th style='background-color:#0d6efd;color:white'>Keterangan</th>"
    html += "</tr></thead><tbody>"
    for field, value in field_value_pairs:
        html += f"<tr><td><strong>{field}</strong></td>"
        html += f"<td>{value}</td></tr>"
    html += "</tbody></table></div>"
    return html


def format_datetime(dt):
    """Ubah datetime ke format yang mudah dibaca manusia (Bahasa Indonesia)"""
    if not dt:
        return '-'
    try:
        # Manual convert UTC ke WIB (UTC+7) tanpa pytz
        from datetime import timezone, timedelta
        bulan = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei',
                 'Juni', 'Juli', 'Agustus', 'September', 'Oktober',
                 'November', 'Desember']

        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            # Convert ke UTC+7 (WIB)
            wib_offset = timezone(timedelta(hours=7))
            dt_wib = dt.astimezone(wib_offset)
            return f"{dt_wib.day} {bulan[dt_wib.month]} {dt_wib.year}, {dt_wib.strftime('%H:%M')} WIB"
        else:
            # Tidak ada timezone info, assume local
            return f"{dt.day} {bulan[dt.month]} {dt.year}, {dt.strftime('%H:%M')} WIB"
    except Exception as e:
        # Fallback terakhir
        try:
            return str(dt)
        except:
            return '-'


def chatbot_page(request):
    """
    Render halaman chatbot UI.
    GET request.
    """
    return render(request, 'chatbot.html', {
        'page_title': 'AI Chatbot',
        'page_description': 'Tanyakan apapun tentang job ETL dan data lineage'
    })


@csrf_exempt
@require_http_methods(["POST"])
def chatbot_ask(request):
    """
    Endpoint AJAX untuk menerima pertanyaan dari user.
    POST request dengan JSON body: {'question': '...'}
    """
    # ============================================================
    # STEP 1: QUERY SEMUA DATA DARI DATABASE
    # ============================================================
    from .models import JobDetail, Relationship, Table, JobDeveloper
    from .bot_eda import JobUploadSessions, JobUploadLogs
    from django.db.models import Count

    # Jobs dengan nama developer (bukan ID angka)
    all_jobs_raw = JobDetail.objects.prefetch_related('developers').all()
    all_jobs = []
    for job in all_jobs_raw:
        devs = list(job.developers.values_list('developer_name', flat=True))
        all_jobs.append({
            'job_name': job.job_name,
            'pic_job': job.pic_job,
            'developers': devs if devs else ['Belum ada developer'],
            'created_at': str(job.created_at)
        })

    # Relationship dengan info kategori tabel
    all_relationships = list(Relationship.objects.values(
        'job_name',
        'table1__table_name', 'table1__table_category',
        'table2__table_name', 'table2__table_category'
    ))

    # Tabel master
    all_tables = list(Table.objects.values(
        'table_name', 'table_category', 'table_desc'
    ))

    # Status upload dari bot_eda
    all_sessions = list(JobUploadSessions.objects.using('bot_eda').values(
        'job_name', 'current_status', 'upload_time', 'pic_job'
    ))

    # Ambil done time per job (waktu log terakhir dengan status Done)
    sessions_with_done = {}
    all_session_objs = list(
        JobUploadSessions.objects.using('bot_eda').all()
    )
    for sess in all_session_objs:
        done_log = JobUploadLogs.objects.using('bot_eda').filter(
            job=sess,
            status__icontains='done'
        ).order_by('-update_time').first()

        sessions_with_done[sess.job_name] = {
            'upload_time': sess.upload_time,
            'done_time': done_log.update_time if done_log else None,
            'current_status': sess.current_status,
            'pic_job': sess.pic_job,
        }

    # Ranking failure
    all_failures = list(
        JobUploadLogs.objects.using('bot_eda')
        .filter(status__icontains='fail')
        .values('job__job_name')
        .annotate(fail_count=Count('log_id'))
        .order_by('-fail_count')
    )

    # Statistik per job dari relationship - FIX: exact match + kategori lengkap
    job_stats = {}
    for job in all_jobs:
        jname = job['job_name']
        # Gunakan exact match untuk filter relationship
        rels = [r for r in all_relationships if r['job_name'] == jname]
        source_tables = []
        target_tables = []
        seen_src = set()
        seen_tgt = set()
        for r in rels:
            if r['table1__table_name'] and r['table1__table_name'] not in seen_src:
                seen_src.add(r['table1__table_name'])
                source_tables.append({
                    'table_name': r['table1__table_name'],
                    'category': r['table1__table_category']
                })
            if r['table2__table_name'] and r['table2__table_name'] not in seen_tgt:
                seen_tgt.add(r['table2__table_name'])
                target_tables.append({
                    'table_name': r['table2__table_name'],
                    'category': r['table2__table_category']
                })
        job_stats[jname] = {
            'total_relationships': len(rels),
            'total_source_tables': len(source_tables),
            'total_target_tables': len(target_tables),
            'source_tables': source_tables,      # list lengkap dengan kategori
            'target_tables': target_tables,      # list lengkap dengan kategori
            'developers': job['developers'],
            'raw_relationships': rels,           # semua relasi mentah
        }

    # ============================================================
    # STEP 2: SCHEMA EXPLANATION UNTUK LLM
    # ============================================================
    DB_SCHEMA = """
=== PENJELASAN STRUKTUR DATABASE ===
JobDetail: master data job ETL
- job_name: nama unik job
- developers: nama developer penanggung jawab (sudah diresolvesi dari ID)
- created_at: tanggal job dibuat

Relationship (2969 relasi - data utama lineage):
- job_name: nama job yang menjalankan proses ini
- table1__table_name: TABEL SOURCE = tabel yang DIBACA/INPUT oleh job
- table2__table_name: TABEL TARGET = tabel yang DITULIS/OUTPUT oleh job
- Artinya: job mengambil data dari table1 lalu menyimpan hasilnya ke table2

Table: master data tabel
- table_name: nama lengkap dengan schema (contoh: NEWDATAMART_PST.DM_NASABAH)
- table_category: DATAMART | STAGING | SOURCE DATA | OTHER
- table_desc: deskripsi tabel

JobUploadSessions (bot_eda): riwayat upload script job ke sistem
- current_status: 'Done' = upload berhasil, 'Upload Failed' = upload gagal
- upload_time: waktu upload

JobUploadLogs (bot_eda): log detail setiap proses upload
- fail_count: jumlah berapa kali job ini pernah gagal diupload
"""

    # ============================================================
    # PARSE PERTANYAAN DAN HISTORY
    # ============================================================
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        history_raw = data.get('history', '[]')
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'answer': 'Format request tidak valid. Gunakan format JSON.'
        })

    if not question:
        return JsonResponse({
            'success': False,
            'answer': 'Mohon masukkan pertanyaan Anda.'
        })

    # Parse conversation history
    try:
        conversation_history = json.loads(history_raw)
    except (json.JSONDecodeError, TypeError):
        conversation_history = []

    question_lower = question.lower()

    # ============================================================
    # STEP 3: DETEKSI JOB YANG DISEBUT DALAM PERTANYAAN + HISTORY
    # ============================================================
    mentioned_job = None
    # Urutkan dari terpanjang ke terpendek agar exact match tidak tertimpa partial
    job_names_sorted = sorted(
        [j['job_name'] for j in all_jobs],
        key=lambda x: len(x),
        reverse=True
    )

    # Exact match dulu (case insensitive)
    for jname in job_names_sorted:
        if jname.lower() in question_lower:
            mentioned_job = jname
            break

    # Partial match hanya jika tidak ada exact match
    if not mentioned_job:
        for jname in job_names_sorted:
            parts = [p for p in jname.lower().split('_') if len(p) > 4]
            if len(parts) >= 3 and all(p in question_lower for p in parts[:4]):
                mentioned_job = jname
                break

    # ============================================================
    # STEP 4: DETEKSI INTENT SEBELUM CONTEXT CARRY-OVER
    # Penting: Casual detection harus dilakukan SEBELUM context carry-over
    # agar kata-kata seperti "oke", "ya", "sip" tidak terbaca sebagai konteks job
    # ============================================================
    intent = 'general'

    # DETEKSI GREETING TERLEBIH DAHULU
    greeting_kw = ['halo', 'hai', 'hello', 'hi', 'selamat pagi', 'selamat siang',
                    'selamat sore', 'hey', 'pagi', 'siang', 'sore']

    # CAPABILITY KEYWORDS - dideteksi PERTAMA sebelum intent lain
    capability_kw = ['bisa apa', 'bisa bertanya apa', 'apa saja yang bisa',
                     'apa saja', 'fitur apa', 'kemampuan', 'bantuan apa', 'help',
                     'cara pakai', 'bagaimana cara', 'apa yang kamu bisa',
                     'kamu bisa apa', 'bisa tanya apa', 'bisa digunakan untuk',
                     'fungsinya apa', 'kegunaan', 'bertanya apa saja',
                     'bisa询问', '询问什么']

    # DEFENISIKAN SEMUA KEYWORD SEBELUM DIGUNAKAN
    casual_kw = ['waw', 'wow', 'keren', 'bagus', 'mantap', 'oke', 'ok',
                 'baik', 'iya', 'ya', 'sip', 'siap', 'noted', 'paham',
                 'mengerti', 'terima kasih', 'makasih', 'thanks', 'thank',
                 'ingin bertanya', 'mau tanya', 'bole tanya', 'mau bertanya',
                 'ada pertanyaan', ' lanjut', 'next', 'oke lanjut',
                 'baiklah', 'sudah', 'cukup', 'oke deh', 'oke baik',
                 'oke thanks', 'oke makasih', 'sipp', 'gass', 'gas']

    # CONTEXT RESET KEYWORDS - menandakan user ingin pindah topik
    context_reset_kw = ['oke', 'ok', 'baik', 'baiklah', 'cukup',
                        'sudah', 'terima kasih', 'makasih', 'thanks',
                        'sip', 'noted', 'paham', 'mengerti', 'lanjut',
                        'next', 'selanjutnya', 'ganti topik',
                        'pertanyaan lain', 'hal lain', 'topik lain']

    impact_kw = ['dampak', 'impact', 'terdampak', 'pengaruh',
                 'jika gagal', 'kalau gagal', 'jika terlambat',
                 'kalau terlambat', 'jika telat', 'kalau telat',
                 'downstream', 'efek', 'buatkan impact', 'buat impact',
                 'impact analysis', 'impact analysisnya', 'analisis dampak',
                 'analisis impactnya', 'coba buatkan impact',
                 'berikan impact', 'tampilkan impact']

    # CONFUSED KEYWORDS - user bingung mau tanya apa
    confused_kw = ['bingung', 'tidak tahu mau tanya', 'ga tau mau tanya',
                   'gak tau', 'nanya yang lain', 'tanya yang lain',
                   'hal lain', 'topik lain', 'pertanyaan lain',
                   'mau nanya lain', 'mau tanya lain', 'ganti topik']

    full_detail_kw = ['source table, target', 'target table, source',
                      'source dan target', 'target dan source',
                      'detail source', 'detail target',
                      'semua tabel', 'lengkap', 'semua detail',
                      'relasinya', 'semua relasi', 'source table dan',
                      'target table dan', 'apa saja source table,']

    source_kw = ['source', 'sumber', 'input', 'dari mana', 'source table',
                 'tabel sumber', 'membaca', 'mengambil']
    target_kw = ['target', 'output', 'hasil', 'menghasilkan', 'menulis',
                 'tabel output', 'tabel target', 'table name', 'tabel name',
                 'tabel apa', 'apa saja tabel']
    status_kw = ['status', 'kondisi', 'failed', 'gagal', 'sukses',
                 'terlambat', 'telat', 'running', 'berjalan', 'upload failed',
                 'upload status']
    log_kw = ['log', 'logs', 'detail log', 'riwayat', 'history upload',
              'history log', 'log upload', 'upload log', 'lihat log',
              'tampilkan log', 'aktivitas', 'rekam jejak',
              'done time', 'waktu selesai', 'kapan selesai',
              'kapan upload', 'waktu upload', 'jam berapa selesai',
              'tanggal upload', 'selesai kapan', 'upload kapan',
              'jam selesai', 'waktu done', 'done kapan',
              'kapan selesai', 'selesai diupload', 'kapan done',
              'waktu selesai upload', 'jam selesai upload',
              'tanggal selesai']
    list_kw  = ['apa saja', 'daftar', 'list', 'tampilkan semua', 'ada berapa',
                'berapa total', 'berapa jumlah', 'semua job', 'semua tabel']
    rel_kw   = ['relationship', 'relasi', 'berapa relationship',
                'total relationship', 'jumlah relationship']
    dev_kw = ['developer', 'siapa developer', 'pic job',
              'penanggung jawab', 'tim developer', 'dibuat oleh',
              'dikerjakan oleh', 'developer job', 'who is']

    # ============================================================
    # DETEKSI CONTEXT RESET - SEBELUM CARRY-OVER
    # ============================================================
    is_reset = (
        any(k in question_lower for k in context_reset_kw)
        and len(question.split()) <= 5
        and not any(k in question_lower for k in
                    impact_kw + source_kw + target_kw + list_kw + dev_kw + status_kw + rel_kw + capability_kw + confused_kw)
    )

    # INIT last_mentioned_job untuk prevent UnboundLocalError
    last_mentioned_job = None

    # JIKA PESAN ADALAH RESET, JANGAN LAKUKAN CONTEXT CARRY-OVER
    if is_reset:
        mentioned_job = None
        last_mentioned_job = None
        intent = 'casual'  # paksa jadi casual
    # JIKA INTENT SUDAH KETEMU (greeting ATAU casual ATAU capability), JANGAN LAKUKAN CONTEXT CARRY-OVER
    elif intent not in ['greeting', 'casual', 'capability']:
        # JIKA BUKAN GREETING/CASUAL/CAPABILITY, BARU LAKUKAN CONTEXT CARRY-OVER
        # Kumpulkan semua job yang disebut dalam history, urut dari terbaru
        jobs_in_history = []
        if not mentioned_job and conversation_history:
            for msg in reversed(conversation_history):
                content_lower = msg['content'].lower()
                for jname in job_names_sorted:
                    if jname.lower() in content_lower:
                        if jname not in jobs_in_history:
                            jobs_in_history.append(jname)

        # Job aktif = job PERTAMA yang ditemukan dari pesan TERBARU
        # Hanya ambil dari pesan USER, bukan dari jawaban assistant
        # karena jawaban assistant sering menyebut banyak job lain
        last_mentioned_job = None
        if not mentioned_job and conversation_history:
            for msg in reversed(conversation_history):
                if msg.get('role') == 'user':
                    content_lower = msg['content'].lower()
                    for jname in job_names_sorted:
                        if jname.lower() in content_lower:
                            last_mentioned_job = jname
                            break
                if last_mentioned_job:
                    break

        # Gunakan job dari history HANYA jika pertanyaan sekarang
        # tidak menyebut job lain secara eksplisit
        if not mentioned_job and last_mentioned_job:
            mentioned_job = last_mentioned_job

    # ============================================================
    # DETEKSI INTENT DATA - PERTAMA (PRIORITAS TERTINGGI)
    # Capability, Impact, Log, Source, Target, Dev, Status, Rel, List, Job Detail
    # Baru setelah itu greeting dan casual
    # ============================================================
    if any(k in question_lower for k in capability_kw):
        intent = 'capability'
    elif any(k in question_lower for k in impact_kw):
        intent = 'impact_analysis'
    elif any(k in question_lower for k in log_kw):
        intent = 'job_logs'
    elif any(k in question_lower for k in source_kw):
        intent = 'source_tables'
    elif any(k in question_lower for k in target_kw):
        intent = 'target_tables'
    elif any(k in question_lower for k in dev_kw):
        intent = 'developer_info'
    elif any(k in question_lower for k in status_kw):
        intent = 'job_status'
    elif any(k in question_lower for k in rel_kw):
        intent = 'relationship_info'
    elif any(k in question_lower for k in list_kw):
        intent = 'list_data'
    elif mentioned_job:
        intent = 'job_detail'
    # GREETING dan casual SETELAH semua intent data
    elif any(k in question_lower for k in greeting_kw) and len(question.split()) <= 3:
        intent = 'greeting'
    elif any(k in question_lower for k in casual_kw) and len(question.split()) <= 5:
        intent = 'casual'
    elif any(k in question_lower for k in confused_kw):
        intent = 'confused'
    else:
        intent = 'general'

    # DEBUG LOGGING
    print(f"DEBUG intent: {intent} | job: {mentioned_job} | q: {question}")

    # ============================================================
    # STEP 5: BANGUN CONTEXT SPESIFIK PER INTENT
    # ============================================================
    specific_context = ""

    # CAPABILITY HANDLER - Jawab natural tanpa dump data
    if intent == 'capability':
        specific_context = """
Pertanyaan user: \"""" + question + """\"

Kamu adalah AI Assistant untuk sistem Data Lineage EDA.
Sistem ini berisi:
- """ + str(len(all_jobs)) + """ job ETL terdaftar
- """ + str(len(all_tables)) + """ tabel database
- """ + str(len(all_relationships)) + """ relasi antar tabel

Tugas: Jawab pertanyaan user secara natural tentang apa saja
yang bisa ditanyakan ke kamu. Jelaskan kemampuan berikut
dalam bahasa yang ramah dan mudah dipahami:

1. Info Job: detail job, developer, status upload
2. Tabel: source table dan target table per job
3. Relasi: berapa relasi per job
4. Impact Analysis: dampak jika suatu job gagal/terlambat
5. Insight: job paling sering gagal, job terbaru, dll
6. Pertanyaan umum: konsep ETL, best practice, dll

Berikan juga 3-4 contoh pertanyaan yang bisa diajukan.
Jangan tampilkan data tabel apapun. Jawab natural saja.
"""

    # GREETING HANDLER
    if intent == 'greeting':
        specific_context = f"""
PERTANYAAN: {question}

Tugas: Balas sapaan user dengan ramah dan profesional dalam 2-3 kalimat.
Perkenalkan diri sebagai AI Assistant untuk Data Lineage EDA.
Sebutkan bahwa kamu bisa membantu tentang: info job, status upload,
impact analysis, dependency antar job, dan pertanyaan seputar ETL.
Jangan tampilkan data apapun. Jangan list schema database.
"""
    # CONFUSED HANDLER - Bantu user yang bingung mau tanya apa
    elif intent == 'confused':
        specific_context = f"""
Pertanyaan user: "{question}"

Sistem ini berisi {len(all_jobs)} job ETL, {len(all_tables)} tabel,
{len(all_relationships)} relasi.

Tugas: Bantu user dengan cara:
1. Akui bahwa tidak apa-apa jika bingung
2. Tawarkan beberapa topik yang bisa ditanyakan:
   - Info detail job (developer, status, relasi)
   - Source table dan target table per job
   - Impact analysis jika suatu job gagal
   - Job yang paling sering gagal
   - Penjelasan konsep ETL
3. Berikan 3-4 contoh pertanyaan konkret
Jawab ramah, singkat, JANGAN tampilkan tabel atau data apapun.
"""
    # CASUAL HANDLER - SANGAT SINGKAT, TANPA DATA
    elif intent == 'casual':
        # Cek job aktif dari history untuk referensi saja
        active_job = mentioned_job or last_mentioned_job

        specific_context = f"""
Pesan user: "{question}"
Job yang sedang dibahas (jika ada): {active_job or 'tidak ada'}

Tugas: Balas pesan kasual ini secara natural dan SANGAT SINGKAT.
- Jika "oke", "baik", "ya", "sip" → balas 1 kalimat saja seperti:
  "Siap! Ada lagi yang ingin ditanyakan?"
- Jika apresiasi seperti "keren", "bagus" → balas singkat dan ramah,
  tawarkan apakah ada yang ingin dilanjutkan
- Jika "ingin bertanya", "mau tanya" → persilakan dengan singkat
JANGAN tampilkan data apapun. JANGAN tampilkan tabel.
JANGAN tampilkan info job. Maksimal 1-2 kalimat.
"""
    elif intent == 'impact_analysis':
        # ============================================================
        # IMPACT ANALYSIS - DENGAN JOB SPESIFIK
        # ============================================================
        if mentioned_job:
            from groq import Groq
            from django.conf import settings

            # Impact analysis untuk job spesifik
            output_tables = set()
            for r in all_relationships:
                if mentioned_job.lower() in r['job_name'].lower():
                    if r['table2__table_name']:
                        output_tables.add(r['table2__table_name'])

            level2 = {}
            level2_outputs = set()
            for r in all_relationships:
                if r['table1__table_name'] in output_tables:
                    if mentioned_job.lower() not in r['job_name'].lower():
                        level2[r['job_name']] = r['table1__table_name']
                        if r['table2__table_name']:
                            level2_outputs.add(r['table2__table_name'])

            level3 = {}
            for r in all_relationships:
                if r['table1__table_name'] in level2_outputs:
                    if r['job_name'] not in level2 and mentioned_job.lower() not in r['job_name'].lower():
                        level3[r['job_name']] = r['table1__table_name']

            # Build tabel job terdampak langsung (level 2) di Python
            level2_html = build_html_table(
                f"Job Terdampak Langsung ({len(level2)} job)",
                ["Job Terdampak", "Via Tabel"],
                [(k, v) for k, v in level2.items()]
            )

            # Build tabel job terdampak tidak langsung (level 3) di Python
            level3_html = build_html_table(
                f"Job Terdampak Tidak Langsung ({len(level3)} job)",
                ["Job Terdampak", "Via Tabel"],
                [(k, v) for k, v in level3.items()]
            ) if level3 else ""

            # LLM hanya buat narasi chain dampak
            impact_intro_context = f"""
Job yang diteliti: {mentioned_job}
Tabel output job ini: {list(output_tables)}
Job langsung terdampak: {list(level2.keys())}
Job tidak langsung terdampak: {list(level3.keys())}
Total terdampak: {len(level2) + len(level3)} job

Tugas: Jelaskan chain dampak secara naratif 2-3 kalimat.
Format: "Jika {mentioned_job} gagal → tabel X tidak update → job Y ikut gagal → dst"
Berikan rekomendasi prioritas penanganan singkat.
JANGAN buat tabel HTML. Tabel sudah disiapkan terpisah.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": impact_intro_context}
                ],
                temperature=0.1,
                max_tokens=400
            )
            llm_narasi = llm_response.choices[0].message.content
            answer = llm_narasi + "<br>" + level2_html + level3_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job})

        # ============================================================
        # IMPACT ANALYSIS - TANPA JOB SPESIFIK
        # Kumpulkan semua job bermasalah dan hitung dampaknya
        # ============================================================
        else:
            from groq import Groq
            from django.conf import settings

            # STEP 1: Kumpulkan semua job bermasalah dari bot_eda
            failed_sessions = [s for s in all_sessions
                               if s.get('current_status') and 'fail' in s['current_status'].lower()]
            failed_job_names = [s['job_name'] for s in failed_sessions]

            # Tambahkan job yang sering gagal dari logs (meski statusnya Done)
            for f in all_failures:
                jname = f['job__job_name']
                if jname not in failed_job_names:
                    failed_job_names.append(jname)

            # STEP 2: Untuk setiap job bermasalah, hitung dampaknya
            all_impacts = []
            for jname in failed_job_names:
                # Cari tabel OUTPUT job ini dari Relationship
                output_tables = set()
                for r in all_relationships:
                    if r['job_name'] == jname and r['table2__table_name']:
                        output_tables.add(r['table2__table_name'])

                # Cari job lain yang pakai tabel output ini sebagai INPUT
                impacted_jobs = {}
                for r in all_relationships:
                    if r['table1__table_name'] in output_tables:
                        if r['job_name'] != jname:
                            impacted_jobs[r['job_name']] = r['table1__table_name']

                # Ambil status dan fail count
                session = next((s for s in all_sessions
                                if s['job_name'] == jname), None)
                fail_count = next((f['fail_count'] for f in all_failures
                                   if f['job__job_name'] == jname), 0)

                all_impacts.append({
                    'job_name': jname,
                    'status': session['current_status'] if session else 'Tidak ada data upload',
                    'fail_count': fail_count,
                    'output_tables': list(output_tables),
                    'total_output_tables': len(output_tables),
                    'impacted_jobs': impacted_jobs,
                    'total_impacted_jobs': len(impacted_jobs),
                })

            # STEP 3: Sort dari yang paling banyak dampaknya
            all_impacts.sort(key=lambda x: x['total_impacted_jobs'], reverse=True)

            # STEP 4: Build tabel ringkasan semua job bermasalah
            summary_rows = []
            for imp in all_impacts:
                summary_rows.append((
                    imp['job_name'],
                    imp['status'],
                    str(imp['fail_count']) + 'x',
                    str(imp['total_output_tables']),
                    str(imp['total_impacted_jobs']),
                ))

            summary_html = build_html_table(
                "Ringkasan Job Bermasalah & Dampaknya (" + str(len(all_impacts)) + " job)",
                ["Nama Job", "Status Upload", "Jumlah Gagal",
                 "Tabel Output", "Job Terdampak"],
                summary_rows
            )

            # STEP 5: Build detail per job bermasalah
            detail_html = ""
            for imp in all_impacts:
                status_icon = "🔴" if 'fail' in imp['status'].lower() else "🟡"

                if imp['output_tables']:
                    output_rows = [(t,) for t in sorted(imp['output_tables'])]
                    output_html = build_html_table(
                        "Tabel Output dari " + imp['job_name'] + " (" + str(len(output_rows)) + " tabel)",
                        ["Nama Tabel"],
                        output_rows
                    )
                else:
                    output_html = "<p><em>Tidak ada tabel output terdeteksi di sistem.</em></p>"

                if imp['impacted_jobs']:
                    impact_rows = [(k, v) for k, v in sorted(imp['impacted_jobs'].items())]
                    impact_job_html = build_html_table(
                        "Job Terdampak jika " + imp['job_name'] + " Gagal (" + str(len(impact_rows)) + " job)",
                        ["Job Terdampak", "Via Tabel"],
                        impact_rows
                    )
                else:
                    impact_job_html = "<p><em>Tidak ada job lain yang terdampak langsung.</em></p>"

                detail_html += """
<hr style='margin:24px 0'>
<h6><strong>""" + status_icon + " " + imp['job_name'] + """</strong></h6>
<p>
  Status: <strong>""" + imp['status'] + """</strong> &nbsp;|&nbsp;
  Riwayat Gagal: <strong>""" + str(imp['fail_count']) + """x</strong> &nbsp;|&nbsp;
  Total Job Terdampak: <strong>""" + str(imp['total_impacted_jobs']) + """ job</strong>
</p>
""" + output_html + impact_job_html

            # STEP 6: LLM hanya buat narasi pembuka
            narasi_context = """
Ada """ + str(len(all_impacts)) + """ job bermasalah di sistem.
Data dampak per job (diurutkan dari dampak terbesar):
""" + str([{
    'job': x['job_name'],
    'status': x['status'],
    'gagal': str(x['fail_count']) + 'x',
    'tabel_output': x['total_output_tables'],
    'job_terdampak': x['total_impacted_jobs']
} for x in all_impacts]) + """

Tugas: Buat narasi pembuka 2-3 kalimat yang menjelaskan:
1. Kondisi sistem secara keseluruhan
2. Job mana yang paling kritis (paling banyak job terdampak)
3. Rekomendasi tindakan prioritas
Gunakan bahasa profesional, tidak kaku.
JANGAN buat tabel. Tabel sudah disiapkan terpisah.
"""
            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": narasi_context}
                ],
                temperature=0.1,
                max_tokens=400
            )
            llm_narasi = llm_response.choices[0].message.content
            answer = llm_narasi + "<br>" + summary_html + detail_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": None})

    # ============================================================
    # JOB_LOGS HANDLER - Tampilkan log upload job
    # ============================================================
    elif intent == 'job_logs':
        from .bot_eda import JobUploadSessions, JobUploadLogs
        from groq import Groq
        from django.conf import settings

        # Jika mentioned_job belum terdeteksi, coba cari lagi dari question
        if not mentioned_job:
            for jname in job_names_sorted:
                if jname.lower() in question_lower:
                    mentioned_job = jname
                    break

        # Juga cari dari history jika masih tidak ketemu
        if not mentioned_job and conversation_history:
            for msg in reversed(conversation_history):
                if msg.get('role') == 'user':
                    for jname in job_names_sorted:
                        if jname.lower() in msg['content'].lower():
                            mentioned_job = jname
                            break
                if mentioned_job:
                    break

        if mentioned_job:
            session = next((s for s in all_sessions
                            if s['job_name'] == mentioned_job), None)

            if session:
                session_obj = JobUploadSessions.objects.using('bot_eda').filter(
                    job_name=mentioned_job
                ).first()

                logs = []
                if session_obj:
                    logs = list(JobUploadLogs.objects.using('bot_eda').filter(
                        job=session_obj
                    ).values(
                        'log_id', 'status', 'log_message', 'update_time'
                    ).order_by('update_time'))

                # Ambil done_time dari sessions_with_done
                done_info = sessions_with_done.get(mentioned_job, {})
                done_time = done_info.get('done_time')

                session_html = build_detail_table(
                    f"Info Upload — {mentioned_job}",
                    [
                        ('Job Name', mentioned_job),
                        ('Status Terakhir', session['current_status']),
                        ('Waktu Upload', format_datetime(session['upload_time'])),
                        ('Done Time', format_datetime(done_time) if done_time else 'Belum selesai'),
                        ('PIC Upload', str(session.get('pic_job', '-'))),
                    ]
                )

                if logs:
                    log_rows = [
                        (str(log['status']),
                         str(log['log_message'])[:120] + '...'
                         if len(str(log['log_message'])) > 120
                         else str(log['log_message']),
                         format_datetime(log['update_time']))
                        for log in logs
                    ]
                    log_html = build_html_table(
                        f"Detail Log Upload ({len(logs)} entri)",
                        ["Status", "Pesan Log", "Waktu"],
                        log_rows
                    )
                else:
                    log_html = "<p><em>Tidak ada log detail tersedia.</em></p>"

                # LLM buat narasi
                narasi_context = f"""
Job: {mentioned_job}
Status upload: {session['current_status']}
Waktu upload: {format_datetime(session['upload_time'])}
Done time: {format_datetime(done_time) if done_time else 'Belum selesai'}
Total log entries: {len(logs)}
Sample log: {[{'status': l['status'], 'time': format_datetime(l['update_time'])} for l in logs[:5]]}

Tugas: Buat ringkasan singkat 2 kalimat tentang riwayat
upload job ini. Sebutkan kapan selesai dan statusnya.
JANGAN buat tabel. Tabel sudah disiapkan terpisah.
"""
                client = get_groq_client()
                llm_response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                        {"role": "user", "content": narasi_context}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                llm_narasi = llm_response.choices[0].message.content
                answer = llm_narasi + "<br>" + session_html + log_html

            else:
                answer = (f"<p>Job <code>{mentioned_job}</code> "
                          f"belum memiliki riwayat upload di sistem.</p>")

        else:
            # Tampilkan semua sessions dengan done_time
            session_rows = []
            for s in sorted(all_sessions,
                           key=lambda x: x['upload_time'], reverse=True):
                done_info = sessions_with_done.get(s['job_name'], {})
                done_time = done_info.get('done_time')
                session_rows.append((
                    s['job_name'],
                    s['current_status'],
                    format_datetime(s['upload_time']),
                    format_datetime(done_time) if done_time else 'Belum selesai'
                ))
            log_html = build_html_table(
                f"Riwayat Upload Semua Job ({len(session_rows)} job)",
                ["Nama Job", "Status", "Waktu Upload", "Done Time"],
                session_rows
            )
            answer = "<p>Berikut riwayat upload semua job di sistem:</p>" + log_html

        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": mentioned_job})

    # FULL DETAIL HANDLER - Build 3 tabel di Python, LLM hanya intro
    elif intent == 'full_detail' and mentioned_job:
        from groq import Groq
        from django.conf import settings

        stats = job_stats.get(mentioned_job, {})
        src = stats.get('source_tables', [])
        tgt = stats.get('target_tables', [])
        rels = stats.get('raw_relationships', [])

        rel_detail = []
        seen_rel = set()
        for r in rels:
            key = (r['table1__table_name'], r['table2__table_name'])
            if key not in seen_rel:
                seen_rel.add(key)
                rel_detail.append(key)

        # Build 3 tabel di Python
        src_html = build_html_table(
            f"Source Tables ({len(src)} tabel)",
            ["Nama Tabel", "Kategori"],
            [(s['table_name'], s.get('category', '-')) for s in src]
        )
        tgt_html = build_html_table(
            f"Target Tables ({len(tgt)} tabel)",
            ["Nama Tabel", "Kategori"],
            [(t['table_name'], t.get('category', '-')) for t in tgt]
        )
        rel_html = build_html_table(
            f"Detail Relasi ({len(rel_detail)} relasi)",
            ["Source Table", "Target Table"],
            list(rel_detail)
        )

        # Kirim ke LLM hanya untuk ringkasan
        intro_context = f"""
Job: {mentioned_job}
Developer: {stats.get('developers', '-')}
- Jumlah source table: {len(src)}
- Jumlah target table: {len(tgt)}
- Jumlah relationship: {len(rel_detail)}

PENTING: Jangan buat tabel HTML. Semua tabel sudah disiapkan.
Tugas: Buat hanya 2-3 kalimat ringkasan tentang job ini secara keseluruhan.
"""

        client = Groq(api_key=settings.GROQ_API_KEY)
        llm_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": intro_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = llm_response.choices[0].message.content
        answer = llm_intro + "<br>" + src_html + tgt_html + rel_html
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": mentioned_job})

    elif intent == 'source_tables':
        if mentioned_job:
            from groq import Groq
            from django.conf import settings

            stats = job_stats.get(mentioned_job, {})
            src = stats.get('source_tables', [])

            # Build tabel di Python
            src_html = build_html_table(
                f"Source Tables — {mentioned_job} ({len(src)} tabel)",
                ["Nama Tabel", "Kategori"],
                [(s['table_name'], s.get('category', '-')) for s in src]
            )

            # Kirim ke LLM hanya untuk kalimat pembuka
            intro_context = f"""
Job: {mentioned_job}
Developer: {stats.get('developers', '-')}
Jumlah source table: {len(src)}

PENTING: Jangan buat tabel HTML. Tabel sudah disiapkan.
Tugas: Buat hanya 1-2 kalimat pembuka tentang source table job ini.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": intro_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = llm_response.choices[0].message.content
            answer = llm_intro + "<br>" + src_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job})
        else:
            specific_context = f"{DB_SCHEMA}\nPERTANYAAN: {question}\nTidak ada job spesifik. Semua job: {[j['job_name'] for j in all_jobs]}\nTugas: Minta user menyebutkan nama job yang dimaksud."

    elif intent == 'target_tables':
        if mentioned_job:
            from groq import Groq
            from django.conf import settings

            stats = job_stats.get(mentioned_job, {})
            tgt = stats.get('target_tables', [])

            # Build tabel di Python
            tgt_html = build_html_table(
                f"Target Tables — {mentioned_job} ({len(tgt)} tabel)",
                ["Nama Tabel", "Kategori"],
                [(t['table_name'], t.get('category', '-')) for t in tgt]
            )

            # Kirim ke LLM hanya untuk kalimat pembuka
            intro_context = f"""
Job: {mentioned_job}
Developer: {stats.get('developers', '-')}
Jumlah target table: {len(tgt)}

PENTING: Jangan buat tabel HTML. Tabel sudah disiapkan.
Tugas: Buat hanya 1-2 kalimat pembuka tentang target table job ini.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": intro_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = llm_response.choices[0].message.content
            answer = llm_intro + "<br>" + tgt_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job})
        else:
            specific_context = f"{DB_SCHEMA}\nPERTANYAAN: {question}\nSemua job: {[j['job_name'] for j in all_jobs]}\nTugas: Minta user menyebutkan nama job."

    elif intent == 'developer_info':
        if mentioned_job:
            from groq import Groq
            from django.conf import settings

            stats = job_stats.get(mentioned_job, {})

            # Build tabel developer di Python
            devs = stats.get('developers', ['Belum ada developer'])
            dev_rows = [(d,) for d in devs]  # WAJIB tuple dengan koma
            dev_html = build_html_table(
                f"Developer - {mentioned_job}",
                ["Nama Developer"],
                dev_rows
            )

            # LLM hanya buat narasi
            dev_context = f"""
Job: {mentioned_job}
Developer: {devs}
Total source table: {stats.get('total_source_tables', 0)}
Total target table: {stats.get('total_target_tables', 0)}
Total relationship: {stats.get('total_relationships', 0)}

Tugas: Jawab siapa developer/PIC dari job ini dalam 1-2 kalimat.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": dev_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = llm_response.choices[0].message.content
            answer = llm_intro + "<br>" + dev_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job})
        else:
            # Tampilkan semua developer
            from groq import Groq
            from django.conf import settings

            all_devs = list(JobDeveloper.objects.values(
                'developer_name', 'department', 'team'
            ))

            # Build tabel semua developer di Python
            dev_list_html = build_html_table(
                f"Semua Developer ({len(all_devs)} orang)",
                ["Nama", "Departemen", "Tim"],
                [(d.get('developer_name', '-'), d.get('department', '-'), d.get('team', '-'))
                 for d in all_devs]
            )

            # LLM hanya buat narasi
            dev_context = f"""
Semua developer yang terdaftar: {len(all_devs)} orang

Tugas: Tampilkan dalam 1-2 kalimat bahwa ada {len(all_devs)} developer yang terdaftar.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": dev_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = llm_response.choices[0].message.content
            answer = llm_intro + "<br>" + dev_list_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job})

    elif intent == 'job_status':
        from groq import Groq
        from django.conf import settings

        if mentioned_job:
            # Status untuk job spesifik
            job_session = next(
                (s for s in all_sessions if s['job_name'] == mentioned_job),
                None
            )
            job_fail = next(
                (f for f in all_failures if f['job__job_name'] == mentioned_job),
                None
            )

            # Build tabel status di Python
            status_data = [
                ("Nama Job", mentioned_job),
                ("Status Upload", job_session['current_status'] if job_session else "Belum diupload"),
                ("Waktu Upload", job_session['upload_time'] if job_session and job_session.get('upload_time') else "-"),
                ("Jumlah Gagal", str(job_fail['fail_count']) if job_fail else "0")
            ]
            status_html = build_html_table(
                f"Status Upload - {mentioned_job}",
                ["Field", "Nilai"],
                status_data
            )

            # LLM hanya buat narasi
            status_context = f"""
Job: {mentioned_job}
Status: {job_session['current_status'] if job_session else 'Belum diupload'}
Jumlah gagal: {job_fail['fail_count'] if job_fail else 0}

Tugas: Jawab pertanyaan status dalam 1-2 kalimat.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""
        else:
            # Status semua job
            # Build tabel semua status di Python
            status_rows = []
            for j in all_jobs:
                jname = j['job_name']
                sess = next((s for s in all_sessions if s['job_name'] == jname), None)
                fail = next((f for f in all_failures if f['job__job_name'] == jname), None)
                status_rows.append((
                    jname,
                    sess['current_status'] if sess else "Belum diupload",
                    str(fail['fail_count']) if fail else "0"
                ))

            status_html = build_html_table(
                f"Status Upload Semua Job ({len(all_jobs)} job)",
                ["Nama Job", "Status", "Gagal"],
                status_rows
            )

            # LLM hanya buat narasi
            status_context = f"""
Total job: {len(all_jobs)}
Job dengan status failed: {len([s for s in all_sessions if s.get('current_status') and 'fail' in s['current_status'].lower()])}
Job paling sering gagal: {[f['job__job_name'] for f in all_failures[:3]] if all_failures else 'Tidak ada'}

Tugas: Jawab pertanyaan status dalam 2-3 kalimat.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""

        client = Groq(api_key=settings.GROQ_API_KEY)
        llm_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": status_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = llm_response.choices[0].message.content
        answer = llm_intro + "<br>" + status_html
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": mentioned_job})

    elif intent == 'relationship_info':
        from groq import Groq
        from django.conf import settings

        # Build ringkasan relationship di Python
        job_rel_summary = [
            {
                'job': k,
                'jumlah_relasi': v['total_relationships'],
                'jumlah_source': v['total_source_tables'],
                'jumlah_target': v['total_target_tables']
            }
            for k, v in sorted(job_stats.items(),
                                key=lambda x: x[1]['total_relationships'],
                                reverse=True)
        ]

        rel_summary_html = build_html_table(
            f"Ringkasan Relationship ({len(all_relationships)} relasi)",
            ["Nama Job", "Relasi", "Source", "Target"],
            [(r['job'], r['jumlah_relasi'], r['jumlah_source'], r['jumlah_target'])
             for r in job_rel_summary[:15]]
        )

        # LLM hanya buat narasi
        rel_context = f"""
Total relationship di database: {len(all_relationships)}
Total job: {len(all_jobs)}
Job dengan relasi paling banyak: {[r['job'] for r in job_rel_summary[:3]]}

Tugas: Jawab pertanyaan tentang relationship dalam 2-3 kalimat.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""

        client = Groq(api_key=settings.GROQ_API_KEY)
        llm_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": rel_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = llm_response.choices[0].message.content
        answer = llm_intro + "<br>" + rel_summary_html
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": mentioned_job})

    elif intent in ['list_data', 'job_detail']:
        from groq import Groq
        from django.conf import settings

        if mentioned_job:
            # Detail untuk job spesifik - sudah ada di job_detail
            stats = job_stats.get(mentioned_job, {})
            devs = stats.get('developers', ['Belum ada developer'])
            status = next((s['current_status'] for s in all_sessions
                           if s['job_name'] == mentioned_job), 'Belum diupload ke bot')

            # Build tabel detail job di Python menggunakan build_detail_table
            detail_html = build_detail_table(
                mentioned_job,
                [
                    ('Developer', ', '.join(stats.get('developers', ['Belum ada developer']))),
                    ('Total Source Table', str(stats.get('total_source_tables', 0))),
                    ('Total Target Table', str(stats.get('total_target_tables', 0))),
                    ('Total Relasi', str(stats.get('total_relationships', 0))),
                    ('Status Upload', status),
                ]
            )

            # LLM hanya buat 1 kalimat ringkasan
            intro_context = f"""
Job: {mentioned_job}
Developer: {', '.join(stats.get('developers', []))}
Total source: {stats.get('total_source_tables', 0)}
Total target: {stats.get('total_target_tables', 0)}
Total relasi: {stats.get('total_relationships', 0)}
Status: {status}

Tugas: Buat 1 kalimat ringkasan singkat tentang job ini.
JANGAN buat tabel. Tabel sudah disiapkan terpisah.
"""
            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": intro_context}
                ],
                temperature=0.1,
                max_tokens=200
            )
            llm_intro = llm_response.choices[0].message.content
            answer = llm_intro + "<br>" + detail_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job})

        # List semua job (untuk intent list_data)
        job_full_summary = [
            {
                'job_name': k,
                'developers': v['developers'],
                'total_source': v['total_source_tables'],
                'total_target': v['total_target_tables'],
                'total_relasi': v['total_relationships'],
                'status_upload': next(
                    (s['current_status'] for s in all_sessions if s['job_name'] == k),
                    'Belum diupload'
                )
            }
            for k, v in job_stats.items()
        ]

        # Build tabel semua job di Python
        job_list_html = build_html_table(
            f"Semua Job ({len(all_jobs)} job)",
            ["Nama Job", "Developer", "Source", "Target", "Relasi", "Status"],
            [(j['job_name'], ", ".join(j['developers'][:2]),
              j['total_source'], j['total_target'], j['total_relasi'],
              j['status_upload'])
             for j in job_full_summary]
        )

        # LLM hanya buat narasi
        job_list_context = f"""
Total job: {len(all_jobs)}
Total tabel: {len(all_tables)}
Total relationship: {len(all_relationships)}

Tugas: Jawab pertanyaan dalam 2-3 kalimat tentang jumlah job/tabel/relasi.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""
        client = Groq(api_key=settings.GROQ_API_KEY)
        llm_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": job_list_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = llm_response.choices[0].message.content
        answer = llm_intro + "<br>" + job_list_html
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": mentioned_job})

    else:
        # General / ETL concepts - Jawab natural tanpa dump data
        specific_context = f"""
Pertanyaan user: "{question}"

Info sistem (gunakan HANYA jika benar-benar relevan):
- Total job: {len(all_jobs)}
- Total tabel: {len(all_tables)}
- Total relasi: {len(all_relationships)}

Tugas: Jawab pertanyaan ini secara natural sesuai konteksnya.
- Pertanyaan umum/konsep → jawab dari pengetahuan LLM
- Butuh data spesifik → minta user lebih spesifik
JANGAN mengulang jawaban dari percakapan sebelumnya.
JANGAN tampilkan tabel jika tidak diminta eksplisit.
"""

    # ============================================================
    # STEP 6: KIRIM KE GROQ
    # ============================================================
    # Tambahkan job context header agar Groq tahu job yang sedang dibahas
    if mentioned_job:
        job_context_header = f"""
!! KONTEKS AKTIF: Percakapan saat ini sedang membahas job '{mentioned_job}'.
Jika pertanyaan tidak menyebut job lain secara eksplisit,
SEMUA pertanyaan diasumsikan tentang job '{mentioned_job}'.
Jangan minta user menyebutkan nama job lagi.
"""
        specific_context = job_context_header + "\n" + specific_context
    from groq import Groq
    from django.conf import settings

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """Kamu adalah AI Assistant untuk tim Data Engineer dan ETL Analyst.
Gunakan Bahasa Indonesia yang profesional namun tidak kaku.
Seperti rekan kerja senior yang menjelaskan sesuatu kepada timnya.

GAYA BAHASA:
- Langsung ke inti jawaban, tidak bertele-tele
- Boleh memberi interpretasi singkat dari data yang ada
- Jangan mulai dengan "Berdasarkan data yang diberikan..."
- Kalau data tidak ada, katakan: "Data ini belum tersedia di sistem."
- Untuk pertanyaan umum ETL/data engineering, jawab bebas dan edukatif

FORMAT OUTPUT (WAJIB HTML, BUKAN MARKDOWN):
- Nama job dan tabel selalu dalam tag <code>
- List gunakan <ul><li> atau <ol><li>
- Tabel gunakan <table class="table table-bordered table-striped table-sm">
- Semua tabel dibungkus <div style="overflow-x:auto">...</div>
- Judul section gunakan <strong> atau <h6>
- JANGAN pakai **, *, ##, atau | --- | (markdown)

FORMAT JOB DETAIL (WAJIB):
Saat menampilkan informasi satu job, gunakan format HTML ini:
<h6><code>NAMA_JOB</code></h6>
<table class='table table-bordered table-sm' style='max-width:500px'>
  <thead><tr><th>Field</th><th>Keterangan</th></tr></thead>
  <tr><td>Developer</td><td>...</td></tr>
  <tr><td>Total Source Table</td><td>...</td></tr>
  <tr><td>Total Target Table</td><td>...</td></tr>
  <tr><td>Total Relasi</td><td>...</td></tr>
  <tr><td>Status Upload</td><td>...</td></tr>
</table>
<p>Penjelasan singkat 1-2 kalimat tentang job ini.</p>

Jangan campur informasi beberapa job dalam satu paragraf.
Jangan buat perbandingan kecuali user meminta perbandingan.
Jika user hanya menyebut satu job, tampilkan info job itu saja.
Jangan tambahkan informasi job lain yang tidak ditanyakan."""
                },
                {
                    "role": "user",
                    "content": specific_context
                }
            ],
            temperature=0.1,
            max_tokens=4000
        )

        answer = response.choices[0].message.content

        # GABUNGKAN LLM response dengan HTML tables
        return JsonResponse({
            'success': True,
            'answer': answer,
            'intent': intent,
            'mentioned_job': mentioned_job
        })

    except Exception as e:
        import traceback
        print("=" * 50)
        print("CHATBOT EXCEPTION DETAILS:")
        print("Exception Type:", type(e).__name__)
        print("Exception Message:", str(e))
        print("Full Traceback:")
        traceback.print_exc()
        print("=" * 50)
        return JsonResponse({
            'success': False,
            'answer': f"Debug error: {type(e).__name__}: {str(e)}",
            'intent': 'error',
            'mentioned_job': None
        })


@require_http_methods(["POST"])
def chatbot_clear(request):
    """
    Clear chat history.
    POST request
    """
    try:
        return JsonResponse({
            'success': True,
            'message': 'Chat history cleared'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })