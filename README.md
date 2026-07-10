# Data Lineage EDA

Sistem manajemen data lineage untuk melacak aliran data antar tabel dan job ETL, dilengkapi dengan AI Chatbot untuk analisis interaktif. Project ini membantu tim Data Engineer dan Analyst dalam memetakan dependencies antar job, menganalisis dampak jika suatu job gagal, serta memantau status upload job secara real-time.

---

## Daftar Isi

- [Tentang Project](#tentang-project)
- [Fitur](#fitur)
- [Tech Stack](#tech-stack)
- [Prasyarat](#prasyarat)
- [Instalasi & Setup](#instalasi--setup)
- [Migrasi Database](#migrasi-database)
- [Menjalankan Project](#menjalankan-project)
- [Fitur AI Chatbot](#fitur-ai-chatbot)
- [Struktur Project](#struktur-project)
- [Konfigurasi](#konfigurasi-tambahan)
- [Troubleshooting](#troubleshooting)
- [Kontributor](#kontributor)

---

## Tentang Project

**Data Lineage EDA** adalah aplikasi web berbasis Django yang dirancang untuk membantu tim Data Engineer dan Analyst mengelola dan melacak lineage (silsilah) data dalam ekosistem ETL bank Mandiri.

### Masalah yang Diselesaikan

- **Ketidakjelasan dependencies**: Tim sering tidak mengetahui job mana yang bergantung pada output job lain
- **Kesulitan tracking dampak**: Ketika sebuah job gagal, sulit untuk menentukan job mana saja yang terdampak
- **Fragmentasi informasi**: Informasi tentang job, tabel, dan developer tersebar di berbagai tempat
- **Monitoring manual**: Pemantauan status upload job dilakukan secara manual

### Untuk Siapa Project Ini

- **Data Engineer**: Mengelola job ETL dan memahami data flow
- **Data Analyst**: Melihat dari mana data berasal dan ke mana data pergi
- **Data Governance**: Memantau lineage dan memastikan kualitas data
- **Team Lead**: Mengawasi pekerjaan tim dan analyzing impact

---

## Fitur

### Dashboard Utama
- Statistik keseluruhan: total job, tabel, relationship, dan data sources
- Navigasi cepat ke semua fitur
- Tampilan ringkas dan informatif

### Manajemen Tabel Database
- **Create Table**: Tambah tabel baru secara manual atau via CSV upload
- **Edit Table**: Modifikasi detail tabel termasuk kolom (column name, data type, description)
- **View Table**: Lihat detail tabel lengkap dengan relasi masuk (incoming) dan keluar (outgoing)
- **Delete Table**: Hapus tabel yang tidak diperlukan
- **Search & Filter**: Pencarian tabel berdasarkan nama atau kategori (DATAMART, STAGING, SOURCE DATA, OTHER)
- Auto-kategori berdasarkan schema mapping

### Manajemen Job ETL
- **Create Job**: Tambah job baru dengan target table dan developer
- **Edit Job**: Modifikasi informasi job, termasuk penambahan source table relationship
- **View Job**: Detail job lengkap dengan semua source dan target table
- **Delete Job**: Hapus job (tabel yang tidak terpakai akan ikut dihapus)
- **Upload Job**: Upload job script ke sistem dengan path ZIP dan informasi target table
- **Download Excel**: Export detail job ke file Excel untuk dokumentasi

### Manajemen Relationship
- **Upload Relationship**: Upload relationship via CSV dengan format Job Name, Target Table, Source Tables
- **Relationship List**: Lihat semua relationship dengan fitur search
- Otomatis create job jika belum ada saat upload relationship

### Visualisasi Data Lineage
- **Interactive Graph**: Visualisasi graf interaktif untuk melihat aliran data
- **Focus Table**: Pilih tabel fokus untuk melihat upstream dan downstream
- **Depth Control**: Atur kedalaman visualisasi lineage
- **Auto-complete**: Pencarian tabel cepat dengan suggestions
- **Category Colors**: Warna berbeda untuk setiap kategori tabel

### Manajemen Developer
- **Create Developer**: Tambah developer baru dengan department dan team
- **Edit Developer**: Update informasi developer
- **View Developer**: Lihat detail developer dan job yang ditangani
- **Delete Developer**: Hapus developer dari sistem
- **Search Developer**: Pencarian berdasarkan nama, departemen, atau team

### Upload Logs Monitoring
- **Status Tracking**: Pantau status upload job (Done, On Progress, Need Confirmation, Upload Failed)
- **Log History**: Riwayat log detail setiap proses upload
- **Tab Filtering**: Filter berdasarkan status
- **Category Update**: Update kategori staging table yang terdeteksi
- **Refresh Status**: Otomatis refresh status dari log terbaru
- **Retry Count**: Informasi jumlah retry upload

### AI Chatbot (Groq API)
Fitur chatbot AI yang memungkinkan pengguna bertanya dalam bahasa natural untuk mendapatkan informasi tentang:

**Info Job:**
- "tampilkan semua job yang ada"
- "detail job CDP_DMT_WHL_EALCO_DLY_H0"
- "siapa developer dari job DPK_H0_KLN?"

**Source & Target Table:**
- "apa saja source table dari job RDBMS_CDP_NEW_RMTOOLS_DLY_H1?"
- "tampilkan target tablenya"

**Impact Analysis:**
- "dampak jika job CDP_DMT_WHL_EALCO_DLY_H0 gagal?"
- "buatkan impact analysis dari semua job yang gagal"

**Log & Status:**
- "tampilkan log upload job RDBMS_CDP_NEW_RMTOOLS_DLY_H1"
- "kapan job CDP_DMT_WHL_EALCO_DLY_H0 selesai diupload?"
- "job mana yang paling sering gagal?"

**Pertanyaan Umum:**
- "apa itu ETL?"
- "apa best practice data lineage?"

---

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Backend | Django 6.0.2 |
| Database | PostgreSQL |
| AI/LLM | Groq API (llama-3.3-70b-versatile) |
| Frontend | Bootstrap 5, jQuery |
| Visualization | Custom JavaScript (Graph) |
| Workflow | n8n |
| Python | 3.12 |

---

## Prasyarat

Sebelum instalasi, pastikan sudah terinstall:

- **Python 3.10** atau lebih baru
- **PostgreSQL 12** atau lebih baru
- **pip** (Python package manager)
- **Git**

---

## Instalasi & Setup

### 1. Clone Repository

```bash
git clone <URL_REPO_GITHUB>
cd data-lineage/Web
```

### 2. Buat Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Database PostgreSQL

Buka pgAdmin atau psql, lalu jalankan:

```sql
CREATE DATABASE data_lineage_eda;
CREATE DATABASE bot_eda;
ALTER USER postgres WITH PASSWORD 'hello123';
```

### 5. Konfigurasi Environment

Buka `data_lineage/settings.py` dan sesuaikan:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'data_lineage_eda',
        'USER': 'postgres',
        'PASSWORD': 'hello123',  # sesuaikan dengan password PostgreSQL kamu
        'HOST': 'localhost',
        'PORT': '5432',
    },
    'bot_eda': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bot_eda',
        'USER': 'postgres',
        'PASSWORD': 'hello123',  # sesuaikan dengan password PostgreSQL kamu
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Tambahkan juga Groq API Key untuk fitur AI Chatbot:

```python
GROQ_API_KEY = 'your-groq-api-key-here'
```

> 📝 **Dapatkan API Key gratis di:** https://console.groq.com

---

## Migrasi Database

### Restore dari File Dump (Recommended)

Project ini sudah menyediakan file dump database di folder `migrasi_db/`.
Restore database dengan perintah berikut:

```bash
# Restore database utama
pg_restore -U postgres -d data_lineage_eda --no-owner --no-acl --clean -v "migrasi_db/data_lineage_eda.dump"

# Restore database bot
pg_restore -U postgres -d bot_eda --no-owner --no-acl --clean -v "migrasi_db/bot_eda.dump"
```

> **Windows:** Pastikan folder bin PostgreSQL sudah ada di PATH.
> Biasanya di `C:\Program Files\PostgreSQL\16\bin`

### Jalankan Migrasi Django

Setelah restore dump, jalankan migrasi Django:

```bash
python manage.py migrate
python manage.py migrate --database=bot_eda
```

### Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

## Menjalankan Project

```bash
# Pastikan virtual environment aktif

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Jalankan server
python manage.py runserver
```

Buka browser dan akses: **http://127.0.0.1:8000**

> **Windows shortcut:** Bisa juga double-click file `run_server.bat`

---

## Fitur AI Chatbot

Akses chatbot di menu **AI Chatbot** pada sidebar.

### Contoh Pertanyaan yang Bisa Diajukan:

**Info Job:**
- "tampilkan semua job yang ada"
- "detail job CDP_DMT_WHL_EALCO_DLY_H0"
- "siapa developer dari job DPK_H0_KLN?"

**Source & Target Table:**
- "apa saja source table dari job RDBMS_CDP_NEW_RMTOOLS_DLY_H1?"
- "tampilkan target tablenya"

**Impact Analysis:**
- "dampak jika job CDP_DMT_WHL_EALCO_DLY_H0 gagal?"
- "buatkan impact analysis dari semua job yang gagal"

**Log & Status:**
- "tampilkan log upload job RDBMS_CDP_NEW_RMTOOLS_DLY_H1"
- "kapan job CDP_DMT_WHL_EALCO_DLY_H0 selesai diupload?"
- "job mana yang paling sering gagal?"

**Pertanyaan Umum:**
- "apa itu ETL?"
- "apa best practice data lineage?"

---

## Struktur Project

```
data-lineage/
├── Web/                          # Root folder aplikasi Django
│   ├── data_lineage/             # Project Django settings
│   │   ├── settings.py            # Konfigurasi utama
│   │   ├── urls.py               # URL routing utama
│   │   ├── db_router.py          # Database router untuk multi-DB
│   │   └── wsgi.py
│   ├── main/                     # App utama
│   │   ├── models.py             # Model database
│   │   ├── views.py              # View untuk semua fitur
│   │   ├── chatbot_views.py     # View untuk AI Chatbot
│   │   ├── urls.py               # URL routing main app
│   │   ├── forms.py              # Form untuk input data
│   │   ├── admin.py              # Django admin configuration
│   │   ├── utils.py             # Utility functions
│   │   ├── migrations/           # Django migrations
│   │   ├── templates/            # HTML templates
│   │   │   ├── base.html        # Template dasar
│   │   │   ├── dashboard.html   # Halaman utama
│   │   │   ├── table_list.html  # Manajemen tabel
│   │   │   ├── job_list.html    # Manajemen job
│   │   │   ├── relationship_list.html
│   │   │   ├── developer_list.html
│   │   │   ├── upload_logs.html # Monitoring upload
│   │   │   ├── chatbot.html     # AI Chatbot UI
│   │   │   └── ...
│   │   └── static/               # Static files (CSS, JS)
│   │       ├── css/
│   │       └── js/
│   ├── migrasi_db/              # Database dump files
│   │   ├── data_lineage_eda.dump
│   │   └── bot_eda.dump
│   ├── venv/                    # Virtual environment
│   ├── requirements.txt         # Python dependencies
│   └── run_server.bat            # Shortcut menjalankan server
│
├── n8n json/                     # n8n workflow JSON files
└── README.md                     # Dokumentasi project
```

---

## Konfigurasi Tambahan

### Database Router

Project ini menggunakan dua database:
1. **data_lineage_eda** - Untuk data lineage utama (tables, jobs, relationships, developers)
2. **bot_eda** - Untuk data upload logs dari n8n bot

Konfigurasi router ada di `data_lineage/db_router.py`.

### n8n Webhook

Untuk menerima lineage data dari n8n workflow, endpoint tersedia di:
- `api/n8n/lineage/` - Menerima data lineage dari n8n

### CSRF Trusted Origins

Jika ingin mengakses dari IP lain, tambahkan ke `CSRF_TRUSTED_ORIGINS` di settings.py:

```python
CSRF_TRUSTED_ORIGINS = [
    'http://172.20.10.2:8000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
```

---

## Troubleshooting

### Masalah Umum

1. **Database connection error**
   - Pastikan PostgreSQL running dan credentials benar di settings.py
   - Cek firewall mengizinkan koneksi ke port 5432

2. **Groq API error**
   - Pastikan API key valid dan aktif
   - Cek quota limit di dashboard Groq

3. **Static files tidak muncul**
   - Jalankan `python manage.py collectstatic`
   - Pastikan STATIC_ROOT dan STATICFILES_DIRS benar

4. **Import error**
   - Pastikan virtual environment aktif
   - Install ulang dependencies: `pip install -r requirements.txt`

---

## Kontributor

Tim Data Management - ODP IT Bank Mandiri