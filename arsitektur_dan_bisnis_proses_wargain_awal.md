# Arsitektur, Fitur, dan Bisnis Proses Platform WargaIn

Dokumen ini memetakan seluruh sistem **WargaIn** (Sistem Informasi Pendataan & Administrasi Warga Tingkat RW) yang sedang berjalan saat ini, mencakup arsitektur boundary, entitas data, alur bisnis proses, serta aturan logika kependudukan.

---

## 1. Arsitektur Boundary (Pemisahan Publik vs Privat)

WargaIn dirancang dengan batasan privasi data yang ketat (*Privacy by Design*):

```mermaid
flowchart TD
    subgraph Publik ["🌐 ZONA PUBLIK (Tanpa Autentikasi)"]
        P1["Beranda (/)<br>• Ringkasan Makro RW<br>• Pengumuman Terbaru<br>• Agenda Terdekat"]
        P2["Informasi RW (/informasi)<br>• Alur Layanan Surat<br>• Regulasi Keamanan<br>• Struktur Organisasi RW<br>• Jadwal Posyandu & Kerja Bakti"]
        P3["Statistik Publik (/statistik)<br>• Agregat Kependudukan<br>• Distribusi RT & Usia<br>• Tanpa NIK / Data Sensitif"]
    end

    subgraph AuthLayer ["🛡️ SECURITY BOUNDARY (Middleware auth + admin.rw)"]
        MW["Validasi Session + Akun Aktif + Relasi rw_id"]
    end

    subgraph AdminZone ["🔒 ZONA ADMINISTRASI RW (Khusus Pengurus RW)"]
        A1["Dashboard Admin"]
        A2["Data Kartu Keluarga (KK)"]
        A3["Data Warga (Individu)"]
        A4["Status Tinggal & Inang Kos"]
        A5["Manajemen Pengurus RW"]
        A6["Manajemen Konten Publik"]
        A7["Manajemen Agenda Kegiatan"]
        A8["Audit Trail & Riwayat Perubahan"]
        A9["Laporan & Rekapitulasi Data"]
    end

    WargaPublik["Warga Umum / Tamu"] --> Publik
    AdminUser["Pengurus RW (Login)"] --> AuthLayer --> AdminZone
```

---

## 2. Entitas Data Utama & Relasinya

```mermaid
erDiagram
    RW ||--o{ USER : "memiliki admin"
    RW ||--o{ KARTU_KELUARGA : "mewadahi"
    RW ||--o{ WARGA : "mencakup"
    RW ||--o{ PENGURUS_RW : "memiliki susunan"
    RW ||--o{ KONTEN_PUBLIK : "mempublikasikan"
    RW ||--o{ AGENDA_KEGIATAN : "menjadwalkan"

    KARTU_KELUARGA ||--o{ WARGA : "anggota keluarga utama"
    KARTU_KELUARGA ||--o{ STATUS_TINGGAL : "sebagai inang kos"
    WARGA ||--o{ STATUS_TINGGAL : "memiliki riwayat tinggal"
    WARGA ||--o{ RIWAYAT_PERUBAHAN : "memiliki catatan mutasi"
```

### Detail Entitas:
1. **`RW`**: Basis wilayah otonom (kode RW, nama RW, kelurahan, kecamatan, kota, provinsi, alamat sekretariat).
2. **`Users`**: Akun login pengurus (`admin_rw`, `super_admin`) yang terikat ke `rw_id`.
3. **`KartuKeluarga`**: Entitas kartu keluarga dengan nomor KK 16 digit, RT/RW, status rumah (milik/sewa/kontrak), dan penetapan kepala keluarga.
4. **`Warga`**: Entitas individu warga (NIK 16 digit, nama lengkap, gender, tempat/tgl lahir, agama, pekerjaan, pendidikan, status keluarga).
5. **`StatusTinggal`**: Status kependudukan aktif dan historis (Tetap, Kontrak, Kos, Pendatang, Sementara, Penghuni Kos).
6. **`PengurusRw`**: Daftar pejabat RW (Ketua, Sekretaris, Bendahara, Seksi Keamanan, Karang Taruna).
7. **`KontenPublik`**: Informasi publik berkategori (Pengumuman, Layanan Surat, Keamanan Lingkungan, Informasi Umum).
8. **`AgendaKegiatan`**: Jadwal kegiatan (Posyandu balita/lansia, Kerja Bakti, Rapat Pengurus).
9. **`RiwayatPerubahan`**: Catatan mutasi (Lahir, Meninggal, Pindah Masuk, Pindah Keluar, Perubahan Data KK).

---

## 3. Alur Bisnis Proses (Proses Inti)

### A. Pendataan Warga Inti vs Penghuni Kos (Revisi Logika Kependudukan)

Salah satu keunggulan logika WargaIn saat ini adalah **pemisahan anggota KK kandung dengan warga kos**:

