# IMPLEMENTATION_PLAN.md

Rencana perbaikan bertahap untuk **Data Lineage EDA**, disusun berdasarkan temuan aktual di `PROJECT_MEMORY.md`. Prinsip yang diikuti di seluruh rencana ini:

- Prioritaskan **stabilitas project** di atas kelengkapan fitur baru.
- Prioritaskan task dengan **ROI tertinggi** (effort rendah, dampak risiko tinggi) terlebih dulu.
- **Hindari rewrite besar** — semua task dirancang sebagai perubahan kecil dan terisolasi.
- **Hindari migrasi framework** — tetap di Django + PostgreSQL + Groq + n8n seperti sekarang.
- **Semua perubahan harus dapat di-rollback** — setiap task mencantumkan rollback plan eksplisit.
- Fokus pada **maintainability jangka panjang**, bukan hanya menutup temuan audit.

Setelah setiap task selesai, catat di bagian "Riwayat Perubahan" pada `PROJECT_MEMORY.md`.

---

## Phase 1 — Stability & Safety

Fokus: menutup risiko Critical/High yang berdampak langsung pada keamanan data dan integritas sistem, dengan perubahan sekecil mungkin.

### 1.1 Escape output HTML di chatbot untuk menutup XSS

- **Tujuan**: Mencegah nilai dari database (`table_name`, `job_name`, `log_message`) yang bisa berasal dari CSV upload atau webhook n8n eksternal dieksekusi sebagai HTML/JS aktif di browser.
- **File terdampak**: `Web/main/chatbot_views.py` (fungsi `build_html_table`, `build_detail_table`, dan semua f-string yang menyisipkan nilai dinamis ke HTML).
- **Risiko**: Rendah — perubahan bersifat aditif (menambah escaping), tidak mengubah struktur data atau flow logic.
- **Kompleksitas**: Rendah–Medium. Perlu satu fungsi escape terpusat (mis. `django.utils.html.escape`) diterapkan konsisten di semua titik interpolasi.
- **Rollback Plan**: Perubahan terisolasi pada 2 fungsi builder; revert lewat `git revert` pada commit terkait tidak berdampak ke bagian lain karena tidak ada perubahan skema/DB.
- **Expected Benefit**: Menutup satu-satunya temuan Critical dengan vektor serangan client-side yang jelas dan aktif dapat dieksploitasi.

### 1.2 Pindahkan `SECRET_KEY` dan password database ke environment variable untuk semua environment

- **Tujuan**: Menghilangkan kredensial plaintext dari kode yang ter-commit ke git.
- **File terdampak**: `Web/data_lineage/settings.py` (baris `SECRET_KEY`, konfigurasi `DATABASES['default']` dan `DATABASES['bot_eda']` untuk kondisi lokal/non-Railway).
- **Risiko**: Medium — jika env var tidak di-set di environment developer lain, aplikasi gagal start. Perlu dokumentasi `.env.example` sebagai mitigasi.
- **Kompleksitas**: Rendah. Pola untuk production (`os.environ.get(...)`) sudah ada di file yang sama, tinggal diterapkan konsisten untuk konfigurasi default/lokal.
- **Rollback Plan**: Simpan nilai default lama sebagai fallback di kode (`os.environ.get('DJANGO_SECRET_KEY', '<nilai lama sementara>')`) selama masa transisi, sehingga developer yang belum update `.env` tidak langsung down; hapus fallback setelah semua environment terkonfirmasi migrasi.
- **Expected Benefit**: Menutup temuan Critical C3; mengurangi risiko kredensial di git history untuk commit berikutnya (history lama tetap ada, tapi tidak bertambah).

### 1.3 Tambah proteksi dasar pada webhook `receive_n8n_lineage`

