========================================================================
                      CREATOR ASSET HUB - S3 LOCALSTACK
               Panduan Menjalankan Projek (Cloud Computing Edition)
========================================================================

Projek ini adalah aplikasi web berbasis Flask untuk manajemen penyimpanan 
cloud (S3) secara lokal menggunakan LocalStack. Dibuat khusus untuk memenuhi 
persyaratan Tugas Mandiri & Tugas Besar Cloud Computing dengan arsitektur 
UI unik berbasis Grid Gallery modern.

------------------------------------------------------------------------
1. PRASYARAT SISTEM (PREREQUISITES)
------------------------------------------------------------------------
Sebelum menjalankan projek, pastikan komponen berikut sudah terinstal:
- Python 3.x
- Docker Desktop (Harus dalam keadaan menyala/Running)
- AWS CLI (Untuk eksekusi perintah pembuatan bucket secara lokal)

------------------------------------------------------------------------
2. STRUKTUR FOLDER PROJEK
------------------------------------------------------------------------
s3-creator-hub/
│
├── create_db.py            # Database dynamoDB
├── app.py                  # File utama Flask (Backend)
├── .env                    # Konfigurasi Environment & Kredensial AWS Lokal
├── requirements.txt        # Daftar dependency Python
├── readme.txt              # Panduan dokumentasi projek (File ini)
└── templates/
    └── index.html          # UI Frontend berbasis Tailwind CSS

------------------------------------------------------------------------
3. LANGKAH-LANGKAH MENJALANKAN PROJEK (STEP-BY-STEP)
------------------------------------------------------------------------

Awali buka terminal : git clone https://github.com/tuegair123/Creator-Asset-Unlimited-Gallery.git
Buat virtual environment : python -m venv .venv
Aktivasi virual environment : .\.venv\Scripts\activate

Langkah 1: Instalasi Dependency Python
Open terminal di folder 's3-creator-hub', lalu jalankan perintah:
> pip install -r requirements.txt
(Tunggu hingga proses selesai dan muncul pesan 'Successfully installed')

Langkah 2: Konfigurasi Environment (.env)
Pastikan file '.env' di direktori utama sudah berisi konfigurasi berikut:
---
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=bucket-tegar
AWS_ENDPOINT_URL=http://localhost:4566
---

Langkah 3: Menyalakan LocalStack Container
Buka Docker Desktop, lalu jalankan perintah berikut di TERMINAL BARU:
> docker run --rm -it -p 4566:4566 -p 4510-4559:4510-4559 localstack/localstack:4.4.0
(Biarkan terminal ini tetap terbuka dan menyala di background hingga berstatus 'Ready')

Langkah 4: Membuat S3 Bucket Lokal
Buka TERMINAL BARU (Tab baru), lalu eksekusi perintah AWS CLI berikut untuk
membuat bucket di dalam LocalStack:
> aws --endpoint-url=http://localhost:4566 s3 mb s3://bucket-tegar
(Jika sukses, akan muncul balasan: make_bucket: bucket-tegar)
> python create_db.py
(Buat database dynamoDB)

Langkah 5: Menjalankan Server Flask
Kembali ke terminal utama projek, lalu jalankan perintah:
> python app.py

Langkah 6: Konfigurasi stackport
Buka web browser anda
> http://localhost:8080
Masuk ke menu Settings > Endpoints > + Add Endpoint.
Isi konfigurasi berikut agar StackPort bisa menembus isolasi jaringan Docker:

Name: Localstack
Endpoint URL: http://host.docker.internal:4566 (Wajib menggunakan URL ini, jangan menggunakan localhost)
Region: us-east-1
Authentication: Pilih Manual / Static Credentials
Access Key ID: test
Secret Access Key: test
Klik Test Connection. Jika status sudah berubah menjadi Healthy (Hijau), simpan konfigurasi tersebut.

Gunakan menu Resources di sebelah kiri untuk melihat isi bucket S3 dan perubahan rekaman data pada tabel CreatorAssets di DynamoDB.

Langkah 7: Akses Aplikasi
Buka web browser Anda (Chrome/Edge/Firefox) lalu ketik URL berikut:
> http://127.0.0.1:5000


