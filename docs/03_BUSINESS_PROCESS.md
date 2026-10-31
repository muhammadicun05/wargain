# WargaIn v2 — Business Process Specifications
**Document Identifier:** DOC-SPEC-03-BPMN  
**Standard Compliance:** BPMN 2.0 (Business Process Model and Notation) & ISO/IEC 19510  
**Status:** Approved for Implementation  
**Audience:** System Architects, Developers, RT/RW Administrators, Quality Assurance Engineers

---

## 1. Scope & Architecture Context

This document specifies the end-to-end operational workflows of WargaIn v2. The processes are designed specifically for Indonesian community governance (Rukun Tetangga / Rukun Warga) and strictly adhere to:
1. **Tri-Axial Relational Isolation**: Differentiating physical inhabitant status from civil registry documentation.
2. **Maker-Checker Governance**: Two-tier verification (Warga $\to$ Ketua RT $\to$ Ketua RW) ensuring grass-roots transparency without administrative overhead.
3. **UU PDP No. 27/2022 Compliance**: Minimizing personal data exposure during cross-boundary interactions and public verifications.

---

## 2. Business Process Catalog

| Process ID | Name | Primary Actor | Trigger Event | Output Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **BP-01** | Tri-Axial Citizen & Domicile Onboarding | Ketua RT / Admin RW | New resident arrival / census | Active `Warga`, `Domisili`, and `KeanggotaanKK` |
| **BP-02** | Mutation Lifecycle (In/Out/Birth/Death) | Warga / RT Official | Vital civil event | Approved `Mutasi` record, status update |
| **BP-03** | Digital Surat Pengantar & QR Verification | Warga / RT / RW | Citizen request for official service | Digitally verifiable PDF/Web Certificate |
| **BP-04** | Dues Billing & Instant WhatsApp Receipting | Bendahara RT / Warga | Monthly billing cycle generation | Cashflow ledger entry & Digital Receipt URL |
| **BP-05** | Wilayah Node Claiming & RT Federation | Pengurus RW / RT | New neighborhood onboarding | Active `WilayahNode` branch & RBAC roles |
| **BP-06** | Zero-Knowledge Inter-RW Transfer | Pengurus RW (Source/Dest) | Outbound/Inbound migration | Cross-tenant cryptographic identity transfer |

---

## 3. Detailed Process Specifications

### BP-01: Tri-Axial Citizen & Domicile Onboarding

This process handles resident registration while preserving the separation between civil documents (KTP/KK) and local physical occupancy (Hunian).

```mermaid
sequenceDiagram
    autonumber
    actor W as Resident / Warga
    actor RT as Ketua / Sekretaris RT
    participant S as WargaIn v2 Backend
    participant DB as PostgreSQL
    participant SEC as Crypto Engine (AES/HMAC)

    W->>RT: Submits physical/photo copy of KTP & KK + Home address info
    RT->>S: Input raw NIK, Nama, KK, and select/create Hunian
    S->>SEC: Generate HMAC-SHA256(NIK, K_blind)
    SEC-->>S: Return nik_blind_index
    S->>DB: Query identitas_orang WHERE nik_blind_index = ?
    alt Identity Anchor Exists
        DB-->>S: Return existing identitas_id
        Note over S,RT: Check if already registered in current RW
        S->>DB: Query warga WHERE identitas_id = ? AND rw_id = current_rw
        alt Already active in this RW
            S-->>RT: Warning: Citizen already registered in this RW
        else Exists in other RW or Archived
            S-->>RT: Citizen identity recognized (cross-tenant match). Prompt transfer option.
        end
    else New Identity
        S->>DB: INSERT INTO identitas_orang (nik_blind_index) RETURNING id
        DB-->>S: Return new identitas_id
    end
    
    S->>SEC: Encrypt NIK with AES-256-GCM & Generate Masked NIK
    SEC-->>S: Return nik_encrypted, nik_masked
    S->>DB: INSERT INTO warga (identitas_id, rw_id, nik_encrypted, nik_masked, ...)
    S->>DB: Upsert kartu_keluarga & keanggotaan_kk
    S->>DB: Upsert domisili (hunian_id, warga_id, peran, tanggal_mulai, is_active=true)
    S-->>RT: Citizen successfully enrolled and linked to Dwelling
```

