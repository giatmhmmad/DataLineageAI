"""
Chatbot Views - Django Views for AI Chatbot
"""
import json

import logging
import re
import traceback
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

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


def normalize_llm_markdown(text):
    """
    Fallback konversi markdown dasar -> HTML untuk narasi LLM.

    System prompt Groq sudah menginstruksikan LLM untuk memakai HTML
    (<strong>, <code>, dll) dan JANGAN memakai markdown, tapi LLM tidak
    selalu patuh 100% - kadang tetap mengeluarkan **bold** mentah. Fungsi
    ini menangkap kasus itu di satu titik, dipanggil di semua tempat yang
    mengambil `.choices[0].message.content` dari Groq, supaya perilakunya
    konsisten di seluruh jalur respons chatbot.

    Hanya menangani **bold** (sesuai bug yang dilaporkan). Tidak melakukan
    unescape/parsing HTML apa pun terhadap isi teks, jadi tidak menambah
    permukaan risiko baru dibanding narasi LLM yang sudah langsung
    dirender sebagai HTML oleh frontend.
    """
    if not text:
        return text
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


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


def extract_active_context(conversation_history, all_jobs, all_relationships, all_sessions):
    """
    Analisa history percakapan untuk ekstrak konteks aktif.
    Return dict berisi semua info yang sedang dibahas.
    """
    context = {
        'active_job': None,
        'active_table': None,
        'last_intent': None,
        'last_data': None,
    }

    job_names_sorted = sorted(
        [j['job_name'] for j in all_jobs],
        key=lambda x: len(x),
        reverse=True
    )

    # Scan dari pesan terbaru ke yang lama
    for msg in reversed(conversation_history):
        content_lower = msg['content'].lower()

        # Cari job yang disebut terakhir (hanya dari pesan USER)
        if msg['role'] == 'user' and not context['active_job']:
            for jname in job_names_sorted:
                if jname.lower() in content_lower:
                    context['active_job'] = jname
                    break

        # Cari intent terakhir dari kata kunci
        if msg['role'] == 'user' and not context['last_intent']:
            if any(k in content_lower for k in ['source', 'sumber', 'input']):
                context['last_intent'] = 'source_tables'
            elif any(k in content_lower for k in ['target', 'output', 'hasil']):
                context['last_intent'] = 'target_tables'
            elif any(k in content_lower for k in ['impact', 'dampak', 'terdampak']):
                context['last_intent'] = 'impact_analysis'
            elif any(k in content_lower for k in ['log', 'riwayat', 'upload']):
                context['last_intent'] = 'job_logs'
            elif any(k in content_lower for k in ['developer', 'pic', 'siapa']):
                context['last_intent'] = 'developer_info'

    return context


def matches_any_keyword_wordwise(text_lower, keywords):
    """
    Cocokkan setiap `keywords` sebagai FRASA UTUH (word-boundary), bukan
    substring biasa (`kw in text_lower`).

    Fase: fix Bug S (akar masalah, bukan tambal per-frasa) - root cause asli
    Bug S BUKAN soal ada/tidaknya nama job eksplisit di kalimat, melainkan
    cara `casual_kw` dicocokkan: keyword pendek seperti 'ya' dicocokkan
    dengan `in` (substring), jadi ikut match di dalam kata APA PUN yang
    kebetulan mengandung huruf "ya" berurutan - "saya", "nya", "hanya",
    "banyak", dst - terlepas dari makna kata itu sendiri. Ini yang membuat
    kalimat seperti "saya mau lihat job" (tanpa nama job eksplisit sama
    sekali, jadi fix Bug S sebelumnya - yang hanya memprioritaskan nama job
    eksplisit - tidak menutupnya) tetap salah jatuh ke intent 'casual'.
    Word-boundary (`\\b...\\b`) memastikan 'ya' hanya match kalau berdiri
    sendiri sebagai kata (atau di ujung/awal kalimat), bukan sebagai
    potongan kata lain.
    """
    for kw in keywords:
        pattern = r'\b' + re.escape(kw.strip()) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False


def resolve_question(question, active_context, job_names_sorted):
    """
    Resolve pertanyaan ambigu menggunakan konteks aktif.
    Contoh: "target tablenya apa" -> mengacu ke active_job
    """
    question_lower = question.lower()

    # Referensi ambigu yang merujuk ke konteks sebelumnya
    reference_kw = [
        'nya', 'itu', 'tersebut', 'yang tadi', 'yang pertama',
        'yang sama', 'dia', 'jobnya', 'job itu', 'job tersebut',
        'itu tadi', 'tadi', 'sebelumnya'
    ]

    # Cek apakah pertanyaan mengandung referensi ambigu
    has_reference = any(k in question_lower for k in reference_kw)

    # Cek apakah pertanyaan tidak menyebut job secara eksplisit
    has_explicit_job = any(
        jname.lower() in question_lower
        for jname in job_names_sorted
    )

    # Jika ada referensi ambigu atau tidak ada job eksplisit
    # tapi ada konteks aktif, gunakan konteks aktif
    if (has_reference or not has_explicit_job) and active_context['active_job']:
        return active_context['active_job']

    return None


# ============================================================
# ACTIVE CONTEXT & SESSION MEMORY (Fase: Active Context & Session Memory)
#
# Mekanisme di atas (extract_active_context/resolve_question) menebak ulang
# job aktif dengan scan teks conversation_history setiap request. Fungsi-fungsi
# di bawah ini menggantikan cara itu dengan pendekatan yang lebih reliable:
# backend mengembalikan `active_context` eksplisit di setiap response, client
# menyimpannya dan mengirimkannya balik apa adanya pada request berikutnya,
# sehingga backend tidak perlu menebak ulang dari teks mentah.
#
# extract_active_context/resolve_question TETAP ADA dan dipakai sebagai
# fallback jika client belum mengirim `active_context` (mis. request lama).
# ============================================================

# Kata kunci ordinal untuk referensi ke item list yang baru ditampilkan,
# contoh: "yang pertama", "yang kedua", "yang terakhir"
ORDINAL_KEYWORDS = {
    'pertama': 0,
    'ke-1': 0,
    'ke 1': 0,
    'kedua': 1,
    'ke-2': 1,
    'ke 2': 1,
    'ketiga': 2,
    'ke-3': 2,
    'ke 3': 2,
    'keempat': 3,
    'ke-4': 3,
    'ke 4': 3,
    'kelima': 4,
    'ke-5': 4,
    'ke 5': 4,
    'terakhir': -1,
}

# Pemetaan tipe last_list -> field context mana yang di-set saat resolusi
# ordinal berhasil, dan key mana di tiap item yang dipakai sebagai nilainya.
# Tipe yang tidak terdaftar di sini (mis. 'developers', 'log_entries') tetap
# disimpan di payload untuk kelengkapan state, tapi belum ada intent handler
# yang mengonsumsinya sebagai objek tunggal, jadi resolusi ordinal untuk tipe
# tersebut tidak menghasilkan apa-apa (lihat catatan di laporan akhir).
LIST_TYPE_FIELD_MAP = {
    'target_tables': ('mentioned_table', 'table_name'),
    'source_tables': ('mentioned_table', 'table_name'),
    'jobs': ('mentioned_job', 'job_name'),
    'impacted_jobs': ('mentioned_job', 'job_name'),
    'problem_jobs': ('mentioned_job', 'job_name'),
}


def list_kind(list_obj):
    """
    'job' | 'table' | None - kategori sebuah last_list berdasarkan tipenya.

    Fase: fix Bug K - dipakai untuk melacak last_list JOB dan last_list
    TABLE secara terpisah (bukan satu slot yang saling menimpa), supaya
    menampilkan list source table untuk sebuah job tidak menghapus jejak
    list job yang ditampilkan sebelumnya di percakapan yang sama.
    """
    if not isinstance(list_obj, dict):
        return None
    mapping = LIST_TYPE_FIELD_MAP.get(list_obj.get('type'))
    if not mapping:
        return None
    return 'job' if mapping[0] == 'mentioned_job' else 'table'


# Pola ordinal berbasis angka eksplisit: "nomor 6", "job ke-6", "yang ke-6",
# "ke 6". Dicek sebagai fallback setelah ORDINAL_KEYWORDS (kata "pertama" dst)
# supaya tidak bentrok - kata sudah lebih spesifik dan dicek lebih dulu.
ORDINAL_NUMBER_PATTERN = re.compile(r'\b(?:nomor|no\.?|ke-?)\s*(\d+)\b')

# Fase: fix Bug J - "job 5"/"tabel 5" langsung tanpa kata pemicu eksplisit
# ("nomor"/"no"/"ke-") di antara kata dan angkanya. Anchor WAJIB pada kata
# "job"/"tabel"/"table" tepat sebelum angka supaya tidak salah tangkap angka
# yang jadi bagian dari nama job/tabel itu sendiri (mis. "V2", "H1",
# "TEST_1"): angka di nama job selalu menempel ke token lain lewat "_"
# (jadi bukan match `\d+` yang berdiri sendiri persis setelah kata "job"/
# "tabel" + spasi), dan tidak ada satu pun job/tabel di database ini yang
# literally mengandung kata "job"/"tabel"/"table" (dicek manual saat audit).
# Selain itu, mentioned_job hasil MATCH PERSIS nama job sudah diresolve di
# STEP 3 SEBELUM fungsi ini pernah dipanggil (lihat guard `if not
# mentioned_job` di chatbot_ask) - jadi pola ini hanya sempat aktif kalau
# pertanyaan memang tidak menyebut nama job/tabel yang valid secara penuh.
ORDINAL_NUMBER_ANCHORED_PATTERN = re.compile(
    r'\b(?:job|tabel|table)\s*(?:nomor|no\.?|ke-?)?\s*(\d+)\b'
)


def resolve_ordinal_index(question_lower):
    """
    Deteksi referensi ordinal di pertanyaan - baik berbasis kata ('yang
    pertama', 'yang kedua', dst) maupun angka eksplisit ('nomor 6', 'ke-6',
    atau langsung 'job 6'/'tabel 6').
    Return index (0-based) atau None jika tidak ada referensi ordinal.
    """
    for kw, idx in ORDINAL_KEYWORDS.items():
        # Fase: fix Bug Q - kw seperti 'ke 2'/'ke-2' berakhir dengan sebuah
        # digit. Dulu dicocokkan dengan substring biasa (`kw in
        # question_lower`), jadi "ke 2" ikut match sebagai substring dari
        # "ke 21"/"ke 25"/dst (angka dua digit apa pun yang KEBETULAN
        # diawali digit yang sama) - "ke" + digit itu terlanjur ketemu
        # duluan SEBELUM ORDINAL_NUMBER_PATTERN sempat menangkap angka
        # penuhnya. Sekarang butuh negative lookahead `(?!\d)` supaya
        # digit di akhir kw TIDAK boleh diikuti digit lain - "ke 2" cuma
        # match kalau memang berdiri sendiri (mis. "ke 2 saja"), bukan
        # prefix dari angka yang lebih panjang.
        if re.search(re.escape(kw) + r'(?!\d)', question_lower):
            return idx
    match = ORDINAL_NUMBER_PATTERN.search(question_lower)
    if not match:
        match = ORDINAL_NUMBER_ANCHORED_PATTERN.search(question_lower)
    if match:
        n = int(match.group(1))
        if n >= 1:
            return n - 1
    return None