- **Tujuan**: Mencegah pihak tak dikenal membuat/mengubah data lineage lewat endpoint publik tanpa autentikasi.
- **File terdampak**: `Web/main/views.py` (`receive_n8n_lineage`).
- **Risiko**: Medium — jika mekanisme proteksi (mis. header shared-secret) tidak disinkronkan dengan konfigurasi n8n, workflow n8n bisa gagal mengirim data.
- **Kompleksitas**: Rendah. Validasi header sederhana (mis. `X-Webhook-Secret` dibandingkan dengan env var) sebelum memproses body request.
- **Rollback Plan**: Validasi dibungkus flag env var (mis. `WEBHOOK_SECRET_REQUIRED`) yang default `False` di awal rollout, sehingga bisa dinonaktifkan instan tanpa deploy ulang kode jika n8n belum siap.
- **Expected Benefit**: Menutup temuan High H1; mengurangi permukaan serangan pada endpoint yang saat ini bisa dipanggil siapa pun.

### 1.4 Perbaiki default fallback `DEBUG`

- **Tujuan**: Mencegah aplikasi berjalan dengan `DEBUG=True` di production jika env var `DJANGO_DEBUG` lupa di-set.
- **File terdampak**: `Web/data_lineage/settings.py:221`.
- **Risiko**: Sangat rendah — perubahan satu nilai default.
- **Kompleksitas**: Sangat rendah.
- **Rollback Plan**: Perubahan satu baris, revert langsung via `git revert`.
- **Expected Benefit**: Mencegah kebocoran stack trace/detail internal ke publik akibat kelalaian konfigurasi operasional.

### 1.5 Tambah timeout pada semua panggilan Groq API

- **Tujuan**: Mencegah worker Gunicorn (hanya 3 worker) tertahan lama jika Groq API lambat/hang.
- **File terdampak**: `Web/main/chatbot_views.py` (semua pemanggilan `client.chat.completions.create(...)`).
- **Risiko**: Rendah — menambah parameter `timeout=` pada SDK call, tidak mengubah logic.
- **Kompleksitas**: Sangat rendah.
- **Rollback Plan**: Hapus parameter `timeout` untuk kembali ke perilaku sebelumnya.
- **Expected Benefit**: Mengurangi risiko seluruh aplikasi (bukan hanya chatbot) menjadi tidak responsif akibat satu permintaan chatbot yang lambat.

### 1.6 Generic error response ke client, detail tetap di log server

- **Tujuan**: Mengurangi information disclosure dari pesan exception mentah yang dikembalikan ke client.
- **File terdampak**: `Web/main/views.py`, `Web/main/chatbot_views.py` (semua blok `except Exception as e: return JsonResponse({'error': str(e)})` dan `f"Debug error: {type(e).__name__}: {str(e)}"`).
- **Risiko**: Rendah, tapi perlu hati-hati agar pesan generik tetap cukup informatif untuk debugging via log (gunakan `logger.exception(...)` sebelum mengembalikan pesan generik).
- **Kompleksitas**: Rendah–Medium karena tersebar di banyak lokasi; bisa dikerjakan bertahap per view tanpa saling bergantung.
- **Rollback Plan**: Setiap perubahan per-blok independen; revert satu file tidak memengaruhi file lain.
- **Expected Benefit**: Mengurangi exposure detail internal ke pengguna akhir tanpa mengorbankan kemampuan debugging tim.

---

## Phase 2 — Code Quality & Maintainability

Fokus: konsistensi kode dan pembersihan dead code, tanpa mengubah behavior yang sudah berjalan.

### 2.1 Konsolidasi pemanggilan Groq client ke `get_groq_client()`

