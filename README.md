# WargaIn v2 — Tata Kelola Rukun Warga & Rukun Tetangga Mandiri

> **Platform Tata Kelola Kependudukan, Layanan Surat Digital Berbasis QR Autentikasi, dan Kas Transparan Tingkat RT/RW.**  
> *Memenuhi Standar UU No. 27/2022 tentang Pelindungan Data Pribadi (UU PDP), Desain Tri-Axial Terisolasi, dan Bebas AI Slop.*

---

## 1. Ikhtisar & Landasan Desain

WargaIn v2 adalah pembangunan ulang (*rebuild*) komprehensif dari sistem administrasi lingkungan rukun warga di Indonesia dengan fokus pada **kebutuhan nyata akar rumput (*grassroots*)**:

1. **Pemisahan Tri-Axial (Tri-Axial Relational Isolation)**:
   - **Axis 1 (Siapa / Entitas Biologis)**: `IdentitasOrang` (Blind Index HMAC) $\to$ `Warga` (Tersandi AES-256-GCM).
   - **Axis 2 (Tercatat di mana / Catatan Sipil)**: `KartuKeluarga` $\to$ `KeanggotaanKK`.
   - **Axis 3 (Tinggal di mana / Keberadaan Fisik)**: `Hunian` (Terikat simpul RT) $\to$ `Domisili`.
   *Dampak Nyata:* Mahasiswa atau pekerja yang menyewa kos/kontrakan dengan KTP luar daerah tetap dapat terdata dalam sensus keamanan, sampah, dan iuran lingkungan tanpa memaksa pembuatan Kartu Keluarga palsu atau manipulasi data catatan sipil.

2. **Kepatuhan Penuh UU PDP No. 27/2022**:
   - NIK tersimpan dalam enkripsi simetris AES-256-GCM dengan nonce 96-bit dan autentikasi tag 128-bit.
   - Pencarian NIK presisi menggunakan **HMAC-SHA256 Blind Index** (database zero-knowledge terhadap NIK mentah).
   - Tampilan default selalu disamarkan (*masked*, misal: `327301******0001`).
   - Pembukaan NIK mentah (*unmask*) wajib mencantumkan alasan kedinasan dan langsung terekam permanen dalam `AuditLog` yang berstatus *append-only* (dilarang hapus/ubah).

3. **Bebas AI Slop & Penundaan Fitur Bansos**:
   - Tidak menggunakan gimmick bot AI yang berhalusinasi.
   - **Scoring Bansos secara eksplisit DITUNDA** dari rilis inti untuk mencegah kecurigaan sosial dan tuduhan pilih kasih di antara warga.

4. **Layanan Surat Pengantar QR & Kuitansi WhatsApp**:
   - Surat pengantar resmi (SKCK, KTP, KK, Domisili, Kematian) dengan alur persetujuan Ketua RT $\to$ Ketua RW.
   - Dilengkapi QR Code autentikasi publik yang dapat dipindai oleh pihak kelurahan/kepolisian tanpa perlu login.
   - Meja kas & iuran satu klik dengan tautan pesan bukti pembayaran resmi siap kirim ke WhatsApp warga.

---

## 2. Struktur Dokumentasi Standar Internasional (`docs/`)

Seluruh arsitektur, spesifikasi teknis, dan proses bisnis telah didokumentasikan secara terpisah sesuai standar industri internasional pada folder [`docs/`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs):