def build_last_list(list_type, items, max_items=None):
    """
    Bangun representasi ringkas dari list yang baru saja ditampilkan ke user,
    supaya follow-up question seperti 'yang pertama' bisa di-resolve ke item
    di dalamnya. `items` harus berupa list of dict.

    Fase: fix Bug M - default TIDAK memotong (max_items=None). Sebelumnya
    default 20 diam-diam memotong list yang disimpan di sini padahal
    build_html_table yang menampilkannya ke user TIDAK punya limit apa pun -
    akibatnya ordinal ke item paling akhir dari list > 20 item (mis. index
    21 dari 21 job, atau index 55 dari 55 source table) selalu dilaporkan
    "out of range" walau itemnya jelas ada dan tampil penuh di layar.
    `max_items` tetap tersedia sebagai override eksplisit kalau suatu saat
    memang perlu membatasi ukuran payload active_context untuk list yang
    sangat besar - tapi HARUS disertai pemotongan yang sama pada tabel HTML
    yang ditampilkan, supaya list yang disimpan selalu persis sama dengan
    yang dilihat user.
    """
    if not items:
        return None
    items = list(items)
    if max_items is not None:
        items = items[:max_items]
    return {'type': list_type, 'items': items}


# Kata kunci generik "semua/seluruh job" - dipakai sebagai guard bersama di
# semua intent yang punya makna ganda per-job vs semua-job (Fase: fix Bug E).
# Sebelumnya hanya ada di impact_analysis (Fase 1B); sekarang di-extract jadi
# helper reusable dan dipasang juga di job_logs, developer_info, job_status,
# source_tables, target_tables.
AGGREGATE_ALL_JOBS_KW = [
    'semua job', 'seluruh job', 'setiap job', 'tiap job',
    'semua jobnya', 'job-job', 'untuk semua job', 'semua joblah',
]



# Fase: fix Bug G - whitelist SATU tempat untuk intent yang BOLEH menyuntik
# `active_job_info` (KONTEKS AKTIF PERCAKAPAN...) ke prompt narasi LLM.
# Sebelumnya active_job_info selalu dibangun kalau `mentioned_job` terisi,
# lalu tiap handler intent yang TIDAK butuh job spesifik (greeting, casual,
# confused, capability, list_data) harus ingat sendiri untuk TIDAK
# memakainya - beberapa sudah ditambal (job_failure/developer_info agregat/
# dst, lihat komentar "Fase: fix Bug F"), tapi greeting/casual/confused/
# capability belum, makanya sapaan biasa masih bisa membocorkan nama job
# aktif dari active_context lama (Bug G). Aturan generik: intent yang TIDAK
# ada di whitelist ini TIDAK PERNAH dapat active_job_info, apa pun state
# active context saat itu - default aman untuk intent baru di masa depan.
INTENTS_ALLOW_ACTIVE_JOB_INFO = {
    'job_detail', 'impact_analysis', 'job_logs', 'source_tables',
    'target_tables', 'developer_info', 'job_status', 'relationship_info',
    'general',
}


def is_aggregate_all_jobs_query(question_lower):
    """
    Deteksi apakah pertanyaan secara eksplisit minta data GABUNGAN/SEMUA job,
    bukan follow-up ke job aktif tertentu dari active context. Kalau True,
    handler harus mengabaikan mentioned_job dan pakai jalur agregat -
    jangan diam-diam menjawab untuk 1 job saja.
    """
    return any(k in question_lower for k in AGGREGATE_ALL_JOBS_KW)


def compute_direct_job_impact(job_name):
    """
    Hitung dampak SATU LEVEL untuk `job_name`: tabel yang jadi OUTPUT job
    ini, dan job LAIN (exact match nama, case-insensitive - BUKAN substring
    match) yang memakai salah satu tabel itu sebagai INPUT.

    Fase: fix Bug O - satu-satunya implementasi perhitungan "job terdampak
    langsung", dipakai baik oleh impact_analysis mode single-job maupun
    mode aggregate, supaya keduanya tidak mungkin lagi menghasilkan angka
    berbeda untuk job yang sama. Root cause bug sebelumnya: versi
    single-job memakai substring match (`job_name in r['job_name']`) untuk
    mengenali "diri sendiri" dan meng-exclude-nya dari daftar terdampak -
    itu salah tangkap job LAIN yang kebetulan namanya diawali nama job ini
    (mis. job "CDP_DMT_WHL_EALCO_DLY_H0" salah menganggap
    "CDP_DMT_WHL_EALCO_DLY_H0_TEST1" sebagai dirinya sendiri, karena nama
    yang lebih pendek adalah substring dari yang lebih panjang), sehingga
    job seperti itu ikut ter-exclude dari daftar "job terdampak" padahal
    sebenarnya job yang benar-benar berbeda. Versi aggregate sudah benar
    dari awal (exact match `==`/`!=`) - itu sebabnya exact match itu yang
    sekarang jadi satu-satunya implementasi, dipakai di kedua mode.

    Fase: performa (Task 4.1) - sebelumnya fungsi ini menerima `all_relationships`
    (list Python HASIL PRELOAD SELURUH tabel Relationship) dan memfilternya di
    Python. Sekarang melakukan query TERTARGET sendiri (WHERE job_name = ...,
    lalu WHERE table1 IN (...)) - jadi dipanggil untuk 1 job, cuma menyentuh
    baris yang relevan untuk job itu, bukan seluruh dataset. Ini yang
    membuat mode single-job DAN aggregate (loop per job bermasalah)
    sama-sama tidak perlu lagi memuat all_relationships secara penuh.

    Return (output_tables: set, impacted_jobs: dict {job_name: via_table}).
    """
    from .models import Relationship

    output_tables = set(
        Relationship.objects.filter(job_name__iexact=job_name)
        .exclude(table2__table_name__isnull=True)
        .values_list('table2__table_name', flat=True)
    )

    impacted_jobs = {}
    if output_tables:
        rows = (
            Relationship.objects
            .filter(table1__table_name__in=output_tables)
            .exclude(job_name__iexact=job_name)
            .values('job_name', 'table1__table_name')
        )
        for r in rows:
            impacted_jobs[r['job_name']] = r['table1__table_name']

    return output_tables, impacted_jobs


# ============================================================
# LIST_DATA PAGINATION + FILTER (Fase: performa, Task 4.1)
#
# "Semua job" tidak lagi memuat SELURUH job ke Python lalu di-slice - query
# DB langsung pakai LIMIT/OFFSET (page_size default 20, didiskusikan dan
# dikonfirmasi user), plus filter dasar (tabel/developer/status "belum
# diupload") diterapkan sebagai klausa WHERE, bukan filter Python di atas
# data yang sudah di-load penuh.
# ============================================================

LIST_DATA_PAGE_SIZE = 20

# Frasa "lanjut ke halaman berikutnya" - HANYA diinterpretasikan sebagai
# page-advance kalau active_context punya last_list_job dengan page_info
# aktif (lihat pengecekan di chatbot_ask). Tanpa itu, kata-kata ini tetap
# berperilaku seperti sebelumnya (mis. "lanjut" tetap masuk casual_kw/
# context_reset_kw seperti biasa) - TIDAK ada perubahan perilaku untuk
# kasus tanpa list berpaginasi aktif.
LIST_DATA_NEXT_PAGE_KW = [
    'lanjut', 'selanjutnya', 'halaman berikutnya', 'halaman selanjutnya',
    'lihat lebih banyak', 'lihat selanjutnya', 'next page', 'more job',
]

# Fase: fix Bug T - "tampilkan ulang dari halaman pertama"/"halaman 1"/
# "dari awal" adalah permintaan RESET PAGINATION (balik ke halaman 1 dari
# list job yang SAMA), bukan referensi ordinal ke item urutan ke-1. Kata
# "pertama" ada di ORDINAL_KEYWORDS (idx=0), jadi harus dicek dan
# di-handle DI SINI, SEBELUM resolve_ordinal_index/resolve_from_active_context
# sempat menangkapnya sebagai ordinal item biasa - kalau tidak, "halaman
# pertama" pada list yang sedang di halaman 2 salah diterjemahkan jadi
# "item nomor 1" (yang letaknya di halaman SEBELUMNYA, di luar jangkauan
# halaman yang sedang dilacak) dan dijawab pesan out-of-range yang keliru.
# "halaman pertaman" (typo umum yang ditemukan saat testing) sengaja
# didaftarkan literal di sini, bukan lewat fuzzy matching - typo tunggal ini
# yang sudah terbukti terjadi, bukan alasan untuk membangun pencocokan
# fuzzy umum di luar scope bug ini.
PAGE_RESET_KW = [
    'halaman pertama', 'halaman pertaman', 'halaman 1', 'halaman awal',
    'dari awal',
]


def detect_list_data_filters(question_lower, table_names_sorted, developer_names_sorted):
    """
    Deteksi filter dasar untuk intent list_data langsung dari teks
    pertanyaan yang MEMICU intent ini.

    Catatan penting soal cakupan: kata status seperti "gagal"/"berhasil"
    SUDAH diklaim intent job_status lebih dulu di urutan pengecekan STEP 4
    (status_kw dicek sebelum list_kw dalam if/elif chain yang sama) -
    kalau pertanyaan mengandung kata itu, intent yang terdeteksi tidak
    pernah 'list_data', jadi filter status semacam itu tidak akan pernah
    sampai ke fungsi ini walau didukung di sini. Menambahkannya berarti
    mengubah prioritas intent yang sudah PASS (di luar scope task ini).
    Yang aman dideteksi di sini karena tidak bentrok kata kunci intent lain
    manapun: nama tabel/developer eksplisit, dan frasa "belum diupload"
    (sengaja tidak ada di status_kw manapun).
    """
    filters = {'table': None, 'developer': None, 'no_session': False}

    for tname in table_names_sorted:
        if tname.lower() in question_lower:
            filters['table'] = tname
            break

    for dname in developer_names_sorted:
        if dname and dname.lower() in question_lower:
            filters['developer'] = dname
            break

    if any(k in question_lower for k in
           ('belum diupload', 'belum upload', 'belum di upload', 'belum di-upload')):
        filters['no_session'] = True

    return filters


def apply_list_data_filters(queryset, filters, all_sessions):
    """
    Terapkan filter list_data ke QuerySet JobDetail di level DATABASE.
    """
    from .models import Relationship
    from django.db.models import Q

    if filters.get('table'):
        job_names = (
            Relationship.objects
            .filter(Q(table1__table_name__icontains=filters['table']) |
                    Q(table2__table_name__icontains=filters['table']))
            .values_list('job_name', flat=True).distinct()
        )
        queryset = queryset.filter(job_name__in=list(job_names))

    if filters.get('developer'):
        queryset = queryset.filter(
            developers__developer_name__icontains=filters['developer']
        ).distinct()

    if filters.get('no_session'):
        # "Belum diupload ke bot" = job tidak punya baris JobUploadSessions
        # sama sekali (lihat default value di build job_full_summary lama).
        # all_sessions sudah dimuat di STEP 1 (bot_eda, DB terpisah) - tidak
        # bisa di-JOIN lintas-DB langsung, jadi exclude pakai daftar nama
        # job yang sudah ada session (di Python, dari data yang sudah di
        # tangan, bukan query baru).
        sessions_job_names = {s['job_name'] for s in all_sessions}
        if sessions_job_names:
            queryset = queryset.exclude(job_name__in=list(sessions_job_names))

    return queryset