```mermaid
flowchart TD
    StartInput["Admin menginput Data Warga Baru"] --> CekTipe{"Tipe Warga?"}
    
    CekTipe -- "Keluarga Inti" --> WargaKK["kartu_keluarga_id: Terisi ID KK<br>status_keluarga: Kepala/Istri/Anak/dll.<br>status_tinggal: Tetap / Kontrak"]
    WargaKK --> RelasiInti["Masuk ke Anggota Keluarga Utama di Kartu Keluarga"]

    CekTipe -- "Penghuni Kos" --> WargaKos["kartu_keluarga_id: NULL (Tidak masuk KK)<br>status_keluarga: NULL / Kosong<br>jenis_status_tinggal: penghuni_kos<br>kartu_keluarga_inang_id: Terhubung ke KK Pemilik Kos"]
    WargaKos --> RelasiInang["Ditampilkan pada Tab 'Penghuni Kos' di KK Pemilik Kos"]
```

**Tujuan Aturan Ini:**
- Menghindari manipulasi data sensus (anak kos tidak boleh tercatat sebagai anggota keluarga sah dari pemilik kos).
- Memastikan pemilik kos tetap bertanggung jawab secara administratif atas data penyewa yang tinggal di lingkungannya.
- Statistik agregat RW dapat membedakan secara presisi antara warga ber-KTP setempat vs pendatang kos.

---

### B. Alur Publikasi Informasi & Agenda RW

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Pengurus RW
    participant Modul as Modul Admin
    participant DB as PostgreSQL
    participant Publik as Portal Warga (/informasi & /)

    Admin->>Modul: Buat Pengumuman / Agenda Baru (Pilih Kategori/Jenis)
    Admin->>Modul: Set is_publik = TRUE, is_aktif = TRUE
    Modul->>DB: Simpan ke tabel konten_publik / agenda_kegiatan
    DB-->>Publik: Otomatis tampil di Beranda dan Halaman Informasi Publik
    Note over Publik: Warga dapat melihat jadwal posyandu, kerja bakti,<br/>dan info surat pengantar tanpa perlu login
```

---

### C. Alur Mutasi & Audit Trail Kependudukan

Setiap ada mutasi kependudukan (contoh: warga meninggal dunia atau pindah domisili keluar):
1. **Pembaruan Status Warga**: Status warga diubah (`status_hidup = meninggal` atau `is_aktif = false`).
2. **Pencatatan Status Tinggal**: Record pada `status_tinggal` diberi `tanggal_keluar` dan `status_aktif = false`.
3. **Perekaman Audit Trail**: Sistem menulis log ke `riwayat_perubahan` (`data_lama` vs `data_baru`) lengkap dengan identitas admin yang mengeksekusi dan alasan mutasi.
4. **Otomasi Kepala Keluarga**: Jika warga yang meninggal/pindah adalah Kepala Keluarga pada KK terkait, sistem meminta penunjukan Kepala Keluarga pengganti.

---

## 4. Matriks Fitur Lengkap Saat Ini

| Modul | Halaman / Endpoint | Hak Akses | Fitur & Fungsi |
|---|---|---|---|
| **Beranda Publik** | `/` | Publik (Bebas) | Profil RW, kartu statistik makro (KK, Warga, RT, Kos), 3 pengumuman terbaru, 3 agenda terdekat. |
| **Informasi RW** | `/informasi` | Publik (Bebas) | Kategori konten (Layanan, Keamanan, Pengumuman), agenda per jenis (Posyandu, Kerja Bakti, Rapat), bagan struktur RW. |
| **Statistik Publik** | `/statistik` | Publik (Bebas) | Distribusi KK per RT, piramida kelompok usia, proporsi status tinggal, statistik pendidikan & pekerjaan. *(Aman tanpa PII)*. |
| **Autentikasi** | `/login`, `/logout` | Publik / User | Login ganda via email atau username, verifikasi admin RW, session guard. |
| **Dashboard** | `/dashboard` | Admin RW | Monitoring angka kependudukan real-time, statistik internal, navigasi cepat ke pendataan. |
| **Kartu Keluarga** | `/kartu-keluarga` | Admin RW | Daftar KK (pencarian nomor KK / kepala), tambah KK, edit data alamat, detail KK (tab anggota utama & tab penghuni kos). |
| **Data Warga** | `/warga` | Admin RW | Registrasi warga baru, filter pencarian NIK & nama, status disabilitas, detail profil lengkap, histori tempat tinggal. |
| **Status Tinggal** | `/status-tinggal` | Admin RW | Mutasi tanggal mulai/keluar tinggal, pemetaan warga ke KK inang kos, filter riwayat aktif/non-aktif. |
| **Konten Publik** | `/konten-publik` | Admin RW | CRUD pengumuman, panduan surat pengantar, regulasi keamanan jam malam, pengaturan urutan & tanggal terbit. |
| **Agenda RW** | `/agenda-kegiatan` | Admin RW | CRUD kegiatan (posyandu, kerja bakti, rapat pleno), jam mulai/selesai, lokasi kegiatan, visibilitas publik. |
| **Pengurus RW** | `/pengurus-rw` | Admin RW | CRUD nama pengurus, jabatan, nomor telepon kontak resmi, urutan hierarki bagan organisasi. |
| **Riwayat Perubahan** | `/riwayat-perubahan` | Admin RW | Audit log mutasi data kependudukan (siapa mengubah apa, kapan, dan nilai sebelum vs sesudah). |
| **Laporan** | `/laporan` | Admin RW | Rekapitulasi agregat administrasi kependudukan untuk pelaporan ke tingkat Kelurahan / Kecamatan. |