| Kode Dokumen | Nama Dokumen | Standar Kepatuhan | Deskripsi |
| :--- | :--- | :--- | :--- |
| [`00_OVERVIEW.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/00_OVERVIEW.md) | Project Charter & Requirements | ISO/IEC/IEEE 29148:2018 | Visi produk, prinsip arsitektur, matriks akses RBAC, dan peta jalan rilis. |
| [`01_ARCHITECTURE.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/01_ARCHITECTURE.md) | System Architecture & C4 Models | ISO/IEC/IEEE 42010 | Diagram C4 Level 1-3, perutean hierarki wilayah nasional, isolasi multi-tenant, dan rollup data kecil ($N < 5$). |
| [`02_ERD_AND_DATA_DICTIONARY.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/02_ERD_AND_DATA_DICTIONARY.md) | Data Model & Dictionary | ISO/IEC 11179 | 14 entitas lengkap dalam diagram Mermaid ERD beserta kamus data fisik, tipe, indeks, dan kebijakan relasi. |
| [`03_BUSINESS_PROCESS.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/03_BUSINESS_PROCESS.md) | Business Process Specifications | BPMN 2.0 / ISO 19510 | Alur kerja onboarding tri-axial, siklus mutasi kependudukan, penerbitan surat pengantar & verifikasi QR, kas iuran WhatsApp, dan protokol transfer antar-RW. |
| [`04_SECURITY_AND_PDP_COMPLIANCE.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/04_SECURITY_AND_PDP_COMPLIANCE.md) | Security & Data Protection | UU No. 27/2022 & ISO 27001 | Formula matematis HMAC blind index, AES-256-GCM cipher payload, aturan masking, dan audit logging pembacaan PII. |
| [`05_API_SPECIFICATION.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/05_API_SPECIFICATION.md) | RESTful API Specification | OpenAPI 3.1 & RFC 7807 | Skema endpoint JSON, autentikasi, dan respons format kesalahan standar. |
| [`06_FEATURES_SPECIFICATION.md`](file:///c:/Workspace/03_My_Businesses/Zyntaxera/2026_Wargain/03_Workspace/Wargain_Rebuild/docs/06_FEATURES_SPECIFICATION.md) | Feature Functional Specs | IEEE Requirements Spec | Rincian modul dashboard, buku register warga, surat QR, kuitansi digital, dan justifikasi penundaan bansos. |

---

## 3. Susunan Kode Program & Modular Apps

Proyek ini dibangun menggunakan **Django 5.2**, **PostgreSQL 18**, dan antarmuka **Tailwind CSS Mobile-First Responsive**:

```
Wargain_Rebuild/
├── manage.py
├── requirements.txt
├── run-dev.bat                      <-- Skrip satu-klik peluncuran lokal
├── .env                             <-- Konfigurasi database & kunci kriptografi
├── config/                          <-- Pengaturan inti proyek Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                            <-- Domain Aplikasi Modular
│   ├── wilayah/                     <-- Simpul hierarki wilayah (Provinsi s/d RT) & profil pengurus
│   ├── kependudukan/                <-- IdentitasOrang (HMAC blind index), Warga (AES-GCM), KartuKeluarga
│   │   └── crypto.py                <-- Mesin kriptografi UU PDP
│   ├── hunian/                      <-- Hunian fisik (rumah/kos) & relasi domisili temporal
│   ├── mutasi/                      <-- Mutasi kependudukan (Lahir, Meninggal, Pindah Masuk/Keluar)
│   ├── layanan/                     <-- Surat Pengantar & Log Verifikasi QR
│   ├── iuran/                       <-- Pos Kas, Tagihan Bulanan Hunian, Kuitansi Pembayaran
│   ├── audit/                       <-- Append-only Audit Log UU PDP
│   └── portal/                      <-- Tampilan antarmuka web responsif & meja operasional pengurus
├── templates/                       <-- Berkas template HTML Tailwind CSS
│   ├── base.html
│   └── portal/
│       ├── login.html               <-- Halaman login dengan tombol akun demo cepat
│       ├── dashboard.html           <-- Pusat komando aksi cepat & indikator iuran
│       ├── warga_list.html          <-- Buku register kependudukan terlindungi
│       ├── warga_form.html          <-- Formulir pendaftaran warga baru terintegrasi hunian
│       ├── warga_detail.html        <-- Profil warga dengan modal unmask NIK terevaluasi audit
│       ├── hunian_list.html         <-- Daftar hunian & persebaran penghuni kos
│       ├── surat_list.html          <-- Antrean persetujuan surat pengantar RT/RW
│       ├── surat_form.html          <-- Pengajuan surat layanan warga
│       ├── surat_print.html         <-- Tata letak cetak resmi Surat Pengantar Standar Kemendagri
│       ├── surat_verifikasi.html    <-- Halaman verifikasi publik pemindai QR Code
│       ├── iuran_desk.html          <-- Meja kas iuran bulanan warga satu klik
│       └── kuitansi.html            <-- Kuitansi digital dengan tombol bagikan WhatsApp
└── docs/                            <-- Dokumentasi standar internasional
```

---

## 4. Cara Menjalankan Aplikasi

### Persyaratan Lingkungan
- **Python**: $\ge 3.12$
- **PostgreSQL**: $\ge 17$ atau $18$ (berjalan pada `localhost:5432`)
- **Web Browser**: Chrome, Edge, Safari, atau Firefox

### Menjalankan dengan Cepat (Windows)
Cukup jalankan berkas batch:
```cmd
run-dev.bat
```
Skrip ini akan secara otomatis:
1. Memastikan migrasi database terpasang.
2. Membuka peramban ke `http://127.0.0.1:8000`.
3. Menjalankan server Django development.

### Menjalankan secara Manual via Terminal
```powershell
# 1. Masuk ke direktori
cd "C:\Workspace\03_My_Businesses\Zyntaxera\2026_Wargain\03_Workspace\Wargain_Rebuild"

# 2. Aktifkan virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Jalankan migrasi database
python manage.py migrate

# 4. Jalankan seeder data percontohan (RW 07 Sukaluyu)
python manage.py seed_pilot_data

# 5. Jalankan server pengembang
python manage.py runserver 0.0.0.0:8000
```

---

## 5. Matriks Hak Akses & Akun Percontohan (*RBAC Access Matrix*)

Sistem menerapkan pemisahan tugas (*Segregation of Duties*) dan proteksi privasi warga yang ketat:

| Fitur / Endpoint | Warga Biasa (`warga_budi`) | Bendahara RT (`rt01_bendahara`) | Ketua RT (`rt01_ketua`) | Ketua RW (`rw07_ketua`) | Admin Pusat (`admin`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Beranda / Dashboard** | **Portal Warga Mandiri** | Meja Operasional RT 01 | Pusat Komando RT 01 | Pusat Komando RW 07 | Komando Penuh |
| **Buku Register Warga** | ⛔ *Ditolak (403/Redirect)* | 👁️ Hanya RT 01 | ✏️ Kelola RT 01 | 👁️ Seluruh RW 07 | ✏️ Kelola Nasional |
| **Buka NIK Lengkap (Unmask)** | ⛔ *Dilarang Keras* | ⛔ *Dilarang* | 👁️ Dicatat Audit Log | 👁️ Dicatat Audit Log | 👁️ Dicatat Audit Log |
| **Data Hunian & Kos** | ⛔ *Ditolak (403/Redirect)* | 👁️ Hunian RT 01 | ✏️ Kelola RT 01 | 👁️ Seluruh RW 07 | ✏️ Kelola Nasional |
| **Daftar Surat Pengantar** | 👁️ Hanya Surat Sendiri | 👁️ Arsip Surat RT 01 | ✏️ Antrean RT 01 | ✏️ Antrean RW 07 | ✏️ Seluruh Surat |
| **Persetujuan Surat (RT)** | ⛔ *Tidak Berwenang* | ⛔ *Tidak Berwenang* | ✅ **Setujui RT** | ✅ Bypass RT | ✅ Superuser |
| **Penerbitan Surat & QR (RW)** | ⛔ *Tidak Berwenang* | ⛔ *Tidak Berwenang* | ⛔ Menunggu RW | ✅ **Terbitkan & QR** | ✅ Superuser |
| **Pengajuan Surat Baru** | ✅ Untuk Diri / Keluarga | ✅ Untuk Warga RT 01 | ✅ Untuk Warga RT 01 | ✅ Untuk Warga RW 07 | ✅ Untuk Semua Warga |
| **Meja Kas & Catat Pembayaran** | ⛔ *Ditolak (403/Redirect)* | ✅ **Terima & Kuitansi** | ✅ Terima & Kuitansi | 👁️ Pantau Kas RW | ✅ Superuser |
| **Status Iuran Rumah Saya** | ✅ Hunian Sendiri (No. 14A) | 👁️ Meja Kas RT 01 | 👁️ Meja Kas RT 01 | 👁️ Meja Kas RW 07 | 👁️ Meja Kas Nasional |

### Kredensial Akun Uji Coba:
- **Ketua RT 01:** `rt01_ketua` / `wargain2026`
- **Bendahara RT 01:** `rt01_bendahara` / `wargain2026`
- **Ketua RW 07:** `rw07_ketua` / `wargain2026`
- **Warga Mandiri:** `warga_budi` / `wargain2026`
- **Admin Utama:** `admin` / `admin1234`

---

## 6. Verifikasi & Pengujian Otomatis

Proyek dilengkapi dengan pengujian unit dan integrasi (*end-to-end*) otomatis yang mencakup mesin kriptografi, model relasional tri-axial, alur penerbitan surat QR, meja kas iuran, dan isolasi hak akses antar-peran:

```powershell
python manage.py test
```

Hasil verifikasi:
```text
Creating test database for alias 'default'...
...........
----------------------------------------------------------------------
Ran 11 tests in 10.456s

OK
Destroying test database for alias 'default'...
Found 11 test(s).
System check identified no issues (0 silenced).
```