def render_job_list_page(offset, filters, active_context_in, all_sessions):
    """
    Bangun 1 halaman list_data (job) langsung dari DB dengan LIMIT/OFFSET,
    dipakai baik untuk permintaan list_data awal (offset=0) maupun follow-up
    "lanjut ke halaman berikutnya".

    Statistik source/target/relasi dihitung dengan query TERTARGET, dibatasi
    ke job_name yang ada di HALAMAN INI saja (biasanya <= page_size), bukan
    seluruh dataset.
    """
    from .models import JobDetail, Relationship
    from django.conf import settings

    page_size = LIST_DATA_PAGE_SIZE
    qs = apply_list_data_filters(
        JobDetail.objects.all().order_by('job_name'), filters, all_sessions
    )

    total_count = qs.count()
    page_jobs = list(qs.prefetch_related('developers')[offset:offset + page_size])
    page_job_names = [j.job_name for j in page_jobs]

    rels_by_job = {}
    for r in Relationship.objects.filter(job_name__in=page_job_names).values(
        'job_name', 'table1__table_name', 'table2__table_name'
    ):
        rels_by_job.setdefault(r['job_name'], []).append(r)

    job_full_summary = []
    for j in page_jobs:
        rels = rels_by_job.get(j.job_name, [])
        src = {r['table1__table_name'] for r in rels if r['table1__table_name']}
        tgt = {r['table2__table_name'] for r in rels if r['table2__table_name']}
        # .all() (bukan .values_list()) supaya pakai cache prefetch_related
        # di qs.prefetch_related('developers') di atas - lihat catatan N+1
        # yang sama di STEP 1 (Fase: performa, Task 4.1).
        devs = [d.developer_name for d in j.developers.all()] or ['Belum ada developer']
        status = next(
            (s['current_status'] for s in all_sessions if s['job_name'] == j.job_name),
            'Belum diupload'
        )
        job_full_summary.append({
            'job_name': j.job_name,
            'developers': devs,
            'total_source': len(src),
            'total_target': len(tgt),
            'total_relasi': len(rels),
            'status_upload': status,
        })

    filter_desc_parts = []
    if filters.get('table'):
        filter_desc_parts.append(f'pakai tabel mengandung "{filters["table"]}"')
    if filters.get('developer'):
        filter_desc_parts.append(f'developer mengandung "{filters["developer"]}"')
    if filters.get('no_session'):
        filter_desc_parts.append('belum diupload ke bot')
    filter_desc = (' (filter: ' + '; '.join(filter_desc_parts) + ')') if filter_desc_parts else ''

    page_start = offset + 1 if total_count else 0
    page_end = min(offset + page_size, total_count)

    job_list_html = build_html_table(
        f"Job{filter_desc} - item {page_start}-{page_end} dari {total_count}",
        ["Nama Job", "Developer", "Source", "Target", "Relasi", "Status"],
        [(j['job_name'], ", ".join(j['developers'][:2]),
          j['total_source'], j['total_target'], j['total_relasi'],
          j['status_upload'])
         for j in job_full_summary]
    )

    has_more = page_end < total_count
    if has_more:
        job_list_html += f"""
<div style='margin-top:10px'>
<button onclick="document.getElementById('chatInput').value='lihat halaman berikutnya';
                document.getElementById('chatInput').focus()"
        style='background:white;border:1px solid #dee2e6;border-radius:16px;
               padding:6px 14px;font-size:0.85rem;cursor:pointer;transition:all 0.2s'
        onmouseover="this.style.background='#0d6efd';this.style.color='white'"
        onmouseout="this.style.background='white';this.style.color='inherit'">
Lihat halaman berikutnya ({total_count - page_end} job lagi)
</button>
</div>"""

    job_list_context = f"""
Total job{filter_desc}: {total_count}
Menampilkan item {page_start} sampai {page_end} dari total {total_count}.

Tugas: Jawab dalam 1-2 kalimat tentang jumlah job yang ditemukan{" sesuai filter" if filter_desc_parts else ""}.
JANGAN mulai dengan basa-basi seperti "terima kasih atas informasinya".
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""
    client = get_groq_client()
    llm_response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
            {"role": "user", "content": job_list_context}
        ],
        temperature=0.1,
        max_tokens=200
    )
    llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
    answer = llm_intro + "<br>" + job_list_html

    last_list = {
        'type': 'jobs',
        'items': [{'job_name': j['job_name']} for j in job_full_summary],
        'page_info': {
            'offset': offset,
            'page_size': page_size,
            'total_count': total_count,
            'filters': filters,
        },
    }

    return JsonResponse({
        "answer": answer,
        "intent": "list_data",
        "mentioned_job": None,
        "active_context": build_active_context_payload(
            None, None, {}, all_sessions, last_list, active_context_in
        ),
    })


def resolve_from_active_context(question_lower, active_context_in, job_names_sorted, table_names_sorted):
    """
    Resolusi pertanyaan follow-up menggunakan `active_context` yang dikirim
    EKSPLISIT oleh client (bukan ditebak ulang dari conversation_history mentah
    seperti extract_active_context/resolve_question).

    Return dict {'mentioned_job': ..., 'mentioned_table': ...} atau None kalau
    tidak ada yang bisa di-resolve.
    """
    if not active_context_in or not isinstance(active_context_in, dict):
        return None

    result = {
        'mentioned_job': None, 'mentioned_table': None,
        'out_of_range_message': None, 'clarification_message': None,
        'ordinal_resolved': False,
    }

    # 1) Referensi ordinal ("yang pertama", dst) terhadap list terakhir yang
    #    ditampilkan - prioritas tertinggi karena eksplisit menunjuk sebuah item.
    #
    # Fase: fix Bug K - `last_list_job` dan `last_list_table` dilacak
    # TERPISAH (lihat build_active_context_payload/list_kind), jadi kalau
    # percakapan sempat lihat list job LALU lihat list source table untuk
    # salah satu job-nya, keduanya tetap tersimpan independen. Kalau
    # keduanya ada dan pertanyaan tidak jelas merujuk ke yang mana (tidak
    # ada kata "job" atau "tabel"/"table"), JANGAN TEBAK - itu akar
    # penyebab bug lama (selalu ambil list yang paling baru ditampilkan
    # walau beda jenis objek sama sekali). Minta klarifikasi generik.
    ordinal_idx = resolve_ordinal_index(question_lower)
    if ordinal_idx is not None:
        last_list_job = active_context_in.get('last_list_job')
        last_list_table = active_context_in.get('last_list_table')
        has_job_list = isinstance(last_list_job, dict) and last_list_job.get('items')
        has_table_list = isinstance(last_list_table, dict) and last_list_table.get('items')

        wants_job = bool(re.search(r'\bjob\b', question_lower))
        wants_table = any(k in question_lower for k in ('tabel', 'table'))

        candidate = None
        if has_job_list and has_table_list:
            if wants_job and not wants_table:
                candidate = last_list_job
            elif wants_table and not wants_job:
                candidate = last_list_table
            else:
                result['clarification_message'] = (
                    "Nomor itu maksudnya dari daftar yang mana ya - daftar job atau "
                    "daftar tabel yang barusan saya tampilkan? Sebutkan salah satu, "
                    "misalnya \"job nomor 5\" atau \"tabel nomor 5\"."
                )
                return result
        elif has_job_list:
            candidate = last_list_job
        elif has_table_list:
            candidate = last_list_table

        if candidate:
            items = candidate['items']
            mapping = LIST_TYPE_FIELD_MAP.get(candidate.get('type'))
            if mapping:
                field_name, item_key = mapping
                page_info = candidate.get('page_info')

                if page_info:
                    # Fase: fix Bug P - header paginasi (render_job_list_page)
                    # menampilkan nomor ABSOLUT ("item 21-21 dari 21"), jadi
                    # ordinal yang diketik user ("nomor 21") juga ABSOLUT
                    # (posisi di SELURUH list), BUKAN posisi lokal di halaman
                    # ini. `ordinal_idx` dari resolve_ordinal_index sudah
                    # bernilai (nomor-1) - itu sudah index absolut 0-based
                    # yang benar; bug-nya ada di sini, dulu dipakai LANGSUNG
                    # sebagai index ke `items` (yang cuma berisi halaman ini,
                    # mulai dari 0 lagi tiap halaman) tanpa dikurangi offset
                    # dulu. Sekarang dikonversi ke index lokal dulu.
                    offset = page_info.get('offset', 0)
                    total_count = page_info.get('total_count', len(items))

                    if ordinal_idx < 0:
                        # "terakhir" dst (ORDINAL_KEYWORDS) - TIDAK diubah,
                        # tetap berarti item terakhir DI HALAMAN INI (bukan
                        # di seluruh dataset), sesuai perilaku lama yang
                        # tidak dilaporkan bermasalah.
                        try:
                            picked = items[ordinal_idx]
                        except IndexError:
                            picked = None
                        if isinstance(picked, dict) and picked.get(item_key):
                            # Fase: fix Bug S (lanjutan) - tandai resolusi ini
                            # berasal dari referensi ORDINAL EKSPLISIT di
                            # pertanyaan SAAT INI (bukan carry-over/implisit
                            # bagian (2) di bawah). Dipakai di chatbot_ask
                            # supaya kalimat seperti "iya job 19" (ada kata
                            # casual "iya" TAPI juga referensi ordinal
                            # eksplisit "job 19") tidak salah jatuh ke intent
                            # 'casual' - beda dari referensi implisit generik
                            # (mis. "nya" tanpa penyebutan apa pun yang baru)
                            # yang MEMANG harus tetap kalah prioritas dari
                            # greeting/casual (fix regresi Active Context).
                            result['ordinal_resolved'] = True
                            result[field_name] = picked[item_key]
                            return result
                    elif ordinal_idx >= total_count:
                        # Genuinely di luar SELURUH data - Fase: fix Bug D.
                        result['out_of_range_message'] = (
                            f"Tidak ada item ke-{ordinal_idx + 1} - total job di sistem cuma "
                            f"{total_count}. Coba sebutkan nomor 1 sampai {total_count}."
                        )
                        return result
                    else:
                        local_idx = ordinal_idx - offset
                        if 0 <= local_idx < len(items):
                            # Ada di HALAMAN INI - inilah fix Bug P: index
                            # lokal yang benar, bukan ordinal_idx mentah.
                            picked = items[local_idx]
                            if isinstance(picked, dict) and picked.get(item_key):
                                result['ordinal_resolved'] = True
                                result[field_name] = picked[item_key]
                                return result
                        elif local_idx >= len(items):
                            # Ada di dataset, tapi di halaman SETELAH ini
                            # (belum dimuat) - perilaku sudah benar dari
                            # Fase 1F, dipertahankan.
                            result['out_of_range_message'] = (
                                f"Item nomor {ordinal_idx + 1} tidak ada di halaman ini - halaman "
                                f"ini cuma menampilkan item {offset + 1} sampai "
                                f"{offset + len(items)} dari total {total_count}. "
                                f"Ketik \"lanjut ke halaman berikutnya\" untuk melihat item "
                                f"berikutnya, atau sebutkan nama job-nya langsung kalau sudah tahu."
                            )
                            return result
                        else:
                            # local_idx < 0: ada di dataset, tapi di halaman
                            # SEBELUM ini. `last_list_job` cuma melacak
                            # halaman yang SEDANG ditampilkan (bukan riwayat
                            # semua halaman yang pernah dilihat), jadi item
                            # ini tidak bisa langsung di-resolve dari sini -
                            # batasan desain, bukan bug. Pesan jelas supaya
                            # tidak menyesatkan seperti sebelumnya.
                            result['out_of_range_message'] = (
                                f"Item nomor {ordinal_idx + 1} ada di halaman sebelumnya (di luar "
                                f"jangkauan halaman yang sedang saya lacak - saat ini item "
                                f"{offset + 1} sampai {offset + len(items)} dari total "
                                f"{total_count}). Sebutkan nama job-nya langsung kalau sudah "
                                f"tahu, atau minta tampilkan ulang dari halaman pertama."
                            )
                            return result
                else:
                    # List TIDAK berpaginasi (mis. source_tables/target_tables,
                    # Fase: fix Bug M) - len(items) MEMANG seluruh data yang
                    # ada, perilaku lama dipertahankan apa adanya.
                    if ordinal_idx >= 0 and ordinal_idx >= len(items):
                        result['out_of_range_message'] = (
                            f"List terakhir yang saya tampilkan cuma berisi {len(items)} item, "
                            f"jadi tidak ada item ke-{ordinal_idx + 1}. "
                            f"Coba sebutkan nomor 1 sampai {len(items)}."
                        )
                        return result
                    try:
                        picked = items[ordinal_idx]
                    except IndexError:
                        picked = None
                    if isinstance(picked, dict) and picked.get(item_key):
                        result['ordinal_resolved'] = True
                        result[field_name] = picked[item_key]
                        return result

    # 2) Referensi implisit umum ("nya", "itu", "targetnya", dst) tanpa
    #    penyebutan objek baru secara eksplisit -> pakai job/table aktif.
    has_explicit_job = any(jn.lower() in question_lower for jn in job_names_sorted)
    has_explicit_table = any(tn.lower() in question_lower for tn in table_names_sorted)

    if not has_explicit_job and active_context_in.get('last_job_name'):
        result['mentioned_job'] = active_context_in['last_job_name']
    if not has_explicit_table and active_context_in.get('last_table_name'):
        result['mentioned_table'] = active_context_in['last_table_name']

    if result['mentioned_job'] or result['mentioned_table']:
        return result
    return None


def build_active_context_payload(mentioned_job, mentioned_table, job_stats, all_sessions,
                                  last_list=None, active_context_in=None):
    """
    Bangun payload `active_context` yang dikirim balik ke client setelah
    chatbot berhasil menjawab tentang sebuah objek. Client menyimpan ini dan
    mengirimkannya balik apa adanya pada request berikutnya (lihat
    resolve_from_active_context), sehingga backend tidak membuang nilai yang
    sudah dihitungnya sendiri lalu menebaknya ulang dari teks.

    `last_list`: HANYA diisi oleh intent yang menampilkan daftar UTUH dan valid
    untuk resolusi ordinal (list_data, source_tables, target_tables). Kalau
    None (dipanggil dari intent lain seperti impact_analysis/job_logs/
    job_status/relationship_info yang menampilkan tabel ringkasan atau
    agregat parsial), slot last_list LAMA (job maupun table) dari
    `active_context_in` dipertahankan apa adanya - JANGAN ditimpa dengan
    subset/filter yang bukan daftar utuh (Fase: fix Bug D, Opsi A).

    Fase: fix Bug K - last_list disimpan di DUA slot terpisah berdasarkan
    kategorinya (`last_list_job` vs `last_list_table`, lihat `list_kind`),
    bukan satu slot yang saling menimpa. Kalau `last_list` yang baru
    berkategori 'table' (mis. user baru saja lihat source table sebuah
    job), slot `last_list_job` yang lama TETAP dipertahankan supaya
    follow-up ordinal soal job masih bisa di-resolve dengan benar
    (resolve_from_active_context memilih slot yang tepat sendiri).
    """
    prev_job_list = None
    prev_table_list = None
    if active_context_in and isinstance(active_context_in, dict):
        prev_job_list = active_context_in.get('last_list_job')
        prev_table_list = active_context_in.get('last_list_table')

    new_kind = list_kind(last_list)
    if new_kind == 'job':
        last_list_job, last_list_table = last_list, prev_table_list
    elif new_kind == 'table':
        last_list_job, last_list_table = prev_job_list, last_list
    else:
        last_list_job, last_list_table = prev_job_list, prev_table_list

    if not mentioned_job and not mentioned_table and not last_list_job and not last_list_table:
        return None

    last_relationship = None
    last_upload_log = None

    if mentioned_job:
        stats = job_stats.get(mentioned_job, {})
        rels = stats.get('raw_relationships', [])
        if len(rels) == 1:
            r = rels[0]
            last_relationship = {
                'job_name': r.get('job_name'),
                'source_table': r.get('table1__table_name'),
                'target_table': r.get('table2__table_name'),
            }

        session = next((s for s in all_sessions if s['job_name'] == mentioned_job), None)
        if session:
            last_upload_log = {
                'job_name': mentioned_job,
                'current_status': session.get('current_status'),
            }

    return {
        'last_job_name': mentioned_job,
        'last_table_name': mentioned_table,
        'last_relationship': last_relationship,
        'last_upload_log': last_upload_log,
        'last_list_job': last_list_job,
        'last_list_table': last_list_table,
    }


def build_proactive_suggestions(intent, mentioned_job, stats):
    """
    Buat suggestion next action yang relevan setelah menjawab.
    """
    if not mentioned_job:
        return ""

    suggestions = []

    if intent == 'job_detail':
        suggestions = [
            "Lihat source table",
            "Lihat target table",
            "Lihat upload log",
            "Impact analysis jika job ini gagal",
            "Info developer job ini"
        ]
    elif intent == 'source_tables':
        suggestions = [
            "Lihat target table",
            "Impact analysis jika job ini gagal",
            "Lihat upload log"
        ]
    elif intent == 'target_tables':
        suggestions = [
            "Lihat source table",
            "Job mana yang pakai tabel output ini",
            "Impact analysis jika job ini gagal"
        ]
    elif intent == 'impact_analysis':
        suggestions = [
            "Siapa developer yang bertanggung jawab",
            "Lihat upload log job ini",
            "Lihat source table job ini"
        ]
    elif intent == 'job_logs':
        suggestions = [
            "Impact analysis jika job ini gagal",
            "Siapa developer job ini",
            "Lihat source dan target table"
        ]

    if not suggestions:
        return ""

    html = """
