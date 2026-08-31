# CLAUDE.md

Dokumen ini membantu AI assistant (Claude Code) memahami project **Data Lineage EDA** dengan cepat dan menghindari kesalahan yang sudah teridentifikasi lewat repository discovery & audit. Semua isi di bawah berbasis temuan aktual dari kode, bukan asumsi.

---

## Tentang Project

Data Lineage EDA adalah aplikasi web Django untuk melacak lineage data (aliran data antar tabel dan job ETL) di lingkungan Bank Mandiri (Tim Data Management, ODP-IT). Dilengkapi AI Chatbot (Groq API) untuk query natural language, dan terintegrasi dengan workflow n8n untuk otomasi deteksi upload job & schema tabel.

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Backend | Django 6.0.2, Python 3.12 |
| Database | PostgreSQL — 2 database terpisah (`default` = `data_lineage_eda`, `bot_eda`) |
| AI/LLM | Groq API (`groq` SDK v0.11.0), model diatur via env var `GROQ_MODEL` |
| Frontend | Django Templates, Bootstrap 5, vanilla JS/jQuery (bukan SPA) |
| Static files | WhiteNoise |
| Automation | n8n (termasuk node LangChain agent + `lmChatGroq`) |
| Deployment | Railway (nixpacks + Gunicorn) + Neon Postgres |

## Struktur Direktori Penting

```
data-lineage/
├── README.md, deployment_guide.md
├── migrasi_db/                # dump PostgreSQL (data_lineage_eda, bot_eda)
├── n8n json/                  # export workflow n8n
└── Web/                       # root Django project
    ├── data_lineage/
    │   ├── settings.py        # config utama — lihat catatan kredensial di bawah
    │   ├── db_router.py       # BotEdaRouter — routing 3 model ke DB bot_eda
    │   └── urls.py
    └── main/                  # satu-satunya Django app
        ├── models.py          # Table, JobDetail, JobDeveloper, Relationship, TableDetail, SchemaCategoryMapping
        ├── bot_eda.py         # model UNMANAGED (managed=False) — dimiliki n8n, bukan Django migrations
        ├── views.py           # ~1787 baris — CRUD + API lineage graph + webhook n8n
        ├── chatbot_views.py   # ~1705 baris — logic chatbot AI
        ├── utils.py, forms.py, admin.py
        ├── migrations/        # migrasi resmi Django (+ folder `backup/` yang TIDAK dieksekusi)
        └── templates/, static/
```

## Menjalankan Project Secara Lokal

Sesuai `README.md`:
1. `python -m venv venv` → `pip install -r requirements.txt` (dijalankan dari `Web/`)
2. Buat 2 database PostgreSQL: `data_lineage_eda` dan `bot_eda`
3. Isi `.env` di `Web/` dengan `GROQ_API_KEY` (dan opsional `GROQ_MODEL`)
4. `python manage.py migrate` lalu `python manage.py migrate --database=bot_eda`
5. `python manage.py runserver`

## Arsitektur Kunci yang Harus Dipahami Sebelum Mengubah Kode

- **Dual-database**: `Table`, `JobDetail`, `Relationship`, `TableDetail`, `JobDeveloper`, `SchemaCategoryMapping` ada di DB `default`. `JobUploadSessions`, `JobUploadLogs`, `StagingDetectedTables` (didefinisikan di `main/bot_eda.py`, `managed = False`) ada di DB `bot_eda` dan **dimiliki oleh n8n** — query ke model ini wajib pakai `.using('bot_eda')`.
- **n8n terhubung dua arah**: (1) webhook masuk `POST /api/n8n/lineage/` (`receive_n8n_lineage` di `views.py`) menerima data dari n8n dan membuat Job/Table/Relationship; (2) n8n juga bisa menulis langsung ke DB `bot_eda` lewat Postgres node — perubahan skema `bot_eda` harus dikoordinasikan dengan workflow n8n, bukan lewat migration Django biasa.
- **Chatbot bersifat hybrid**: intent-detection berbasis keyword Bahasa Indonesia (bukan LLM function-calling), lalu query data dilakukan manual di Python, tabel HTML dibangun manual (`build_html_table`, `build_detail_table`), dan Groq **hanya** dipakai untuk narasi/ringkasan — bukan untuk mengambil data. Pola ini sengaja mengurangi risiko halusinasi angka oleh LLM; pertahankan pola ini saat menambah fitur chatbot baru.

## Kondisi & Batasan Saat Ini (Wajib Diperhatikan Sebelum Edit)

