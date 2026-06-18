# Panduan Deployment Project Data Lineage ke Server Linux Internal

Panduan ini berisi langkah-langkah detail untuk memindahkan (deploy) project **Data Lineage Dashboard** dari komputer lokal (Windows) ke server Linux di jaringan internal kantor Anda. 

Kita akan menggunakan kombinasi standar industri yang sangat tangguh: **Gunicorn** (sebagai *Application Server*) dan **Nginx** (sebagai *Reverse Proxy*).

---

> [!NOTE]
> **Asumsi Sistem Server:**
> - Sistem Operasi: **Ubuntu/Debian** atau **CentOS/RHEL** (Perintah di bawah mayoritas menggunakan syntax Ubuntu/Debian `apt`. Jika pakai CentOS, ganti `apt` dengan `yum` atau `dnf`).
> - Anda memiliki akses `sudo` (root) di server Linux tersebut.

## Langkah 1: Persiapan Server & Install Dependencies

Masuk ke server Linux Anda via SSH, kemudian jalankan update dan install beberapa package yang dibutuhkan:

```bash
sudo apt update
sudo apt install python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl -y
```

> [!WARNING]
> **Server Tanpa Internet?** 
> Karena server Anda berada di jaringan internal, jika server **tidak memiliki akses internet sama sekali**, Anda tidak bisa menjalankan perintah `apt install` atau `pip install` secara langsung. Anda harus mengunduh *package* secara manual (seperti file `.deb` atau `.whl`) dari komputer yang ada internetnya, lalu memindahkannya via Flashdisk/SCP ke server Linux untuk di-install.

## Langkah 2: Memindahkan File Project (Codebase)

Pindahkan folder project dari komputer Windows Anda ke server Linux. Anda bisa menggunakan tools seperti **WinSCP**, **FileZilla**, atau menggunakan command `scp` dari PowerShell Windows:

```bash
# Buka PowerShell/CMD di Windows Anda
scp -r d:\data_lineage\Web nama_user_linux@ip_server_linux:/home/nama_user_linux/data_lineage
```
*Pastikan Anda mengganti `nama_user_linux` dan `ip_server_linux` dengan data server yang sebenarnya.*

## Langkah 3: Setup Database (PostgreSQL)

Melihat file `settings.py` Anda, project ini menggunakan 2 database PostgreSQL (`data_lineage_eda` dan `bot_eda`). Kita perlu membuatnya di server Linux.

Masuk ke console PostgreSQL di Linux:
```bash
sudo -u postgres psql
```

Jalankan perintah SQL berikut untuk membuat user dan database (sesuaikan password jika ingin diubah):
```sql
CREATE DATABASE data_lineage_eda;
CREATE DATABASE bot_eda;
CREATE USER postgres WITH PASSWORD 'hello123';
ALTER ROLE postgres SET client_encoding TO 'utf8';
ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
ALTER ROLE postgres SET timezone TO 'Asia/Jakarta';
GRANT ALL PRIVILEGES ON DATABASE data_lineage_eda TO postgres;
GRANT ALL PRIVILEGES ON DATABASE bot_eda TO postgres;
\q
```

## Langkah 4: Setup Virtual Environment & Install Python Packages

Masuk ke folder project yang sudah di-copy tadi:
```bash
cd /home/nama_user_linux/data_lineage
```

Buat Virtual Environment (agar library Python tidak bentrok dengan bawaan sistem operasi Linux):
```bash
python3 -m venv venv
source venv/bin/activate
```
*(Tanda `(venv)` akan muncul di sebelah kiri command prompt Anda yang menandakan virtual environment sudah aktif).*