<div style='margin-top:16px;padding:12px;
            background:#f8f9fa;border-radius:8px;
            border-left:3px solid #0d6efd'>
<small><strong>💡 Kamu juga bisa tanya:</strong></small>
<div style='margin-top:8px;display:flex;flex-wrap:wrap;gap:6px'>
"""
    for s in suggestions:
        html += f"""
<button onclick="document.getElementById('chatInput').value='{s} {mentioned_job}';
                document.getElementById('chatInput').focus()"
        style='background:white;border:1px solid #dee2e6;
               border-radius:16px;padding:4px 12px;
               font-size:0.8rem;cursor:pointer;
               transition:all 0.2s'
        onmouseover="this.style.background='#0d6efd';this.style.color='white'"
        onmouseout="this.style.background='white';this.style.color='inherit'">
{s}
</button>"""
    html += "</div></div>"
    return html


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
    from django.db.models import Count, Max, Q

    # Jobs dengan nama developer (bukan ID angka).
    # Fase: performa (Task 4.1) - `job.developers.values_list(...)` di bawah
    # SEBELUMNYA memicu N+1 tersembunyi: memanggil .values_list()/.filter()
    # pada related manager SELALU membuat query baru dan TIDAK memakai cache
    # dari prefetch_related (batasan/gotcha Django yang terkenal - hanya
    # `.all()` pada relasi yang di-prefetch yang memakai cache). Ditemukan
    # saat benchmark: 52 query untuk 50 job (1 + 1 prefetch + 50 per-job).
    # Diganti jadi `.all()` (pakai cache prefetch) - 2 query total untuk
    # SELURUH job, apa pun jumlahnya. Urutan nama developer bisa sedikit
    # beda dari sebelumnya untuk job dengan >1 developer (keduanya sama-sama
    # "urutan default DB", tidak pernah ada Meta.ordering eksplisit di
    # JobDeveloper) - cuma memengaruhi urutan tampilan teks, bukan datanya.
    all_jobs_raw = JobDetail.objects.prefetch_related('developers').all()
    all_jobs = []
    for job in all_jobs_raw:
        devs = [d.developer_name for d in job.developers.all()]
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

    # Ambil done time per job (waktu log terakhir dengan status Done).
    # Fase: performa (Task 4.1) - sebelumnya ini N+1 (1 query JobUploadSessions
    # + 1 query JobUploadLogs TERPISAH per session, jadi 1+N query - di skala
    # 1000+ job berarti 1000+ query cuma untuk field ini). Diganti jadi 2 query
    # total: satu Max('update_time') ter-agregasi per job (grup di level DB),
    # digabung dengan all_sessions yang sudah dimuat di atas (tidak query ulang
    # JobUploadSessions). Hasil/shape dict sama persis seperti sebelumnya.
    done_time_by_job = {
        d['job__job_name']: d['done_time']
        for d in JobUploadLogs.objects.using('bot_eda')
            .filter(status__icontains='done')
            .values('job__job_name')
            .annotate(done_time=Max('update_time'))
    }
    sessions_with_done = {
        s['job_name']: {
            'upload_time': s['upload_time'],
            'done_time': done_time_by_job.get(s['job_name']),
            'current_status': s['current_status'],
            'pic_job': s['pic_job'],
        }
        for s in all_sessions
    }

    # Ranking failure
    all_failures = list(
        JobUploadLogs.objects.using('bot_eda')
        .filter(status__icontains='fail')
        .values('job__job_name')
        .annotate(fail_count=Count('log_id'))
        .order_by('-fail_count')
    )

    # Statistik per job dari relationship - exact match + kategori lengkap.
    # Fase: performa (Task 4.1) - sebelumnya untuk SETIAP job dilakukan scan
    # penuh ke SELURUH all_relationships (`[r for r in all_relationships if
    # r['job_name']==jname]`) -> O(jumlah_job x jumlah_relasi). Di skala
    # 1000+ job dengan puluhan ribu relasi ini jadi puluhan-ratusan juta
    # perbandingan Python murni. Diganti jadi satu single-pass pengelompokan
    # relasi per job_name (O(jumlah_relasi)), baru job_stats dibangun dari
    # hasil pengelompokan itu. Hasil/shape job_stats[...] IDENTIK seperti
    # sebelumnya - semua intent yang membaca job_stats tidak perlu berubah.
    rels_by_job = {}
    for r in all_relationships:
        rels_by_job.setdefault(r['job_name'], []).append(r)

    job_stats = {}
    for job in all_jobs:
        jname = job['job_name']
        rels = rels_by_job.get(jname, [])
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

    # Fase: fix Bug S - simpan terpisah bahwa job ini disebut EKSPLISIT di
    # TEKS PERTANYAAN SAAT INI (bukan hasil carry-over dari active context/
    # riwayat percakapan di bawah, yang bisa menimpa `mentioned_job` lagi
    # nanti). Dipakai di STEP 4 supaya pertanyaan yang menyebut nama job
    # valid secara eksplisit tidak pernah salah jatuh ke intent
    # casual/greeting akibat jebakan substring kata seperti "ya" di dalam
    # "saya"/"nya" (lihat casual_kw) - beda dengan mentioned_job hasil
    # carry-over context (mis. dari active_job lama) yang MEMANG harus
    # tetap kalah prioritas dari greeting/casual (lihat fix regresi
    # Active Context sebelumnya).
    explicit_job_in_question = mentioned_job

    # ============================================================
    # RESOLUSI ACTIVE CONTEXT DARI CLIENT (Fase: Active Context & Session Memory)
    # Jalankan SEBELUM fallback lama (extract_active_context/resolve_question).
    # Prioritas: kalau client sudah mengirim active_context eksplisit dan
    # berhasil di-resolve, fallback lama di bawah tidak perlu jalan lagi
    # (mentioned_job/mentioned_table sudah terisi).
    # ============================================================
    try:
        active_context_in = data.get('active_context')
        if not isinstance(active_context_in, dict):
            active_context_in = None
    except Exception:
        active_context_in = None

    table_names_sorted = sorted(
        [t['table_name'] for t in all_tables if t.get('table_name')],
        key=lambda x: len(x),
        reverse=True
    )

    # Daftar nama developer - untuk deteksi filter list_data (Fase: performa,
    # Task 4.1). Tabel JobDeveloper kecil (jumlah developer manusia, bukan
    # proporsional ke jumlah job), jadi query kecil dan cukup dilakukan sekali.
    developer_names_sorted = sorted(
        [d for d in JobDeveloper.objects.values_list('developer_name', flat=True).distinct() if d],
        key=len,
        reverse=True
    )

    # Fase: performa (Task 4.1) - "lanjut ke halaman berikutnya" untuk
    # list_data yang berpaginasi. Dicek SEBELUM deteksi intent normal, tapi
    # HANYA jadi page-advance kalau active_context punya last_list_job DENGAN
    # page_info aktif - kalau tidak ada list berpaginasi aktif, frasa seperti
    # "lanjut" tetap jatuh ke jalur lama (context_reset_kw/casual_kw) tanpa
    # perubahan sama sekali.
    if active_context_in:
        last_list_job_ctx = active_context_in.get('last_list_job')
        has_paginated_job_list = (
            isinstance(last_list_job_ctx, dict) and last_list_job_ctx.get('page_info')
        )
        # Fase: fix Bug T - reset pagination ("halaman pertama"/"halaman 1"/
        # "dari awal") dicek DI SINI, SEBELUM resolve_ordinal_index sempat
        # menangkap kata "pertama" sebagai ordinal item ke-1 (lihat
        # PAGE_RESET_KW). Sama seperti page-advance di bawah, HANYA aktif
        # kalau ada list job berpaginasi aktif.
        if has_paginated_job_list and any(k in question_lower for k in PAGE_RESET_KW):
            page_info = last_list_job_ctx['page_info']
            return render_job_list_page(
                0, page_info.get('filters') or {}, active_context_in, all_sessions
            )
        if (has_paginated_job_list
                and any(k in question_lower for k in LIST_DATA_NEXT_PAGE_KW)):
            page_info = last_list_job_ctx['page_info']
            next_offset = page_info.get('offset', 0) + page_info.get('page_size', LIST_DATA_PAGE_SIZE)
            if next_offset < page_info.get('total_count', 0):
                return render_job_list_page(
                    next_offset, page_info.get('filters') or {}, active_context_in, all_sessions
                )
            # Sudah di halaman terakhir - biarkan lanjut ke deteksi intent
            # normal (mis. "lanjut" tanpa list lagi -> casual "ada lagi?").

    mentioned_table = None
    # Fase: fix Bug S (lanjutan) - True hanya kalau resolusi berhasil lewat
    # referensi ORDINAL EKSPLISIT di pertanyaan SAAT INI (lihat
    # `ordinal_resolved` di resolve_from_active_context), bukan lewat
    # referensi implisit/carry-over ("nya", fallback last_job_name).
    ordinal_resolved_this_turn = False
    if not mentioned_job:
        context_resolution = resolve_from_active_context(
            question_lower, active_context_in, job_names_sorted, table_names_sorted
        )
        if context_resolution:
            # Fase: fix Bug D - index ordinal di luar jangkauan list terakhir.
            # Jawab jujur & jelas di sini, JANGAN lanjut ke intent detection/
            # jalur LLM generik yang bisa menyesatkan ("Data ini belum
            # tersedia di sistem" - seolah datanya memang tidak ada).
            if context_resolution.get('out_of_range_message'):
                # Fase: fix Bug U - referensi ordinal yang gagal (nomor di
                # luar jangkauan) BUKAN pergantian topik, jadi job/tabel aktif
                # yang sedang dibahas TIDAK BOLEH ikut hilang. Sebelumnya
                # dipanggil dengan (None, None) di sini, yang menimpa
                # `last_job_name`/`last_table_name` jadi None walau job aktif
                # sebelumnya valid - follow-up berikutnya yang tidak menyebut
                # job apa pun (mis. "tampilkan ulang") lalu gagal resolve
                # lewat active context (last_job_name sudah kosong) dan jatuh
                # ke fallback lama (extract_active_context/resolve_question)
                # yang scan ulang SELURUH conversation_history dari teks
                # mentah - berpotensi menemukan job yang jauh lebih lama dari
                # yang sebenarnya sedang dibahas. Preserve saja job/tabel aktif
                # yang sudah ada di active_context_in.
                preserved_job = active_context_in.get('last_job_name') if active_context_in else None
                preserved_table = active_context_in.get('last_table_name') if active_context_in else None
                return JsonResponse({
                    'success': True,
                    'answer': f"<p>{context_resolution['out_of_range_message']}</p>",
                    'intent': 'out_of_range',
                    'mentioned_job': None,
                    'active_context': build_active_context_payload(
                        preserved_job, preserved_table, job_stats, all_sessions, None, active_context_in)
                })
            # Fase: fix Bug K - ordinal ambigu (dua jenis list, job & tabel,
            # sama-sama ada, pertanyaan tidak jelas merujuk ke yang mana).
            # Sama seperti out_of_range: jawab jujur & generik di sini,
            # JANGAN lanjut ke intent detection/jalur LLM generik yang bisa
            # menyebut nama objek dari list yang salah jenis.
            if context_resolution.get('clarification_message'):
                # Fase: fix Bug U - sama seperti out_of_range di atas, minta
                # klarifikasi bukan pergantian topik - preserve job/tabel aktif.
                preserved_job = active_context_in.get('last_job_name') if active_context_in else None
                preserved_table = active_context_in.get('last_table_name') if active_context_in else None
                return JsonResponse({
                    'success': True,
                    'answer': f"<p>{context_resolution['clarification_message']}</p>",
                    'intent': 'ambiguous_ordinal',
                    'mentioned_job': None,
                    'active_context': build_active_context_payload(
                        preserved_job, preserved_table, job_stats, all_sessions, None, active_context_in)
                })
            if context_resolution.get('mentioned_job'):
                mentioned_job = context_resolution['mentioned_job']
            if context_resolution.get('mentioned_table'):
                mentioned_table = context_resolution['mentioned_table']
            ordinal_resolved_this_turn = bool(context_resolution.get('ordinal_resolved'))

    # Ekstrak konteks aktif dari history (FALLBACK LAMA - tidak diubah,
    # tetap jalan hanya kalau resolusi active_context di atas belum
    # menghasilkan mentioned_job apa pun)
    active_context = extract_active_context(
        conversation_history, all_jobs, all_relationships, all_sessions
    )

    # Resolve job jika pertanyaan ambigu (fallback lama, TIDAK DIUBAH)
    # Guard tambahan `not mentioned_table`: kalau resolusi active_context di atas
    # SUDAH memutuskan pertanyaan ini merujuk ke sebuah TABEL (mis. via referensi
    # ordinal ke source_tables/target_tables), jangan biarkan fallback lama ini
    # menimpa dengan tebakan JOB dari scan teks mentah - keduanya tidak boleh
    # bentrok untuk pertanyaan yang sama.
    if not mentioned_job and not mentioned_table:
        resolved = resolve_question(question, active_context, job_names_sorted)
        if resolved:
            mentioned_job = resolved

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
    capability_kw = [
        'bisa apa', 'bisa bertanya apa', 'apa saja yang bisa',
        'fitur apa', 'kemampuan', 'bantuan apa', 'help',
        'cara pakai', 'bagaimana cara', 'apa yang kamu bisa',
        'kamu bisa apa', 'bisa tanya apa', 'kegunaan', 'fungsinya',
        'apa yang bisa kamu lakukan', 'kamu bisa bantu apa',
        'gimana cara pakainya', 'panduan', 'tutorial'
    ]

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

    impact_kw = [
        'dampak', 'impact', 'terdampak', 'pengaruh', 'efek',
        'jika gagal', 'kalau gagal', 'jika terlambat', 'kalau terlambat',
        'jika telat', 'downstream', 'buatkan impact', 'buat impact',
        'impact analysis', 'analisis dampak', 'coba buatkan impact',
        'berikan impact', 'tampilkan impact', 'risiko', 'bahaya',
        'yang terdampak', 'apa dampaknya', 'dampaknya apa',
        'pengaruhnya', 'efeknya', 'akibatnya', 'konsekuensinya'
    ]

    # CONFUSED KEYWORDS - user bingung mau tanya apa
    confused_kw = [
        'bingung', 'tidak tahu mau tanya', 'ga tau mau tanya',
        'gak tau', 'nanya yang lain', 'tanya yang lain',
        'hal lain', 'topik lain', 'pertanyaan lain',
        'mau nanya lain', 'mau tanya lain', 'ganti topik',
        'ga tau harus tanya apa', 'tidak tahu harus tanya apa',
        'mau tanya tapi bingung'
    ]

    full_detail_kw = ['source table, target', 'target table, source',
                      'source dan target', 'target dan source',
                      'detail source', 'detail target',
                      'semua tabel', 'lengkap', 'semua detail',
                      'relasinya', 'semua relasi', 'source table dan',
                      'target table dan', 'apa saja source table,']

    source_kw = [
        'source', 'sumber', 'input', 'dari mana', 'source table',
        'tabel sumber', 'membaca', 'mengambil', 'dibaca dari',
        'data dari mana', 'asalnya', 'originnya', 'tabel input',
        'source nya', 'sourcenya', 'tabel asal'
    ]
    target_kw = [
        'target', 'output', 'hasil', 'menghasilkan', 'menulis',
        'tabel output', 'tabel target', 'table name', 'tabel name',
        'tabel apa', 'apa saja tabel', 'targetnya', 'target nya',
        'tabel hasil', 'tabel tujuan', 'disimpan ke', 'ditulis ke',
        'outputnya', 'hasilnya kemana', 'kemana datanya'
    ]
    status_kw = [
        'status', 'kondisi', 'failed', 'gagal', 'sukses',
        'terlambat', 'telat', 'running', 'berjalan', 'upload failed',
        'upload status', 'berhasil', 'tidak berhasil', 'error',
        'statusnya', 'kondisinya', 'gimana statusnya', 'bagaimana status'
    ]
    log_kw = [
        'log', 'logs', 'detail log', 'riwayat', 'history upload',
        'history log', 'log upload', 'upload log', 'lihat log',
        'tampilkan log', 'aktivitas', 'rekam jejak', 'done time',
        'waktu selesai', 'kapan selesai', 'kapan upload', 'waktu upload',
        'jam berapa selesai', 'tanggal upload', 'selesai kapan',
        'upload kapan', 'lognya', 'riwayatnya', 'historynya'
    ]
    list_kw  = [
        'apa saja', 'daftar', 'list', 'tampilkan semua', 'ada berapa',
        'berapa total', 'berapa jumlah', 'semua job', 'semua tabel',
        'show all', 'lihat semua', 'kasih lihat semua', 'job apa saja',
        'job yang ada', 'ada job apa', 'job apa yang', 'semua nya',
        'keseluruhan', 'seluruh job', 'list job', 'daftarkan',
        # Fase: fix Bug C - "job lain" tidak boleh resolve ke active context
        # (user eksplisit minta job LAIN, bukan follow-up job aktif) dan tidak
        # boleh jatuh ke casual_kw (jebakan 'ya' di dalam kata 'yang'/'saya').
        # Ditangani dengan reuse list_data: tampilkan list semua job supaya
        # user bisa pilih sendiri - deterministik, tidak pernah mengklaim
        # "hanya ada 1 job".
        'job lain', 'job lainnya', 'job yang lain', 'lihat job lain',
        'lihat job lainnya', 'melihat job lain', 'melihat job lainnya',
    ]
    rel_kw   = ['relationship', 'relasi', 'berapa relationship',
                'total relationship', 'jumlah relationship']
    dev_kw = [
        'developer', 'siapa developer', 'pic job', 'penanggung jawab',
        'tim developer', 'dibuat oleh', 'dikerjakan oleh', 'developer job',
        'siapa yang buat', 'siapa yang handle', 'siapa pic nya',
        'developernya', 'pic nya', 'pengembangnnya', 'yang mengerjakan'
    ]

    # ============================================================
    # DETEKSI CONTEXT RESET - SEBELUM CARRY-OVER
    # ============================================================
    # Fase: fix Bug S (lanjutan) - `not explicit_job_in_question` ditambahkan
    # supaya pesan yang menyebut nama job VALID secara eksplisit (mis. "oke
    # lihat job X") tidak ikut dianggap reset walau kebetulan mengandung kata
    # context_reset_kw ("oke"). Tanpa guard ini, is_reset tetap mengosongkan
    # `mentioned_job` (baris di bawah) walau intent sudah benar dipaksa jadi
    # 'job_detail' - lalu handler list_data/job_detail (STEP 5) jatuh ke
    # cabang list_data karena guard-nya sendiri butuh `mentioned_job` terisi.
    is_reset = (
        any(k in question_lower for k in context_reset_kw)
        and len(question.split()) <= 5
        and not explicit_job_in_question
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
        # tidak menyebut job lain secara eksplisit.
        # Guard `not mentioned_table`: sama seperti fallback resolve_question
        # di STEP 3, jangan timpa resolusi TABEL yang sudah diputuskan oleh
        # resolve_from_active_context dengan tebakan JOB dari scan teks mentah.
        if not mentioned_job and not mentioned_table and last_mentioned_job:
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
    # Fase: fix Bug S - nama job VALID disebut EKSPLISIT di teks pertanyaan
    # ini (bukan carry-over dari active context/riwayat) SELALU jadi
    # job_detail, apa pun kata kerja di depannya ("saya mau lihat job X",
    # "saya ingin lihat job X", dst). Dicek SEBELUM greeting/casual/confused
    # supaya tidak kalah oleh jebakan substring kata seperti "ya" di dalam
    # "saya"/"nya" (casual_kw) - beda dari guard di bawah (`elif
    # mentioned_job`) yang menangani mentioned_job hasil CARRY-OVER, yang
    # MEMANG harus kalah prioritas dari greeting/casual (lihat fix regresi
    # Active Context - "haloo", "oke saya mau beralih ke topik lain").
    #
    # Fase: fix Bug S (lanjutan) - `ordinal_resolved_this_turn` ditambahkan
    # di kondisi yang SAMA dengan alasan yang SAMA: referensi ORDINAL
    # EKSPLISIT yang berhasil di-resolve dari pesan INI (mis. "job 19",
    # "nomor 5", "yang pertama") adalah sinyal eksplisit yang setara dengan
    # nama job eksplisit - harus menang atas kata casual/confirmatif apa pun
    # yang menyertainya di kalimat yang sama (mis. "iya job 19", di mana kata
    # "iya" cocok literal dengan entry 'iya' di casual_kw - BUKAN cuma
    # jebakan substring seperti 'ya' di dalam 'saya', jadi word-boundary
    # matching pada casual_kw saja tidak menutup kasus ini). Kalau
    # resolusinya ke TABEL (tidak ada intent 'table_detail' di chatbot ini -
    # limitation lama, lihat PROJECT_MEMORY), biarkan jatuh ke 'general' yang
    # sudah otomatis menyuntik `active_table_info` (lihat
    # INTENTS_ALLOW_ACTIVE_JOB_INFO), bukan dipaksa 'job_detail'.
    elif explicit_job_in_question or ordinal_resolved_this_turn:
        intent = 'job_detail' if mentioned_job else 'general'
    # GREETING, casual, confused DICEK SEBELUM job_detail (Fase: Active Context
    # regression fix). Kalau tidak, mentioned_job yang terisi dari active
    # context (bukan disebut eksplisit di pertanyaan) akan membajak sapaan/
    # basa-basi/permintaan ganti topik jadi "job_detail" - persis bug yang
    # dilaporkan untuk "haloo" dan "oke saya mau beralih ke topik lain".
    elif any(k in question_lower for k in greeting_kw) and len(question.split()) <= 3:
        intent = 'greeting'
    elif matches_any_keyword_wordwise(question_lower, casual_kw) and len(question.split()) <= 5:
        intent = 'casual'
    elif any(k in question_lower for k in confused_kw):
        intent = 'confused'
    elif mentioned_job:
        intent = 'job_detail'
    else:
        intent = 'general'

    # DEBUG LOGGING

    # ============================================================
    # STEP 5: BANGUN CONTEXT SPESIFIK PER INTENT
    # ============================================================
    specific_context = ""

    # Bangun info konteks aktif jika ada job yang sedang dibahas - HANYA
    # untuk intent yang memang butuh objek job spesifik (lihat
    # INTENTS_ALLOW_ACTIVE_JOB_INFO, Fase: fix Bug G).
    active_job_info = ""
    if mentioned_job and intent in INTENTS_ALLOW_ACTIVE_JOB_INFO:
        stats = job_stats.get(mentioned_job, {})
        active_job_info = f"""