- **Tujuan**: Menghilangkan duplikasi pola instansiasi `Groq(api_key=...)` yang tersebar di banyak handler intent, menyatukan validasi & logging di satu tempat.
- **File terdampak**: `Web/main/chatbot_views.py` (semua lokasi yang memanggil `Groq(api_key=settings.GROQ_API_KEY)` langsung, ganti ke `get_groq_client()`).
- **Risiko**: Rendah — `get_groq_client()` sudah ada dan teruji dipakai di sebagian handler; perubahan bersifat penyeragaman.
- **Kompleksitas**: Rendah.
- **Rollback Plan**: Perubahan mekanis per baris pemanggilan; mudah di-revert per commit.
- **Expected Benefit**: Perbaikan bug/observability (timeout dari 1.5, error handling dari 1.6) otomatis berlaku di semua handler tanpa duplikasi maintenance.

### 2.2 Hapus atau isolasi `Web/utils/seeding.py` yang usang

- **Tujuan**: Mencegah kebingungan atau error jika script ini tidak sengaja dijalankan, karena mereferensikan model (`ParentChildRelationship`, `ColumnUsedInRelationship`) yang sudah dihapus.
- **File terdampak**: `Web/utils/seeding.py`.
- **Risiko**: Sangat rendah — file ini sudah tidak fungsional saat ini.
- **Kompleksitas**: Sangat rendah.
- **Rollback Plan**: File dipindah ke folder `archive/` (bukan dihapus permanen) sehingga histori tetap tersedia dan bisa dikembalikan jika ternyata masih dirujuk di suatu tempat.
- **Expected Benefit**: Mengurangi dead code yang menyesatkan kontributor baru.

### 2.3 Bersihkan `main/migrations/backup/`

- **Tujuan**: Menghilangkan file migrasi lama yang membingungkan (terlihat seperti bagian migrations resmi padahal tidak dieksekusi Django).
- **File terdampak**: `Web/main/migrations/backup/0011-0014...py`.
- **Risiko**: Rendah, dengan syarat dipastikan dulu tidak ada referensi/import ke file-file ini dari kode lain (perlu grep cepat sebelum eksekusi).
- **Kompleksitas**: Sangat rendah.
- **Rollback Plan**: Pindahkan (bukan hapus) ke folder di luar `main/` (mis. `docs/archive/migrations_backup/`) agar riwayat schema evolution tetap terdokumentasi tapi tidak berada di lokasi yang membingungkan.
- **Expected Benefit**: Struktur folder migrations lebih jelas bagi kontributor baru.

### 2.4 Selaraskan dokumentasi `GROQ_MODEL` antara README dan `settings.py`

- **Tujuan**: Menghilangkan kebingungan model LLM apa yang sebenarnya aktif.
- **File terdampak**: `README.md`, `Web/data_lineage/settings.py:181` (opsional: cukup update dokumentasi tanpa ubah default kode jika default saat ini sudah sesuai kebutuhan produksi).
- **Risiko**: Sangat rendah — perubahan dokumentasi murni.
- **Kompleksitas**: Sangat rendah.
- **Rollback Plan**: Revert dokumentasi via git.
- **Expected Benefit**: Mengurangi kesalahan asumsi biaya/perilaku API saat troubleshooting atau onboarding.

### 2.5 Setup infrastruktur testing (tanpa menulis test besar dulu)

- **Tujuan**: Menyediakan fondasi agar test bisa mulai ditulis secara bertahap.
- **File terdampak**: `Web/requirements.txt` (tambah `pytest`, `pytest-django`), file konfigurasi baru `pytest.ini` atau `setup.cfg` minimal.
- **Risiko**: Sangat rendah — penambahan dependency dev, tidak memengaruhi kode aplikasi.
- **Kompleksitas**: Rendah.
- **Rollback Plan**: Hapus dependency dari `requirements.txt` jika bermasalah; tidak ada perubahan pada kode produksi.
- **Expected Benefit**: Membuka jalan untuk Task 2.6 dan mengurangi biaya psikologis "mulai testing dari nol" di masa depan.

### 2.6 Tulis unit test untuk area berisiko tinggi tanpa test coverage

