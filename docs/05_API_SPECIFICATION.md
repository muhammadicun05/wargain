# WargaIn v2 — RESTful API Specification
**Document Identifier:** DOC-SPEC-05-API  
**Standard Compliance:** OpenAPI 3.1.0 & RFC 7807 (Problem Details for HTTP APIs)  
**Status:** Approved for Implementation  
**Base URL:** `https://api.wargain.id/api/v2`

---

## 1. Overview & General Architecture

The WargaIn v2 API provides programmatic access to neighborhood operations, resident verification, and municipal service issuance.
- **Data Exchange**: JSON (`application/json`) with UTF-8 encoding.
- **Authentication**: Session-based Cookie (for web PWA) and HTTP Bearer Token (Authorization: Bearer `<token>`).
- **Standard Error Format**: RFC 7807 Problem Details.
- **Pagination**: Envelope pattern (`data`, `meta: { current_page, per_page, total_items, total_pages }`).

---

## 2. Global Error Specification (RFC 7807)

Every non-`2xx` HTTP response returns a structured problem detail object:

```json
{
  "type": "https://api.wargain.id/errors/validation-failed",
  "title": "Validation Error",
  "status": 422,
  "detail": "Data NIK tidak valid atau format salah.",
  "instance": "/api/v2/warga/",
  "invalid_params": [
    {
      "name": "nik",
      "reason": "NIK harus tepat 16 digit angka numerik."
    }
  ]
}
```

---

## 3. Core Endpoint Catalog

### 3.1. Identity & Wilayah

#### `GET /api/v2/wilayah/tree/`
Returns the subtree rooted at the authenticated official's jurisdiction (e.g. RW and all child RTs).

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "id": "a1b2c3d4-0000-0000-0000-000000000001",
    "nama": "RW 07",
    "level": "RW",
    "kode_pos": "40132",
    "child_nodes": [
      {
        "id": "b2c3d4e5-0000-0000-0000-000000000002",
        "nama": "RT 01",
        "level": "RT",
        "total_hunian": 42,
        "total_warga": 138
      },
      {
        "id": "c3d4e5f6-0000-0000-0000-000000000003",
        "nama": "RT 02",
        "level": "RT",
        "total_hunian": 36,
        "total_warga": 112
      }
    ]
  }
}
```

---

### 3.2. Citizen & Population (`/warga/`)

#### `GET /api/v2/warga/`
Returns tenant-scoped citizens with masked PII.

**Query Parameters:**
- `page` (integer, default 1)
- `per_page` (integer, default 20)
- `rt_id` (uuid, optional filter)
- `status` (string, `AKTIF` | `MUTASI_KELUAR` | `MENINGGAL`, default `AKTIF`)
- `search` (string, searches `nama_lengkap`)

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "4b2e8d19-3333-4444-5555-666677778888",
      "nama_lengkap": "Budi Santoso",
      "nik_masked": "327301******0001",
      "jenis_kelamin": "L",
      "tanggal_lahir": "1985-04-12",
      "status_perkawinan": "KAWIN",
      "hunian_saat_ini": {
        "nomor_rumah": "No. 14A",
        "rt_nama": "RT 01"
      },
      "status_keberadaan": "AKTIF"
    }
  ],
  "meta": {
    "current_page": 1,
    "per_page": 20,
    "total_items": 250,
    "total_pages": 13
  }
}
```

#### `POST /api/v2/warga/`
Enrolls a new citizen into the RW, computing HMAC blind index and AES-256-GCM ciphertext.

**Request Payload:**
```json
{
  "nik": "3273011508900001",
  "nama_lengkap": "Siti Aminah",
  "tempat_lahir": "Bandung",
  "tanggal_lahir": "1992-06-25",
  "jenis_kelamin": "P",
  "agama": "ISLAM",
  "status_perkawinan": "BELUM_KAWIN",
  "pekerjaan": "Karyawan Swasta",
  "nomor_telepon": "081234567890",
  "hunian_id": "9a8b7c6d-5555-4444-3333-222211110000",
  "peran_di_hunian": "PENYEWA_UTAMA"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Data warga berhasil didaftarkan.",
  "data": {
    "id": "e9a8b7c6-1111-2222-3333-444455556666",
    "nik_masked": "327301******0001",
    "nama_lengkap": "Siti Aminah"
  }
}
```

#### `POST /api/v2/warga/{id}/unmask/`
Audited endpoint that decrypts raw NIK for official verification purposes.

**Request Payload:**
```json
{
  "alasan": "Verifikasi Surat Pengantar SKCK No. 045/RT03/IX/2026"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "nik_unmasked": "3273011508900001",
    "audit_reference_id": "7f8e9d0a-..."
  }
}
```

---

### 3.3. Dwellings & Domicile (`/hunian/`)

#### `GET /api/v2/hunian/`
Lists dwellings under the caller's RT/RW jurisdiction with occupancy summary.

**Response (200 OK):**
```json
{
  "data": [
    {
      "id": "9a8b7c6d-5555-4444-3333-222211110000",
      "rt_nama": "RT 01",
      "nomor_rumah": "No. 14A",
      "status_kepemilikan": "SEWA_KONTRAK",
      "total_penghuni": 3,
      "kepala_hunian": "Budi Santoso",
      "status_iuran_bulan_ini": "LUNAS"
    }
  ]
}
```

---

### 3.4. Administrative Letters & Public Verification (`/layanan/`)

#### `POST /api/v2/layanan/surat/`
Submits a new citizen letter request.

**Request Payload:**
```json
{
  "pemohon_warga_id": "4b2e8d19-3333-4444-5555-666677778888",
  "kategori_layanan": "SKCK",
  "keperluan": "Persyaratan Melamar Pekerjaan BUMN"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "data": {
    "id": "3c4d5e6f-...",
    "nomor_surat": "045/RT01-RW07/X/2026",
    "status_surat": "PENGAJUAN",
    "verification_token": "a1b2c3d4e5f67890abcdef1234567890"
  }
}
```

#### `GET /api/v2/layanan/verifikasi/{verification_token}/`
**Public, unauthenticated** endpoint called by third parties scanning the physical/digital QR code. Automatically appends an entry to `verifikasi_surat_log`.

**Response (200 OK):**
```json
{
  "status": "valid",
  "dokumen": {
    "nomor_surat": "045/RT01-RW07/X/2026",
    "kategori_layanan": "SKCK",
    "nama_pemohon": "Budi Santoso",
    "nik_masked": "3273**********01",
    "asal_wilayah": "RT 01 / RW 07, Kelurahan Sukaluyu",
    "keperluan": "Persyaratan Melamar Pekerjaan BUMN",
    "tanggal_terbit": "2026-10-15",
    "berlaku_sampai": "2026-11-15",
    "status": "ASLI_DAN_BERLAKU"
  }
}
```

---

### 3.5. Dues & Treasury (`/iuran/`)

#### `POST /api/v2/iuran/bayar/`
Records cash or transfer settlement for dwelling dues invoice.

**Request Payload:**
```json
{
  "tagihan_id": "2d3e4f5a-...",
  "jumlah_dibayar": 50000,
  "metode_pembayaran": "TUNAI"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Pembayaran berhasil dicatat.",
  "data": {
    "nomor_kuitansi": "KWT-202610-0042",
    "receipt_url": "https://wargain.id/kuitansi/KWT-202610-0042",
    "whatsapp_share_text": "Terima kasih, pembayaran Iuran Kebersihan & Keamanan No. 14A bulan Okt 2026 sebesar Rp 50.000 telah lunas. Kuitansi: https://wargain.id/kuitansi/KWT-202610-0042"
  }
}
```
