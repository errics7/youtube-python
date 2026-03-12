# YouTube Data Logger (Streamlit + Google Sheets)

Aplikasi web berbasis **Streamlit** untuk:

* Mengambil metadata video YouTube (judul, tanggal upload, views, dll)
* Mengirim data ke **Google Sheets**
* Mengelola entri **Short / VOD**
* Input hari **libur / cuti editor**

Aplikasi ini menggunakan:

* Python
* Streamlit
* YouTube Data API v3
* Google Sheets API
* Google Drive API

---

# 1. Install Python

Download Python dari:

https://www.python.org/downloads/

Saat install **WAJIB centang:**

```
Add Python to PATH
```

Cek instalasi:

```bash
python --version
```

atau

```bash
py --version
```

Jika berhasil akan muncul:

```
Python 3.x.x
```

---

# 2. Install Streamlit

Install menggunakan pip:

```bash
pip install streamlit
```

Cek apakah berhasil:

```bash
streamlit hello
```

Browser akan terbuka jika instalasi berhasil.

---

# 3. Menjalankan Aplikasi di Localhost

Masuk ke folder project:

```bash
cd nama-folder-project
```

Jalankan:

```bash
streamlit run app.py
```

atau:

```bash
python -m streamlit run app.py
```

Streamlit akan berjalan di:

```
http://localhost:8501
```

---

# 4. Menghentikan Server

Tekan:

```
CTRL + C
```

di terminal.

---

# 5. Uninstall Streamlit

Jika ingin uninstall:

```bash
pip uninstall streamlit
```

---

# 6. Setup Google Cloud

Masuk ke:

https://console.cloud.google.com/

### 1. Buat Project Baru

Klik:

```
New Project
```

Contoh:

```
youtube-data
```

---

# 7. Enable API

Masuk ke:

```
APIs & Services → Library
```

Aktifkan API berikut:

### 1️⃣ YouTube Data API v3

Digunakan untuk:

* mengambil judul video
* tanggal upload
* views
* channel

Klik:

```
Enable
```

---

### 2️⃣ Google Sheets API

Digunakan untuk:

* membaca
* menulis
* update spreadsheet

Klik:

```
Enable
```

---

### 3️⃣ Google Drive API

Digunakan untuk:

* membuka file Google Sheets melalui API

Klik:

```
Enable
```

---

# 8. Membuat YouTube API Key

Masuk ke:

```
APIs & Services → Credentials
```

Klik:

```
Create Credentials
```

Pilih:

```
API Key
```

Contoh:

```
AIzaSyXXXXXXX
```

API ini digunakan untuk:

```
YouTube Data API
```

---

# 9. Membuat Service Account

Masuk ke:

```
IAM & Admin → Service Accounts
```

Klik:

```
Create Service Account
```

Isi:

```
Name : youtube-logger
Role : Editor
```

---

# 10. Download JSON Key

Masuk ke service account → tab:

```
Keys
```

Klik:

```
Add Key → Create New Key → JSON
```

File akan terdownload.

Contoh:

```
youtube-data-xxxx.json
```

---

# 11. Beri Akses Google Sheet

Buka Google Sheet.

Klik:

```
Share
```

Tambahkan email service account:

```
xxxxx@project-id.iam.gserviceaccount.com
```

Role:

```
Editor
```

---

# 12. Setup Streamlit Secrets

Di Streamlit Cloud:

```
App Settings → Secrets
```

Tambahkan:

```toml
YOUTUBE_API_KEY="API_KEY_KAMU"

[gcp_service_account]
type="service_account"
project_id="PROJECT_ID"
private_key_id="PRIVATE_KEY_ID"
private_key="""PRIVATE_KEY"""
client_email="SERVICE_ACCOUNT_EMAIL"
client_id="CLIENT_ID"
token_uri="https://oauth2.googleapis.com/token"
```

---

# 13. Deploy ke Streamlit Cloud

Masuk ke:

https://share.streamlit.io

Langkah:

1. Login dengan GitHub
2. Pilih repository
3. Pilih file:

```
app.py
```

Klik:

```
Deploy
```

---

# 14. URL Aplikasi

Setelah deploy berhasil, aplikasi dapat diakses melalui:

```
https://nama-app.streamlit.app
```

---

# 15. Struktur Project

```
youtube-logger/
│
├── app.py
├── requirements.txt
├── README.md
└── .streamlit
     └── secrets.toml (local only)
```

---

# 16. Requirements.txt

Isi minimal:

```
streamlit
gspread
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
```

---

# 17. Catatan Keamanan

Jangan upload:

```
service-account.json
secrets.toml
API keys
```

Tambahkan ke `.gitignore`.

---

# 18. Fitur Aplikasi

✔ Preview video YouTube
✔ Kirim metadata ke Google Sheets
✔ Auto detect SHORT / VOD
✔ Input hari libur / cuti
✔ Web app berbasis Streamlit

---