- **Tujuan**: Mulai menutup celah test coverage di 3 area yang paling kompleks dan paling sering berubah: BFS lineage traversal (`api_get_lineage`), parser webhook n8n (`receive_n8n_lineage`), dan fungsi ekstraksi konteks chatbot (`extract_active_context`, `resolve_question`).
- **File terdampak**: File test baru di `Web/main/tests.py` atau dipecah ke `Web/main/tests/` (tidak mengubah kode aplikasi, murni menambah test).
- **Risiko**: Sangat rendah untuk kode produksi (test tidak mengubah behavior), tapi berpotensi menemukan bug tersembunyi yang perlu ditriase terpisah.
- **Kompleksitas**: Medium — perlu memahami fixture data dan koneksi dual-database untuk test yang menyentuh `bot_eda`.
- **Rollback Plan**: Test bersifat aditif murni; tidak ada risiko rollback terhadap kode aplikasi.
- **Expected Benefit**: Regresi pada 3 area paling rapuh (M4 di `PROJECT_MEMORY.md`) mulai bisa terdeteksi otomatis.

---

## Phase 3 — Architecture Improvements

Fokus: perbaikan arsitektur inkremental yang tidak mengubah pola dual-database atau struktur app secara fundamental.

### 3.1 Tambah rate limiting pada endpoint chatbot

- **Tujuan**: Mencegah penyalahgunaan endpoint `/chatbot/ask/` yang memanggil Groq API berbayar tanpa batas, terutama karena belum ada autentikasi.
- **File terdampak**: `Web/main/chatbot_views.py` (`chatbot_ask`), `Web/main/urls.py`.
- **Risiko**: Medium — rate limit yang terlalu ketat bisa mengganggu penggunaan wajar; perlu threshold yang wajar dan feedback jelas ke user saat limit tercapai.
- **Kompleksitas**: Medium (memilih library/pendekatan throttle sederhana berbasis IP/session).
- **Rollback Plan**: Middleware/decorator rate-limit dibungkus flag env var agar bisa dinonaktifkan instan tanpa deploy ulang.
- **Expected Benefit**: Melindungi biaya API dan availability server dari potensi penyalahgunaan endpoint publik.

### 3.2 Dokumentasikan kontrak data webhook n8n secara eksplisit

- **Tujuan**: Mengurangi risiko inkonsistensi skema antara jalur masuk data n8n (webhook vs akses langsung ke `bot_eda`).
- **File terdampak**: Dokumentasi baru (mis. `docs/n8n_contract.md`), tidak mengubah kode.
- **Risiko**: Sangat rendah — perubahan dokumentasi murni.
- **Kompleksitas**: Rendah, tapi butuh koordinasi dengan pemilik workflow n8n untuk memastikan akurasi.
- **Rollback Plan**: Tidak relevan (dokumentasi tidak memengaruhi runtime).
- **Expected Benefit**: Perubahan skema di masa depan (baik dari sisi Django maupun n8n) punya rujukan bersama, mengurangi risiko breaking change silent.

### 3.3 Tambah audit logging untuk aksi mutasi (create/update/delete)

- **Tujuan**: Menyediakan jejak audit siapa melakukan apa, terutama setelah autentikasi mulai diaktifkan (lanjutan dari Phase 1 jika auth ditambahkan).
- **File terdampak**: `Web/main/views.py` (view create/edit/delete untuk Table, JobDetail, JobDeveloper, Relationship), konfigurasi `LOGGING` di `settings.py`.
- **Risiko**: Rendah — logging bersifat aditif, tidak mengubah alur bisnis.
- **Kompleksitas**: Medium — perlu keputusan format log (file terpisah vs tabel audit) dan konsistensi penerapan di semua view mutasi.
- **Rollback Plan**: Logging tambahan dapat dinonaktifkan via level logger tanpa mengubah kode; jika diimplementasi sebagai model DB, migration dapat di-reverse.
- **Expected Benefit**: Investigasi insiden data (mis. penghapusan tak sengaja) menjadi mungkin, terutama krusial karena saat ini tidak ada auth yang membatasi siapa bisa menghapus apa.

