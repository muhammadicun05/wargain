# WargaIn v2 — Functional Features Specification
**Document Identifier:** DOC-SPEC-06-FEAT  
**Standard Compliance:** ISO/IEC/IEEE 29148:2018 (Requirements Engineering)  
**Status:** Approved for Implementation  
**Audience:** Product Managers, Front-End Engineers, UI/UX Designers, QA

---

## 1. Feature Architecture Philosophy: Zero AI Slop & Real-World Grassroots

WargaIn v2 rejects speculative "AI slop" (e.g. generative chat bots answering trash schedules or hallucinating legal advice). Instead, every feature directly solves the acute operational bottlenecks faced by Indonesian volunteer RT/RW administrators:
1. **Action-Driven, Not Vanity Metrics**: The dashboard surfaces tasks requiring decisions (unprocessed letters, uncollected dues, incoming mutation requests), rather than non-actionable decorative graphs.
2. **Mobile First via WhatsApp Links**: Neighborhood residents do not install heavy mobile apps for occasional neighborhood tasks. The platform runs as a high-performance Progressive Web App (PWA) with instant authentication links sent through WhatsApp.
3. **Strict Feature Postponement (No Bansos Scoring)**: Social assistance (*Bansos*) prioritization algorithms are **strictly deferred** from initial releases to prevent community distrust, accusations of bias (*tuduhan pilih kasih*), and social friction among neighbors.

---

## 2. Feature Modules Breakdown

### 2.1. Action-Driven Command Dashboard (`FEAT-01`)

```
+-----------------------------------------------------------------------------------+
|  WARGAIN v2 | RW 07 Kelurahan Sukaluyu                           [ Ketua RT 01 v ]|
+-----------------------------------------------------------------------------------+
|  [ ACTION REQUIRED (3) ]                                                          |
|  * 2 Pengajuan Surat Pengantar menunggu persetujuan           [ Tinjau Sekarang ] |
|  * 1 Permohonan Mutasi Masuk baru dari RW 03                  [ Verifikasi ]      |
+-----------------------------------------------------------------------------------+
|  STATISTIK OPERASIONAL BULAN INI (OKTOBER 2026)                                   |
|  * Total Warga Aktif   : 284 Jiwa (142 L / 142 P)                                 |
|  * Hunian Terisi       : 74 Rumah / Kos (96.1%)                                   |
|  * Realisasi Iuran     : Rp 3.700.000 / Rp 4.200.000 (88.1%) [ Tagih Sisanya ]   |
+-----------------------------------------------------------------------------------+
|  AKSI CEPAT                                                                       |
|  [+ Catat Warga Baru]  [+ Input Hunian]  [+ Terbitkan Kuitansi]  [+ Buat Pengumuman]|
+-----------------------------------------------------------------------------------+
```

#### Functional Requirements:
- **FR-01.1**: Realtime alert banner displaying count of pending `SuratPengantar` and `Mutasi`.
- **FR-01.2**: Financial collection thermometer displaying monthly billing progress (`Realisasi vs Target`).
- **FR-01.3**: Quick-action modal shortcuts operable on small mobile viewports with single-thumb reach.

---

### 2.2. Tri-Axial Citizen & Dwelling Registry (`FEAT-02`)

Solves the classic dilemma: *"KTP luar kota tapi ngekos/ngontrak di sini, dihitung warga atau bukan?"*

#### Functional Requirements:
- **FR-02.1**: **Dwelling-Centric Registry**: Each dwelling (`Hunian`) lists its current physical occupants, distinguishing between `KEPALA_RUMAH_TANGGA`, `ANGGOTA`, `PENYEWA_UTAMA`, and `PENGHUNI_KOS`.
- **FR-02.2**: **Masked Citizen Search**: Fast search by full name, house number, or masked NIK. Full raw NIK search operates via HMAC blind indexing.
- **FR-02.3**: **Family Card Grouping**: Supports citizens living in the neighborhood without requiring a local family card. Local family cards can group multiple members.

---

### 2.3. Digital Surat Pengantar with QR Verification (`FEAT-03`)

Transforms the traditional bureaucratic letter into an authenticated, tamper-evident document.

#### Functional Requirements:
- **FR-03.1**: Citizen or RT official selects pre-configured letter templates (KTP Baru, Perpanjangan KK, Pengantar SKCK, Keterangan Domisili, Keterangan Kematian).
- **FR-03.2**: Two-tier digital signoff: RT approval moves state to `DISETUJUI_RT`; RW approval moves state to `DISETUJUI_RW` and generates a verifiable document.
- **FR-03.3**: High-density QR code embedding a unique verification URL (`/layanan/verifikasi/<token>/`).
- **FR-03.4**: When third parties (Kelurahan, Polsek, Bank) scan the QR code, the public portal displays official document metadata confirming authenticity, while logging IP and timestamp.

---

### 2.4. Frictionless Dues & Digital WhatsApp Kuitansi (`FEAT-04`)

Eliminates paper receipt booklets and cash discrepancies.

#### Functional Requirements:
- **FR-04.1**: Automatic batch generation of monthly bills on the 1st of each month for all active dwellings.
- **FR-04.2**: **One-Click Payment Desk**: Treasurer selects house number $\to$ clicks "Bayar Rp 50.000" $\to$ selects "Tunai" or "Transfer" $\to$ settlement saved.
- **FR-04.3**: **WhatsApp Digital Receipt**: Instant generation of a clean pre-filled WhatsApp message containing the official digital receipt link (`/kuitansi/KWT-XXXXXX`), ready to send to the resident with one tap.
- **FR-04.4**: Transparent cashflow ledger showing total income, categorized operational expenditures, and current bank/cash balances.

---

### 2.5. Resident Mutation Lifecycle Engine (`FEAT-05`)

Maintains population integrity without data corruption.

#### Functional Requirements:
- **FR-05.1**: Distinct mutation types: `PINDAH_MASUK`, `PINDAH_KELUAR`, `MENINGGAL`, `LAHIR`.
- **FR-05.2**: Outbound moves do not delete historical database rows; they flag `status_keberadaan = MUTASI_KELUAR` and deactivate `domisili.is_active = FALSE`.
- **FR-05.3**: Deceased citizens retain their historical references on past letters and dues records, while marked `MENINGGAL` to suppress them from active demographic tallies.

---

### 2.6. Deferral Notice: Bansos Prioritization (`FEAT-06`)

> [!IMPORTANT]
> **Explicit Directive:** Algorithmic ranking or scoring of citizens for government social aid (Bansos/BLT) is **not included** in WargaIn v2 Core.
> 
> *Rationale*: RT/RW governance is built on delicate grassroots social trust. Algorithmic scoring creates friction and accusations of favoritism. Data export for government needs is limited to standard, neutral demographic listings (e.g. filter by elderly citizens living alone) without automated subjective ranking.

---

## 3. Non-Functional & Cross-Cutting Requirements

1. **Performance**: Page load $< 800\text{ ms}$ on standard 4G mobile connections. Assets minified via Tailwind CSS standalone build.
2. **Offline-Tolerant Entry**: Critical forms retain state locally in case of brief mobile signal drops.
3. **Accessibility**: High-contrast, legible typography (Inter/System UI fonts), minimum touch targets of $44 \times 44\text{ px}$.
4. **Zero Vendor Lock-in**: Standard Django 5.x, PostgreSQL 18, and pure CSS. Can be deployed on any low-cost VPS, Docker container, or bare metal server.