KONTEKS AKTIF PERCAKAPAN INI:
- Job yang sedang dibahas: {mentioned_job}
- Developer: {', '.join(stats.get('developers', ['-']))}
- Total source table: {stats.get('total_source_tables', 0)}
- Total target table: {stats.get('total_target_tables', 0)}
- Total relasi: {stats.get('total_relationships', 0)}
- Status upload: {next((s['current_status'] for s in all_sessions if s['job_name'] == mentioned_job), 'Belum diupload')}

Jika user bertanya tanpa menyebut nama job, asumsikan
pertanyaan tentang job {mentioned_job} di atas.
"""

    # Info konteks aktif untuk TABEL (dipakai kalau follow-up merujuk ke tabel,
    # bukan job - lihat resolve_from_active_context). Saat ini hanya dipakai
    # oleh jalur LLM generik di STEP 6 karena belum ada intent handler khusus
    # "detail tabel X" di chatbot ini.
    active_table_info = ""
    if mentioned_table and not mentioned_job:
        table_obj = next((t for t in all_tables if t['table_name'] == mentioned_table), None)
        if table_obj:
            active_table_info = f"""
KONTEKS AKTIF PERCAKAPAN INI:
- Tabel yang sedang dibahas: {mentioned_table}
- Kategori: {table_obj.get('table_category') or 'OTHER'}
- Deskripsi: {table_obj.get('table_desc') or '-'}