### 3.4 Evaluasi (bukan eksekusi) pemisahan `main` app menjadi beberapa Django app

- **Tujuan**: Menyiapkan dasar keputusan untuk refactor struktural di masa depan tanpa mengeksekusinya sekarang.
- **File terdampak**: Tidak ada perubahan kode — hasil evaluasi didokumentasikan di `PROJECT_MEMORY.md`.
- **Risiko**: Tidak ada (task ini murni analisis).
- **Kompleksitas**: Rendah untuk evaluasi; refactor aktualnya (jika disetujui nanti) akan High.
- **Rollback Plan**: Tidak relevan.
- **Expected Benefit**: Keputusan refactor besar (jika dan kapan dilakukan) berdasarkan data, bukan dorongan sesaat — sejalan dengan prinsip "hindari rewrite besar" di rencana ini.

---

## Phase 4 — Performance Improvements

Fokus: optimasi yang ditargetkan pada bottleneck yang sudah teridentifikasi, bukan optimasi spekulatif.

### 4.1 Optimalkan query chatbot — hindari load seluruh dataset per-request

- **Tujuan**: Mengurangi beban query pada `chatbot_ask` yang saat ini memuat seluruh `JobDetail`, `Relationship`, `Table`, `JobUploadSessions` ke memori Python di setiap request chat, termasuk loop N+1 untuk `sessions_with_done`.
- **File terdampak**: `Web/main/chatbot_views.py` (`chatbot_ask`, terutama blok `all_jobs_raw`, `all_relationships`, `sessions_with_done`).
- **Risiko**: Medium — perubahan pada logic query bisa mengubah hasil intent tertentu jika tidak hati-hati; perlu dites terhadap semua contoh pertanyaan yang didokumentasikan di README sebelum dianggap selesai (idealnya didukung test dari Task 2.6).
- **Kompleksitas**: Medium–High — perlu query bertarget berdasarkan intent yang sudah terdeteksi, bukan mengganti keseluruhan arsitektur data-loading sekaligus. Disarankan dikerjakan per-intent secara bertahap, dimulai dari intent yang paling sering dipakai.
- **Rollback Plan**: Kerjakan per-intent sebagai commit terpisah; setiap commit dapat di-revert independen tanpa memengaruhi intent lain karena setiap blok `elif intent == ...` relatif independen satu sama lain.
- **Expected Benefit**: Mengurangi waktu respons chatbot dan beban database seiring data bertambah (mitigasi H2), tanpa mengubah pola arsitektur "LLM hanya untuk narasi" yang sudah baik.

### 4.2 Evaluasi kebutuhan reset sequence manual pada delete

- **Tujuan**: Menilai apakah `setval(pg_get_serial_sequence(...))` yang dijalankan di setiap `delete_table`/`delete_job` benar-benar diperlukan, mengingat berpotensi race condition pada concurrent delete/insert.
- **File terdampak**: `Web/main/views.py` (`delete_table`, `delete_job`).
- **Risiko**: Medium — mengubah/menghapus logic ini tanpa pemahaman penuh alasan awal penambahannya bisa memunculkan masalah ID yang tidak terduga di UI (jika UI bergantung pada urutan ID tertentu).
- **Kompleksitas**: Rendah untuk evaluasi, Medium jika keputusan akhirnya mengubah logic.
- **Rollback Plan**: Jika logic diubah, simpan versi lama sebagai comment/flag sementara agar mudah dikembalikan jika muncul masalah.
- **Expected Benefit**: Mengurangi operasi database ekstra per delete jika terbukti tidak diperlukan, dan mengurangi potensi race condition.

---

## Phase 5 — Long Term Improvements

Fokus: perbaikan yang bernilai tinggi tapi butuh effort/koordinasi lebih besar, dieksekusi setelah Phase 1–4 stabil dan hanya jika didukung kebutuhan nyata (bukan optimisasi spekulatif).

