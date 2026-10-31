# VROOO Database Module (SQLite)

> **Autonomous Adaptive Traffic Signal System Berbasis Computer Vision untuk Optimalisasi Pengaturan Lalu Lintas Secara Real-Time**  
> Proyek Based Learning (PBL) Semester 5 — Teknologi Rekayasa Perangkat Lunak (TRPL), Politeknik Negeri Batam.

---

## 📌 Ringkasan Proyek

Repository ini berisi rancangan skema basis data SQLite, modul integrasi Python, skrip pengujian simulasi, serta sistem otomatisasi rekapitulasi data mingguan (ETL & *data retention*) untuk sistem **VROOO**.

Basis data ini dirancang untuk:
* Berjalan secara lokal dan hemat sumber daya pada **Raspberry Pi 4**.
* Dapat diuji coba secara langsung di lingkungan laptop pengembang (*development machine*).
* Menangani pencatatan deteksi kendaraan real-time dari model Computer Vision (YOLO/OpenCV).
* Mendukung fitur interaktif simulasi **Web Playground** (membandingkan efisiensi waktu tunggu metode adaptif vs konvensional).

---

## 🗂️ Struktur Berkas

```text
VROOO-DB/
├── schema.sql                   # Skrip DDL SQLite (tabel, indeks, relasi, seed data)
├── db_helper.py                 # Modul helper Python untuk integrasi Computer Vision & Web
├── cleanup_and_summary.py       # Skrip ETL mingguan: agregasi data + pembersihan log lama + VACUUM
├── test_system.py               # Skrip pengujian simulasi alur database end-to-end
├── vrooo.db                     # File database SQLite lokal
├── DATABASE_DOCUMENTATION.md    # Penjelasan mendalam untuk setiap tabel dan kolom
├── .gitignore                   # Konfigurasi pengabaian file Git
└── README.md                    # Dokumentasi utama proyek
```

---

## 📊 Rancangan Tabel Basis Data

Dokumentasi lengkap mengenai tipe data, *constraints*, dan relasi setiap kolom dapat dibaca di **[`DATABASE_DOCUMENTATION.md`](DATABASE_DOCUMENTATION.md)**.

Ringkasan fungsi tabel:
1. **`intersections`**: Master data persimpangan (Simpang 3, Simpang 4, Simpang 5).
2. **`approaches`**: Jalur arah mata angin (Utara, Timur, Selatan, Barat) dan kamera pengawasnya.
3. **`vehicle_detections`**: Log mentah objek deteksi Computer Vision (Motor, Mobil, Bus, Truk).
4. **`traffic_density_logs`**: Catatan periodik kepadatan kendaraan dan estimasi panjang antrean per jalur.
5. **`traffic_signal_logs`**: Riwayat keputusan lampu lalu lintas (arah yang hijau, durasi detik, dan mode kontrol).
6. **`simulation_runs`**: Penyimpanan hasil pengujian dari halaman Web Playground.
7. **`weekly_traffic_summary`**: Tabel rekapitulasi permanen mingguan sebelum log mentah dibersihkan.

---

## 🚀 Panduan Penggunaan & Pengujian di Laptop

### 1. Prasyarat
* Python 3.8+ (Modul `sqlite3` sudah bawaan dari Python standar).

### 2. Menjalankan Pengujian Otomatis
Buka terminal / PowerShell di direktori ini:
```powershell
cd "P:\TRPL SEMESTER 5\VROOO-DB"
python test_system.py
```
Skrip akan menguji:
1. Pembuatan tabel dari `schema.sql`.
2. Input data deteksi real-time dan kepadatan jalur.
3. Penyimpanan skenario simulasi Playground.
4. Pengambilan status terkini untuk antarmuka web.
5. Agregasi mingguan dan pembersihan data lama.

### 3. Menginspeksi Database dengan Antarmuka GUI
Anda dapat membuka file `vrooo.db` menggunakan aplikasi:
* **[DB Browser for SQLite](https://sqlitebrowser.org/)** (Rekomendasi)
* Ekstensi **SQLite Viewer** pada VS Code.

---

## 🍓 Implementasi pada Raspberry Pi 4

### 1. Menjadwalkan Otomatisasi Pembersihan Mingguan (Cron Job)
Di terminal Linux Raspberry Pi 4:
```bash
crontab -e
```
Tambahkan perintah berikut agar dieksekusi setiap hari Minggu jam 23:59:
```cron
59 23 * * 0 /usr/bin/python3 /home/pi/VROOO-DB/cleanup_and_summary.py >> /home/pi/VROOO-DB/cleanup.log 2>&1
```

---

## 👥 Tim Pengembang (PBL-TRPL525)

* **Manajer Proyek:** Nanda Putra Perkasa, S.Tr.Kom
* **Anggota Tim:**
  1. Pandu Tenaya (4342411002)
  2. Lucky Abdillah (4342411004)
  3. Keysya Arghinaya (4342411005)
  4. Rizky Alfiansyah (4342411022)
  5. Nauval Putra Widaya (4342411024)