Jika user bertanya tanpa menyebut nama tabel, asumsikan
pertanyaan tentang tabel {mentioned_table} di atas.
"""

    # CAPABILITY HANDLER - Jawab natural tanpa dump data
    if intent == 'capability':
        specific_context = active_job_info + """
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
        specific_context = active_job_info + f"""
PERTANYAAN: {question}

Tugas: Balas sapaan user dengan ramah dan profesional dalam 2-3 kalimat.
Perkenalkan diri sebagai AI Assistant untuk Data Lineage EDA.
Sebutkan bahwa kamu bisa membantu tentang: info job, status upload,
impact analysis, dependency antar job, dan pertanyaan seputar ETL.
Jangan tampilkan data apapun. Jangan list schema database.
"""
    # CONFUSED HANDLER - Bantu user yang bingung mau tanya apa
    elif intent == 'confused':
        specific_context = active_job_info + f"""
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

        specific_context = active_job_info + f"""
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
        # Deteksi kata kunci agregat (Fase: Active Context regression fix):
        # kalau pertanyaan secara eksplisit minta SEMUA/FILTER job (mis. "job
        # yang gagal", "semua job"), jangan sempit ke job aktif dari active
        # context - user jelas minta analisis lintas-job, bukan job ini saja.
        impact_failure_filter_kw = [
            'yang gagal', 'job yang gagal', 'job-job yang gagal',
            'job yang bermasalah', 'yang bermasalah', 'semua yang gagal',
        ]
        is_impact_aggregate_query = (
            is_aggregate_all_jobs_query(question_lower)
            or any(k in question_lower for k in impact_failure_filter_kw)
        )

        # ============================================================
        # IMPACT ANALYSIS - DENGAN JOB SPESIFIK
        # ============================================================
        if mentioned_job and not is_impact_aggregate_query:
            from groq import Groq
            from django.conf import settings

            # Impact analysis untuk job spesifik - Fase: fix Bug O, level 1
            # (output_tables + job terdampak langsung) sekarang dihitung
            # lewat compute_direct_job_impact, fungsi yang SAMA dipakai mode
            # aggregate di bawah, supaya keduanya tidak mungkin lagi beda
            # hasil untuk job yang sama.
            output_tables, level2 = compute_direct_job_impact(mentioned_job)

            # level2_outputs: tabel output level2 job persis dari relationship
            # yang memicu job itu masuk level2 (struktur sama seperti semula,
            # cuma kriteria job level2 sekarang pakai `in level2` - exact
            # match terhadap dict level2 yang sudah benar, bukan substring).
            # Fase: performa (Task 4.1) - query tertarget (WHERE table1 IN
            # output_tables AND job_name IN level2 jobs), bukan scan
            # all_relationships penuh; level2 biasanya cuma segelintir job
            # jadi klausa IN ini kecil.
            level2_job_names = list(level2.keys())
            level2_outputs = set(
                Relationship.objects.filter(
                    table1__table_name__in=output_tables,
                    job_name__in=level2_job_names,
                ).exclude(table2__table_name__isnull=True)
                .values_list('table2__table_name', flat=True)
            ) if level2_job_names else set()

            level3 = {}
            if level2_outputs:
                rows = (
                    Relationship.objects
                    .filter(table1__table_name__in=level2_outputs)
                    .exclude(Q(job_name__in=level2_job_names) | Q(job_name__iexact=mentioned_job))
                    .values('job_name', 'table1__table_name')
                )
                for r in rows:
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
            impact_intro_context = active_job_info + f"""
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
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": impact_intro_context}
                ],
                temperature=0.1,
                # Fase: fix Bug N - 400 token kadang tidak cukup untuk job
                # dengan banyak dampak downstream (level2+level3): setiap
                # nama job/tabel yang disebut LLM di narasi "chain dampak"
                # + rekomendasi bisa makan belasan token sendiri (nama job
                # panjang seperti CDP_DMT_WHL_..._DLY_H1 dipecah jadi banyak
                # subword token), jadi makin banyak job/tabel terdampak,
                # makin sering narasi terpotong sebelum kalimat/rekomendasi
                # selesai. Diverifikasi live: job dengan 4 dampak downstream
                # terpotong mid-kalimat di 2 dari 4 percobaan pada 400 token.
                max_tokens=700
            )
            llm_narasi = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_narasi + "<br>" + level2_html + level3_html + build_proactive_suggestions(intent, mentioned_job, job_stats.get(mentioned_job, {}))
            # Fase: fix Bug D - job terdampak (level2) BUKAN daftar utuh (cuma
            # subset job yang kena dampak), jangan timpa last_list valid yang
            # lama. last_list=None -> preserve otomatis di build_active_context_payload.
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job,
                                 "active_context": build_active_context_payload(
                                     mentioned_job, None, job_stats, all_sessions,
                                     None, active_context_in)})

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
                # Fase: fix Bug O - fungsi yang SAMA dipakai oleh mode
                # single-job di atas, supaya angka "job terdampak" tidak
                # mungkin lagi berbeda untuk job yang sama.
                output_tables, impacted_jobs = compute_direct_job_impact(jname)

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

            # Fase: performa (Task 4.1) - ditemukan lewat load-test 1000+ job:
            # tanpa batas, jumlah job "bermasalah" bisa besar (ratusan), dan
            # SELURUHNYA dulu di-dump ke summary_html/detail_html DAN ke
            # prompt Groq (narasi_context) sekaligus - prompt jadi > token
            # limit Groq (HTTP 413 "Request too large", crash nyata, bukan
            # cuma lambat). Sekarang dibatasi ke TOP N (paling kritis, sudah
            # terurut dari total_impacted_jobs terbesar) untuk detail_html
            # DAN narasi Groq - summary_html tetap menampilkan SEMUA baris
            # (ringkasan 1 baris/job jauh lebih kecil daripada detail_html
            # yang berisi sub-tabel per job, jadi risikonya rendah), tapi
            # kalau daftar job bermasalah sendiri sangat besar, itu di luar
            # scope task ini (list_data yang eksplisit diminta berpaginasi;
            # halaman aggregate ini didokumentasikan sebagai follow-up di
            # laporan akhir).
            IMPACT_ANALYSIS_TOP_N = 20
            top_impacts = all_impacts[:IMPACT_ANALYSIS_TOP_N]
            truncated_count = len(all_impacts) - len(top_impacts)

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

            # STEP 5: Build detail per job bermasalah - HANYA top N paling
            # kritis (lihat catatan performa di atas).
            detail_html = ""
            if truncated_count > 0:
                detail_html += (
                    f"<p><em>Menampilkan detail {len(top_impacts)} job paling kritis "
                    f"dari {len(all_impacts)} total job bermasalah "
                    f"({truncated_count} job lainnya cuma tampil di ringkasan di atas, "
                    f"tanya spesifik nama job-nya untuk detail lengkap).</em></p>"
                )
            for imp in top_impacts:
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
            # Fase: fix Bug F - JANGAN suntik active_job_info di sini. Ini
            # jawaban agregat lintas-job; menyisipkan info 1 job aktif bikin
            # LLM dapat instruksi kontradiktif (narasi agregat vs "asumsikan
            # semua tentang job X") dan hasilnya kalimat tidak nyambung/typo.
            narasi_context = """