Install library yang dibutuhkan project Django:
```bash
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

## Langkah 5: Konfigurasi Django untuk Production

1. Edit file `settings.py` jika ada penyesuaian IP. (Di file Anda, `ALLOWED_HOSTS` sudah berisi `['*']` sehingga tidak akan memblokir IP server, ini aman untuk tahap internal).
2. Lakukan proses **Collectstatic** untuk mengumpulkan file CSS, JS, dan Gambar agar siap disajikan oleh Nginx:
   ```bash
   python manage.py collectstatic --noinput
   ```
3. Lakukan **Migrasi Database** untuk membentuk struktur tabel di PostgreSQL yang baru dibuat:
   ```bash
   python manage.py migrate
   python manage.py migrate --database=bot_eda
   ```
4. Buat akun Admin (Superuser) jika diperlukan:
   ```bash
   python manage.py createsuperuser
   ```

## Langkah 6: Setup Gunicorn (Application Server)

Kita akan membuat *Service* (Daemon) agar Gunicorn berjalan otomatis di background, dan akan menyala sendiri setiap kali server Linux di-restart (reboot).

Buat file service menggunakan editor teks (misal: `nano`):
```bash
sudo nano /etc/systemd/system/data_lineage.service
```

Isi dengan script berikut (Pastikan untuk mengubah teks `/home/nama_user_linux` menjadi path user Anda yang sebenarnya):

```ini
[Unit]
Description=gunicorn daemon untuk data lineage
After=network.target

[Service]
User=nama_user_linux
Group=www-data
WorkingDirectory=/home/nama_user_linux/data_lineage
ExecStart=/home/nama_user_linux/data_lineage/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/home/nama_user_linux/data_lineage/data_lineage.sock \
          data_lineage.wsgi:application

[Install]
WantedBy=multi-user.target
```

Simpan file (Jika pakai `nano`, tekan `Ctrl+X`, lalu ketik `Y`, lalu `Enter`).

Jalankan dan hidupkan service Gunicorn:
```bash
sudo systemctl start data_lineage
sudo systemctl enable data_lineage
sudo systemctl status data_lineage
```
*(Pastikan statusnya berwarna hijau dan bertuliskan **active (running)**)*.

## Langkah 7: Setup Nginx (Reverse Proxy)

Nginx berfungsi sebagai pintu gerbang web yang akan menerima *request* HTTP dari komputer pengguna (klien) dan meneruskannya ke Gunicorn.

Buat file konfigurasi Nginx:
```bash
sudo nano /etc/nginx/sites-available/data_lineage
```

Isikan blok berikut:

```nginx
server {
    listen 80;
    server_name _; # Menerima semua IP jaringan internal

    location = /favicon.ico { access_log off; log_not_found off; }
    
    # Rute untuk static files (CSS, JS)
    location /static/ {
        root /home/nama_user_linux/data_lineage;
    }
    
    # Rute untuk file uploads (jika ada)
    location /media/ {
        root /home/nama_user_linux/data_lineage;
    }

    # Semua rute lainnya diteruskan ke Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://unix:/home/nama_user_linux/data_lineage/data_lineage.sock;
    }
}
```

Aktifkan konfigurasi Nginx tersebut:
```bash
sudo ln -s /etc/nginx/sites-available/data_lineage /etc/nginx/sites-enabled
```

Hapus konfigurasi *default* Nginx agar tidak konflik:
```bash
sudo rm /etc/nginx/sites-enabled/default
```

Periksa apakah ada penulisan Nginx yang error (typo):
```bash
sudo nginx -t
```
*(Jika muncul tulisan **syntax is ok** dan **test is successful**, lanjutkan)*.

Restart Nginx untuk menerapkan perubahan:
```bash
sudo systemctl restart nginx
```

## Langkah 8: Konfigurasi Firewall (Opsional)

Jika server Linux Anda menggunakan `ufw` (Uncomplicated Firewall), buka port 80 (HTTP) dan port 22 (SSH) agar bisa diakses dari jaringan internal:

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

---

## Selesai! 🎉

Sekarang Anda sudah bisa mencoba membuka aplikasi Data Lineage ini dari komputer mana pun yang terhubung di jaringan internal kantor Anda dengan mengetikkan IP server Linux tersebut di browser.

**Contoh:** `http://192.168.1.50/` (Ganti dengan IP server Linux).

> [!TIP]
> **Cara Update Code Jika Ada Perubahan Baru (Maintenance):**
> 1. Timpa/Ganti file project yang ada di Linux dengan file terbaru dari Windows Anda via SCP/WinSCP.
> 2. Restart layanan Gunicorn untuk menerapkan kode Python/Views terbaru: `sudo systemctl restart data_lineage`
> 3. Jika ada perubahan desain/CSS, jangan lupa jalankan lagi: `python manage.py collectstatic`