#### Key Rules:
- A non-local resident (e.g., Mahasiswa / Pekerja Kos) is enrolled into `warga` and `domisili` with `peran_di_hunian = PENGHUNI_KOS`.
- If their family card is located in another province, they are not forced into an artificial local `kartu_keluarga`.

---

### BP-02: Population Mutation Lifecycle

Covers civil dynamics: Birth (*Lahir*), Death (*Meninggal*), Inbound Migration (*Pindah Masuk*), and Outbound Migration (*Pindah Keluar*).

```mermaid
flowchart TD
    Start([Event Occurs: Lahir / Meninggal / Pindah]) --> Draft[Pengurus RT drafts Mutation Request]
    Draft --> Attach[Attach evidence document: Surat Lahir/Kematian/SKPWNI]
    Attach --> Validate{Is Actor Authorized?}
    Validate -- No --> RejectActor[Reject with HTTP 403]
    Validate -- Yes --> Submit[Submit Mutation with status PENDING]
    Submit --> Review[Ketua RW Reviews Mutation Queue]
    Review --> Decision{Decision}
    Decision -- Rejected --> RejectNote[Add catatan_penolakan & Set status DITOLAK]
    RejectNote --> NotifyRT[Notify RT Official]
    Decision -- Approved --> ExecuteState[Set status DISETUJUI & Update Citizen State]
    
    ExecuteState --> SubAction{Jenis Mutasi?}
    SubAction -- MENINGGAL --> MarkDead[warga.status_keberadaan = MENINGGAL<br/>domisili.is_active = FALSE]
    SubAction -- PINDAH_KELUAR --> MarkMoved[warga.status_keberadaan = MUTASI_KELUAR<br/>domisili.is_active = FALSE]
    SubAction -- PINDAH_MASUK --> MarkActive[warga.status_keberadaan = AKTIF<br/>Create active domisili]
    SubAction -- LAHIR --> CreateBaby[Create new warga row & link keanggotaan_kk as ANAK]

    MarkDead --> Audit[Write append-only AuditLog]
    MarkMoved --> Audit
    MarkActive --> Audit
    CreateBaby --> Audit
    Audit --> End([Process Completed])
```

---

### BP-03: Digital Surat Pengantar & Public QR Verification

Eliminates the physical friction of locating RT/RW leaders at home while retaining formal legal validity through digital verification tokens.

```mermaid
sequenceDiagram
    autonumber
    actor W as Warga (Citizen)
    actor RT as Ketua RT
    actor RW as Ketua RW
    participant S as WargaIn v2 Engine
    participant DB as PostgreSQL
    actor INST as Public Verifier (Kelurahan / Polsek / Bank)

    W->>S: Request Surat Pengantar (Category: SKCK, Purpose: "Melamar Pekerjaan")
    S->>DB: INSERT INTO surat_pengantar (status='PENGAJUAN', verification_token=gen_token())
    S-->>RT: Push notification: Pending Surat Request
    
    RT->>S: Review citizen profile & domicile standing
    alt RT Approves
        RT->>S: Approve request
        S->>DB: UPDATE surat_pengantar SET status='DISETUJUI_RT'
        S-->>RW: Notification: Forwarded to RW
    else RT Rejects
        RT->>S: Reject request with reason
        S->>DB: UPDATE surat_pengantar SET status='DITOLAK', catatan_penolakan=reason
        S-->>W: Notify rejection with explanation
    end

    alt Requires RW Approval
        RW->>S: Review & Sign off
        S->>DB: UPDATE surat_pengantar SET status='DISETUJUI_RW', diterbitkan_pada=NOW()
    end

    S->>S: Generate PDF with Embedded Tamper-Evident QR Code
    S-->>W: Surat Pengantar Ready for Download / WhatsApp Share
    
    Note over INST,S: Public Verification Phase
    INST->>S: Scans QR Code pointing to /layanan/verifikasi/<token>/
    S->>DB: Query surat_pengantar WHERE verification_token = ?
    alt Valid Token & Not Expired
        S->>DB: INSERT INTO verifikasi_surat_log (surat_id, ip_address, user_agent)
        S-->>INST: Display Official Verification Card (Nomor, Pemohon, Keperluan, Status: ASLI & VALID)
    else Invalid or Expired
        S-->>INST: Display Warning: "Dokumen Tidak Ditemukan atau Telah Kadaluwarsa"
    end
```

---

### BP-04: Periodic Dues (Iuran) Billing & Instant Digital Receipts