Ada """ + str(len(all_impacts)) + """ job bermasalah di sistem.
Data dampak """ + (f"{len(top_impacts)} job PALING KRITIS" if truncated_count > 0 else "per job") + """ (diurutkan dari dampak terbesar):
""" + str([{
    'job': x['job_name'],
    'status': x['status'],
    'gagal': str(x['fail_count']) + 'x',
    'tabel_output': x['total_output_tables'],
    'job_terdampak': x['total_impacted_jobs']
} for x in top_impacts]) + """

Tugas: Buat narasi pembuka 2-3 kalimat yang menjelaskan:
1. Kondisi sistem secara keseluruhan
2. Job mana yang paling kritis (paling banyak job terdampak)
3. Rekomendasi tindakan prioritas
Gunakan bahasa profesional, tidak kaku. Langsung ke inti pembahasan.
JANGAN mulai dengan basa-basi seperti "terima kasih atas informasinya" -
user belum memberikan informasi apa pun, data di atas murni untukmu.
JANGAN buat tabel. Tabel sudah disiapkan terpisah.
"""
            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": narasi_context}
                ],
                temperature=0.1,
                # Fase: fix Bug N - naik dari 400 selaras dengan versi
                # single-job (lihat komentar di atas); narasi agregat ini
                # dibatasi ke "2-3 kalimat" jadi risiko terpotongnya lebih
                # rendah, tapi tetap bisa menyebut beberapa nama job kritis.
                max_tokens=500
            )
            llm_narasi = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_narasi + "<br>" + summary_html + detail_html
            # Fase: fix Bug D - job bermasalah BUKAN daftar utuh 21 job (cuma
            # subset hasil filter "gagal"), jangan timpa last_list valid yang
            # lama. last_list=None -> preserve otomatis.
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": None,
                                 "active_context": build_active_context_payload(
                                     None, None, job_stats, all_sessions,
                                     None, active_context_in)})

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

        # Fase: fix Bug E - kalau user eksplisit minta log SEMUA job, jangan
        # diam-diam sempit ke job aktif dari active context.
        if mentioned_job and not is_aggregate_all_jobs_query(question_lower):
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
                narasi_context = active_job_info + f"""
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
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                        {"role": "user", "content": narasi_context}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                llm_narasi = normalize_llm_markdown(llm_response.choices[0].message.content)
                answer = llm_narasi + "<br>" + session_html + log_html

            else:
                answer = (f"<p>Job <code>{mentioned_job}</code> "
                          f"belum memiliki riwayat upload di sistem.</p>")
            reported_job = mentioned_job

        else:
            # Tampilkan semua sessions dengan done_time. Masuk sini juga kalau
            # user eksplisit minta "semua job" walau active context masih ada
            # job aktif (Fase: fix Bug E) - reported_job=None supaya jawaban
            # ini tidak dilaporkan sebagai "tentang job aktif".
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
            reported_job = None

        # Fase: fix Bug D - riwayat upload sessions BUKAN daftar utuh 21 job
        # (cuma job yang pernah upload via bot, lihat PROJECT_MEMORY.md),
        # jangan timpa last_list valid yang lama. last_list=None -> preserve.
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": reported_job,
                             "active_context": build_active_context_payload(
                                 reported_job, None, job_stats, all_sessions,
                                 None, active_context_in)})

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
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": intro_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
        answer = llm_intro + "<br>" + src_html + tgt_html + rel_html
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": mentioned_job,
                             "active_context": build_active_context_payload(
                                 mentioned_job, None, job_stats, all_sessions, None)})

    elif intent == 'source_tables':
        # Fase: fix Bug E - "source table semua job" tidak boleh sempit ke
        # job aktif dari active context.
        if mentioned_job and not is_aggregate_all_jobs_query(question_lower):
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
            intro_context = active_job_info + f"""
Job: {mentioned_job}
Developer: {stats.get('developers', '-')}
Jumlah source table: {len(src)}

PENTING: Jangan buat tabel HTML. Tabel sudah disiapkan.
Tugas: Buat hanya 1-2 kalimat pembuka tentang source table job ini.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": intro_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_intro + "<br>" + src_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job,
                                 "active_context": build_active_context_payload(
                                     mentioned_job, None, job_stats, all_sessions,
                                     build_last_list('source_tables', src), active_context_in)})
        else:
            specific_context = f"{DB_SCHEMA}\nPERTANYAAN: {question}\nTidak ada job spesifik. Semua job: {[j['job_name'] for j in all_jobs]}\nTugas: Minta user menyebutkan nama job yang dimaksud."

    elif intent == 'target_tables':
        # Fase: fix Bug E - "target table semua job" tidak boleh sempit ke
        # job aktif dari active context.
        if mentioned_job and not is_aggregate_all_jobs_query(question_lower):
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
            intro_context = active_job_info + f"""
Job: {mentioned_job}
Developer: {stats.get('developers', '-')}
Jumlah target table: {len(tgt)}

PENTING: Jangan buat tabel HTML. Tabel sudah disiapkan.
Tugas: Buat hanya 1-2 kalimat pembuka tentang target table job ini.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": intro_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_intro + "<br>" + tgt_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job,
                                 "active_context": build_active_context_payload(
                                     mentioned_job, None, job_stats, all_sessions,
                                     build_last_list('target_tables', tgt), active_context_in)})
        else:
            specific_context = f"{DB_SCHEMA}\nPERTANYAAN: {question}\nSemua job: {[j['job_name'] for j in all_jobs]}\nTugas: Minta user menyebutkan nama job."

    elif intent == 'developer_info':
        # Fase: fix Bug E - "developer semua job" tidak boleh sempit ke job
        # aktif dari active context.
        if mentioned_job and not is_aggregate_all_jobs_query(question_lower):
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
            dev_context = active_job_info + f"""
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
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": dev_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_intro + "<br>" + dev_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job,
                                 "active_context": build_active_context_payload(
                                     mentioned_job, None, job_stats, all_sessions,
                                     None, active_context_in)})
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

            # LLM hanya buat narasi. Fase: fix Bug F - JANGAN suntik
            # active_job_info di sini, ini jawaban agregat semua developer.
            dev_context = f"""
Semua developer yang terdaftar: {len(all_devs)} orang