### 5.1 Tambah CI/CD pipeline dasar (lint + test gate sebelum deploy)

- **Tujuan**: Menangkap regresi dan kredensial ter-commit secara otomatis sebelum sampai ke production, memanfaatkan test infra dari Task 2.5/2.6.
- **File terdampak**: File konfigurasi CI baru (di luar kode aplikasi), tidak mengubah `Web/`.
- **Risiko**: Rendah — tidak memengaruhi runtime aplikasi, hanya proses deployment.
- **Kompleksitas**: Medium.
- **Rollback Plan**: Pipeline CI dapat dinonaktifkan tanpa memengaruhi kemampuan deploy manual yang sudah ada (`build.sh`, `railway.toml`).
- **Expected Benefit**: Mengurangi risiko berulangnya insiden seperti kredensial ter-commit (C3), diverifikasi otomatis di setiap PR.

### 5.2 Tambah retry/backoff dan graceful degradation untuk panggilan Groq API

- **Tujuan**: Chatbot tidak gagal total (pesan "Debug error: ...") saat Groq API sedang rate-limited atau downtime sesaat.
- **File terdampak**: `Web/main/chatbot_views.py` (setelah konsolidasi ke `get_groq_client()` di Task 2.1, retry bisa diterapkan di satu tempat).
- **Risiko**: Rendah–Medium — retry yang tidak dibatasi bisa memperlambat response time saat Groq benar-benar down; perlu batas percobaan dan timeout total yang wajar.
- **Kompleksitas**: Medium.
- **Rollback Plan**: Retry logic dibungkus fungsi terpisah yang bisa dinonaktifkan (kembali ke single-attempt) tanpa mengubah pemanggil.
- **Expected Benefit**: Pengalaman pengguna lebih baik saat gangguan API eksternal sesaat, mengurangi keluhan "chatbot error" yang sebenarnya disebabkan pihak ketiga.

### 5.3 Mitigasi prompt injection ringan dari data user

- **Tujuan**: Mengurangi kemungkinan nama job/tabel yang berisi teks instruksi memengaruhi output narasi LLM.
- **File terdampak**: `Web/main/chatbot_views.py` (semua fungsi yang membangun `*_context` sebelum dikirim ke Groq).
- **Risiko**: Rendah — penambahan delimiter/escaping pada data yang masuk prompt, tidak mengubah logic bisnis.
- **Kompleksitas**: Rendah–Medium.
- **Rollback Plan**: Perubahan pada format string prompt, mudah di-revert per commit tanpa efek samping ke data.
- **Expected Benefit**: Mengurangi risiko output chatbot yang menyesatkan akibat data yang sengaja dirancang untuk memanipulasi narasi LLM.

### 5.4 Eksekusi pemisahan `main` app menjadi beberapa Django app (kondisional)

- **Tujuan**: Menindaklanjuti hasil evaluasi Task 3.4 **hanya jika** kecepatan fitur sudah stabil dan hasil evaluasi mendukung.
- **File terdampak**: Seluruh `Web/main/` (restrukturisasi besar — `views.py`, `chatbot_views.py`, `models.py`, `urls.py`, `templates/`).
- **Risiko**: High — perubahan struktural besar dengan potensi merge conflict tinggi, terutama karena belum ada test coverage penuh (bergantung pada progres Phase 2).
- **Kompleksitas**: High.
- **Rollback Plan**: Wajib dikerjakan di branch terpisah dengan checkpoint per-app yang dipisah (mis. satu app per PR), sehingga setiap tahap bisa di-revert independen; tidak dilakukan sebagai satu rewrite besar sekaligus (selaras dengan prinsip "hindari rewrite besar").
- **Expected Benefit**: Maintainability jangka panjang meningkat signifikan untuk file yang saat ini >1700 baris, dengan syarat dieksekusi bertahap dan didukung test coverage yang memadai dari Phase 2.