Eliminates loss of funds and manual bookkeeping errors through monthly dwelling-based invoices and automated WhatsApp receipts.

```mermaid
flowchart TD
    Start([1st of Month Billing Trigger]) --> BatchGen[System Generates Monthly Tagihan for each Active Hunian]
    BatchGen --> DuesList[Dues Items: Sampah + Keamanan]
    DuesList --> SaveInvoices[(tagihan_iuran created with status BELUM_BAYAR)]
    
    SaveInvoices --> CitizenPay[Citizen pays via Cash / QRIS / Transfer]
    CitizenPay --> TreasAction[Bendahara RT opens WargaIn Dues Desk]
    TreasAction --> SelectDwelling[Search Dwelling / House Number]
    SelectDwelling --> InputAmount[Input Amount Received & Channel]
    InputAmount --> RecordPay[Submit Settlement]

    RecordPay --> DBTrans[Database Transaction]
    DBTrans --> UpdateBill[UPDATE tagihan_iuran SET status_pembayaran='LUNAS']
    DBTrans --> InsertPay[INSERT INTO pembayaran_iuran with Kuitansi No: KWT-YYYYMM-XXXX]
    DBTrans --> UpdateCashflow[Update Node Realtime Balance]
    
    UpdateCashflow --> GenReceipt[Generate Digital Receipt Link & WhatsApp Template]
    GenReceipt --> SendWA[Send Proof of Payment to Citizen via WhatsApp]
    SendWA --> End([Payment Settled & Audited])
```

---

### BP-05: Wilayah Node Claiming & RT Federation

Governs the establishment of new RW and RT nodes within the national hierarchical tree.

1. **Hierarchy Registration**: An applicant (Ketua RW) creates an organizational node under the specific `Kelurahan`.
2. **Identity Verification**: The applicant submits SK Kepengurusan RW from the Kelurahan.
3. **Node Activation**: Platform admin verifies credentials and marks the RW node as `is_active = TRUE`.
4. **RT Sub-node Creation**: The RW administrator creates child nodes (`RT 01` through `RT 0n`) and invites Ketua RT via telephone/email token.
5. **Role Assignment**: RT officials receive restricted scoped permissions (read/write only within their own RT node and subordinate hunian).

---

### BP-06: Zero-Knowledge Inter-RW Citizen Transfer Protocol

Facilitates citizen relocation across participating RWs without leaking previous private logs or sensitive unmasked records.

```mermaid
sequenceDiagram
    autonumber
    actor W as Moving Citizen
    actor RW1 as Source RW (RW 03)
    actor RW2 as Target RW (RW 07)
    participant S as WargaIn Engine
    participant DB as PostgreSQL

    W->>RW1: Requests Pindah Keluar (Outbound Mutation)
    RW1->>S: Approve Outbound Mutation
    S->>DB: UPDATE warga SET status_keberadaan = 'MUTASI_KELUAR' WHERE rw_id = RW1
    
    W->>RW2: Reports arrival at new residence
    RW2->>S: Enter citizen NIK for onboarding
    S->>S: Compute HMAC-SHA256(NIK, K_blind)
    S->>DB: Query identitas_orang by blind index
    Note over S,RW2: Match found! IdentitasOrang exists in system.
    S-->>RW2: "NIK is recognized in system as Outbound from RW 03. Import history?"
    
    RW2->>S: Confirm Inbound Transfer
    S->>DB: INSERT INTO warga (identitas_id, rw_id=RW2, nik_encrypted, ...)
    S->>DB: INSERT INTO mutasi (jenis_mutasi='PINDAH_MASUK', target_node_id=RW2, status_approval='DISETUJUI')
    S-->>RW2: Citizen successfully enrolled into RW 07 without historical tenant data leakage.
```

---

## 4. Business Exception & Resilience Protocols

1. **Offline Collection Handling**: If RT treasurers collect cash during door-to-door rounds without internet connectivity, the system accepts batch entry timestamping with retro-active payment dates, preventing unfair late-marking.
2. **Stale Surat Requests**: Surat Pengantar requests in `PENGAJUAN` state exceeding 14 days without RT/RW action are automatically marked `KADALUWARSA` to avoid unbounded queues.
3. **Disputed Domicile Occupancy**: If two residents claim the same dwelling under conflicting roles, the RT administrator must execute a physical verification and override via the Domicile Management interface.