Tugas: Tampilkan dalam 1-2 kalimat bahwa ada {len(all_devs)} developer yang terdaftar.
JANGAN mulai dengan basa-basi seperti "terima kasih atas informasinya" -
user belum memberikan informasi apa pun.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""

            client = get_groq_client()
            llm_response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": dev_context}
                ],
                temperature=0.1,
                max_tokens=300
            )
            llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_intro + "<br>" + dev_list_html
            # reported_job=None: ini jawaban agregat, bukan tentang job aktif.
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": None,
                                 "active_context": build_active_context_payload(
                                     None, None, job_stats, all_sessions,
                                     None, active_context_in)})

    elif intent == 'job_status':
        from groq import Groq
        from django.conf import settings

        # Fase: fix Bug E - "status semua job" tidak boleh sempit ke job
        # aktif dari active context (pola sama seperti impact_analysis Fase
        # 1B, ditemukan lewat audit di fase ini - lihat laporan akhir).
        if mentioned_job and not is_aggregate_all_jobs_query(question_lower):
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
            status_context = active_job_info + f"""
Job: {mentioned_job}
Status: {job_session['current_status'] if job_session else 'Belum diupload'}
Jumlah gagal: {job_fail['fail_count'] if job_fail else 0}

Tugas: Jawab pertanyaan status dalam 1-2 kalimat.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""
            reported_job = mentioned_job
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

            # LLM hanya buat narasi. Fase: fix Bug F - JANGAN suntik
            # active_job_info di sini, ini jawaban agregat semua job.
            status_context = f"""
Total job: {len(all_jobs)}
Job dengan status failed: {len([s for s in all_sessions if s.get('current_status') and 'fail' in s['current_status'].lower()])}
Job paling sering gagal: {[f['job__job_name'] for f in all_failures[:3]] if all_failures else 'Tidak ada'}

Tugas: Jawab pertanyaan status dalam 2-3 kalimat.
JANGAN mulai dengan basa-basi seperti "terima kasih atas informasinya" -
user belum memberikan informasi apa pun.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""
            reported_job = None

        client = Groq(api_key=settings.GROQ_API_KEY)
        llm_response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": status_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
        answer = llm_intro + "<br>" + status_html
        # Fase: fix Bug D - status semua job sengaja TIDAK menimpa last_list
        # (biar konsisten dengan aturan "hanya list_data/source_tables/
        # target_tables yang boleh update last_list"). last_list=None -> preserve.
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": reported_job,
                             "active_context": build_active_context_payload(
                                 reported_job, None, job_stats, all_sessions,
                                 None, active_context_in)})

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

        # LLM hanya buat narasi. Fase: fix Bug F - JANGAN suntik active_job_info
        # di sini - relationship_info SELALU jawaban agregat lintas-job, tidak
        # pernah bercabang ke 1 job spesifik.
        rel_context = f"""
Total relationship di database: {len(all_relationships)}
Total job: {len(all_jobs)}
Job dengan relasi paling banyak: {[r['job'] for r in job_rel_summary[:3]]}

Tugas: Jawab pertanyaan tentang relationship dalam 2-3 kalimat.
JANGAN mulai dengan basa-basi seperti "terima kasih atas informasinya" -
user belum memberikan informasi apa pun.
JANGAN buat tabel HTML. Tabel sudah disiapkan.
"""

        client = Groq(api_key=settings.GROQ_API_KEY)
        llm_response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                {"role": "user", "content": rel_context}
            ],
            temperature=0.1,
            max_tokens=400
        )
        llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
        answer = llm_intro + "<br>" + rel_summary_html
        # Fase: fix Bug D - ranking top-15 BUKAN daftar utuh, jangan timpa
        # last_list valid yang lama. reported_job=None karena selalu agregat.
        return JsonResponse({"answer": answer, "intent": intent,
                             "mentioned_job": None,
                             "active_context": build_active_context_payload(
                                 None, None, job_stats, all_sessions,
                                 None, active_context_in)})

    elif intent in ['list_data', 'job_detail']:
        from groq import Groq
        from django.conf import settings

        # Guard `intent == 'job_detail'` (Fase: Active Context regression fix):
        # kalau intent yang terdeteksi adalah 'list_data' (mis. "semua job",
        # "tampilkan semua job yang ada"), SELALU tampilkan list - jangan
        # sampai mentioned_job dari active context membajaknya jadi detail
        # satu job saja.
        if mentioned_job and intent == 'job_detail':
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
            intro_context = active_job_info + f"""
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
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Kamu adalah AI Assistant untuk Data Lineage EDA. Gunakan Bahasa Indonesia profesional."},
                    {"role": "user", "content": intro_context}
                ],
                temperature=0.1,
                max_tokens=200
            )
            llm_intro = normalize_llm_markdown(llm_response.choices[0].message.content)
            answer = llm_intro + "<br>" + detail_html
            return JsonResponse({"answer": answer, "intent": intent,
                                 "mentioned_job": mentioned_job,
                                 "active_context": build_active_context_payload(
                                     mentioned_job, None, job_stats, all_sessions,
                                     None, active_context_in)})

        # List semua job (untuk intent list_data) - Fase: performa (Task 4.1).
        # Sebelumnya membangun job_full_summary dari job_stats (SELURUH job
        # yang sudah di-load penuh di STEP 1) lalu menampilkan semuanya
        # sekaligus tanpa batas - di skala 1000+ job tabel HTML jadi tidak
        # praktis. Sekarang query DB langsung dengan LIMIT/OFFSET (halaman
        # pertama, offset=0) + filter dasar (tabel/developer/"belum
        # diupload") dari teks pertanyaan, lewat render_job_list_page -
        # fungsi yang SAMA dipakai follow-up "lanjut ke halaman berikutnya"
        # (lihat pengecekan di STEP 3), supaya kedua jalur selalu konsisten.
        filters = detect_list_data_filters(question_lower, table_names_sorted, developer_names_sorted)
        return render_job_list_page(0, filters, active_context_in, all_sessions)

    else:
        # Fase: fix Bug R - frasa yang secara implisit minta "semua data
        # sekaligus tanpa halaman" (mis. "tampilkan langsung semua job",
        # "tampilkan langsung 21 job") tidak match keyword list_kw manapun
        # (list_kw sudah punya "tampilkan semua"/"semua job" dst, tapi
        # bukan "tampilkan langsung"), jadi jatuh ke intent 'general' -
        # lalu Groq dapat instruksi sistem "kalau data tidak ada, katakan
        # 'Data ini belum tersedia di sistem'" (lihat STEP 6) dan salah
        # menyimpulkan seolah datanya memang tidak ada, padahal datanya
        # ADA, cuma paginasi "semua sekaligus" tidak didukung. Ditangani
        # di sini dengan pesan deterministik (bukan lewat Groq, supaya
        # tidak bergantung pada LLM menebak konteks dengan benar) yang
        # jujur soal keterbatasannya dan mengarahkan ke paginasi yang
        # sudah ada. TIDAK menambah fitur tampilkan-semua-tanpa-halaman
        # sungguhan - itu keputusan produk terpisah, di luar scope.
        no_pagination_kw = [
            'langsung semua', 'tampilkan langsung', 'sekaligus semua',
            'semua sekaligus', 'satu halaman', 'tanpa halaman',
            'tanpa paginasi', 'jangan per halaman', 'sekali lihat semua',
        ]
        if any(k in question_lower for k in no_pagination_kw):
            return JsonResponse({
                "answer": (
                    "<p>Job ditampilkan per halaman (20 job per halaman), "
                    "bukan sekaligus semua - supaya tabelnya tetap mudah "
                    "dibaca. Coba minta \"tampilkan semua job\" dulu, lalu "
                    "ketik \"lihat halaman berikutnya\" untuk lanjut ke "
                    "halaman selanjutnya.</p>"
                ),
                "intent": "list_data_no_pagination_hint",
                "mentioned_job": None,
                "active_context": build_active_context_payload(
                    None, None, {}, all_sessions, None, active_context_in)
            })

        # General / ETL concepts - Jawab natural tanpa dump data
        specific_context = active_job_info + f"""
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
    # Tambahkan job context header agar Groq tahu job yang sedang dibahas.
    # Fase: fix Bug G (lanjutan) - header ini adalah TITIK KEDUA yang bisa
    # membocorkan job/tabel aktif ke narasi (terpisah dari active_job_info
    # di STEP 5, yang sudah digerbang whitelist). Justru header ini yang
    # paling agresif ("SEMUA pertanyaan diasumsikan tentang job X, jangan
    # minta user menyebutkan nama job lagi") jadi kalau tidak ikut digerbang
    # whitelist yang sama, greeting/casual/capability/confused tetap bisa
    # menyebut job aktif walau active_job_info sudah dikosongkan.
    if mentioned_job and intent in INTENTS_ALLOW_ACTIVE_JOB_INFO:
        job_context_header = f"""
!! KONTEKS AKTIF: Percakapan saat ini sedang membahas job '{mentioned_job}'.
Jika pertanyaan tidak menyebut job lain secara eksplisit,
SEMUA pertanyaan diasumsikan tentang job '{mentioned_job}'.
Jangan minta user menyebutkan nama job lagi.
"""
        specific_context = job_context_header + "\n" + specific_context
    elif mentioned_table and intent in INTENTS_ALLOW_ACTIVE_JOB_INFO:
        table_context_header = f"""
!! KONTEKS AKTIF: Percakapan saat ini sedang membahas tabel '{mentioned_table}'.
Jika pertanyaan tidak menyebut tabel lain secara eksplisit,
SEMUA pertanyaan diasumsikan tentang tabel '{mentioned_table}'.
"""
        specific_context = active_table_info + table_context_header + "\n" + specific_context
    from groq import Groq
    from django.conf import settings

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """Kamu adalah AI Assistant untuk tim Data Engineer dan ETL Analyst.
Gunakan Bahasa Indonesia yang profesional namun tidak kaku.
Seperti rekan kerja senior yang menjelaskan sesuatu kepada timnya.

GAYA BAHASA:
- Langsung ke inti jawaban, tidak bertele-tele
- Boleh memberi interpretasi singkat dari data yang ada
- Jangan mulai dengan "Berdasarkan data yang diberikan..."zz
- Kalau data tidak ada, katakan: "Data ini belum tersedia di sistem."
- Untuk pertanyaan umum ETL/data engineering, jawab bebas dan edukatif

FORMAT OUTPUT (WAJIB HTML, BUKAN MARKDOWN):
- Nama job dan tabel selalu dalam tag <code>
- List gunakan <ul><li> atau <ol><li>
- Tabel gunakan <table class="table table-bordered table-striped table-sm">
- Semua tabel dibungkus <div style="overflow-x:auto">...</div>
- Judul section gunakan <strong> atau <h6>
- JANGAN pakai **, *, ##, atau | --- | (markdown)
z
FORMAT JOB DETAIL (WAJIB):
Saat menampilkan informasi satu job, gunakan format HTML ini:
<h6><code>NAMA_JOB</code></h6>
<table class='table table-bordered table-sm' style='max-width:500px'>
  <thead><tr><th>Field</th><th>Keterangan</th></tr></thead>
  <tr><td>Developer</td><td>...</td></tr>
  <tr><td>Total Source Table</td><td>...</td></tr>
  <tr><td>Total Target Table</td><td>...</td></tr>.
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

        answer = normalize_llm_markdown(response.choices[0].message.content)

        # GABUNGKAN LLM response dengan HTML tables
        return JsonResponse({
            'success': True,
            'answer': answer,
            'intent': intent,
            'mentioned_job': mentioned_job,
            'active_context': build_active_context_payload(
                mentioned_job, mentioned_table, job_stats, all_sessions, None, active_context_in)
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