- **Tidak ada test coverage.** `main/tests.py` masih boilerplate default Django, tidak ada `pytest`/`pytest-django` di `requirements.txt`. Perubahan pada `views.py` atau `chatbot_views.py` tidak bisa diverifikasi otomatis — lakukan perubahan minimal, incremental, dan test manual sebelum menganggap selesai.
- **Tidak ada autentikasi di layer aplikasi.** `django.contrib.auth` terpasang di `INSTALLED_APPS` tapi tidak dipakai di app `main` — tidak ada `@login_required` di manapun. Jangan berasumsi ada permission check tersembunyi saat menambah endpoint baru.
- **Kredensial hardcoded di `data_lineage/settings.py`** (`SECRET_KEY`, password DB) dan file ini **ter-track di git**. Jangan tambahkan secret baru langsung ke `settings.py` — gunakan environment variable seperti pola yang sudah ada untuk konfigurasi production (`os.environ.get(...)`).
- **`build_html_table`/`build_detail_table` di `chatbot_views.py` tidak melakukan HTML-escaping** terhadap nilai dari database (`table_name`, `job_name`, `log_message`) sebelum dikirim ke frontend dan di-render lewat `innerHTML` (`chatbot.html`). Nilai-nilai ini bisa berasal dari CSV upload (`create_table`) atau webhook n8n eksternal (`receive_n8n_lineage`) — hati-hati saat menyentuh fungsi ini, jangan perkenalkan interpolasi string baru tanpa escaping.
- **Banyak endpoint memakai `@csrf_exempt`**: `chatbot_ask`, `upload_relationships`, `receive_n8n_lineage`, `api_add_relationship`, `api_delete_relationship`. Jangan menghapus dekorator ini tanpa memverifikasi frontend sudah mengirim CSRF token yang valid (`chatbot.html` sudah mengirim `X-CSRFToken` di beberapa tempat).
- **`Web/utils/seeding.py` sudah usang** — mereferensikan model `ParentChildRelationship` dan `ColumnUsedInRelationship` yang sudah dihapus dari `models.py` (lihat migration `0002_remove_parentchildrelationship...`). File ini akan error jika dijalankan; jangan jadikan referensi pola seeding.
- **`main/migrations/backup/`** berisi file migrasi lama (`0011`–`0014`) yang **tidak dieksekusi** Django karena berada di subfolder, bukan langsung di `migrations/`. Jangan pindahkan isinya ke dalam `migrations/` tanpa audit menyeluruh terhadap state skema saat ini.
- **Inkonsistensi dokumentasi model LLM**: `settings.py` men-default `GROQ_MODEL` ke `openai/gpt-oss-120b`, sedangkan `README.md` menyebut `llama-3.3-70b-versatile` sebagai contoh. Env var `GROQ_MODEL` yang menentukan model aktual di runtime — jangan asumsikan dari README saja.
- **Tidak ada retry/timeout pada panggilan Groq API** di `chatbot_views.py` — permintaan chatbot yang lambat bisa menahan worker Gunicorn (hanya 3 worker dikonfigurasi di `Procfile`/`railway.toml`).

## Do's

- Selalu cek apakah model yang disentuh ada di `main/bot_eda.py` (unmanaged) — jika ya, gunakan `.using('bot_eda')` dan jangan buat migration Django untuk model tersebut.
- Escape/sanitize semua nilai dinamis sebelum dimasukkan ke string HTML di `chatbot_views.py`.
- Untuk perubahan pada `settings.py`, gunakan environment variable, ikuti pola production yang sudah ada (`if os.environ.get('...')`).
- Untuk perubahan berisiko (auth, CSRF, webhook), buat perubahan kecil dan dapat di-rollback (lihat `IMPLEMENTATION_PLAN.md`).

## Don'ts

- Jangan menghapus `@csrf_exempt` tanpa memverifikasi CSRF token terkirim dari frontend terkait.
- Jangan menganggap ada validasi/otorisasi tersembunyi di view manapun — cek eksplisit dulu.
- Jangan lakukan rewrite besar terhadap `chatbot_views.py` atau `views.py` sekaligus — keduanya file besar (>1700 baris) tanpa test coverage, perubahan kecil bertahap lebih aman.
- Jangan hapus file di `migrations/` (termasuk `backup/`) tanpa mengonfirmasi state skema database saat ini.

## Rujukan

Audit teknis lengkap (arsitektur, security, performance, testing, AI/LLM reliability) tersedia sebagai riwayat percakapan sebelumnya dan diringkas di `PROJECT_MEMORY.md`. Rencana perbaikan bertahap ada di `IMPLEMENTATION_PLAN.md`.
