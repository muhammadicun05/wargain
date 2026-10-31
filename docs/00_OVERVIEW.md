# WargaIn v2 — System Overview & Requirements Specification

**Document Identifier:** `DOC-WARGAIN-00-OVERVIEW`  
**Standard Compliance:** ISO/IEC/IEEE 29148:2018 (Systems and software engineering — Life cycle processes — Requirements engineering)  
**Author:** Zyntaxera Engineering (@Icun)  
**Classification:** Internal Technical Architecture  
**Release Version:** 2.0.0-PROD-SPEC  

---

## 1. Executive Summary & Problem Statement

### 1.1 The Grassroots Governance Challenge in Indonesia
Rukun Warga (RW) and Rukun Tetangga (RT) represent the foundational tier of community governance in Indonesia, administering over 280 million citizens. However, RT/RW operations suffer from fundamental structural inefficiencies:
1. **Conflation of Administrative Registration and Physical Habitation:** Existing tools conflate Family Cards (*Kartu Keluarga / KK*) with physical residential structures. This creates severe anomalies when handling rental tenants, boarding house occupants (*penghuni kos*), and temporary residents.
2. **Administrative Friction in Public Service:** 90% of citizen interactions with RT/RW revolve around requesting formal Introduction Letters (*Surat Pengantar*). Traditional manual workflows rely on paper ledgers, prone to duplication, physical loss, and forgery.
3. **Social Friction in Neighborhood Dues Collection:** Collection of sanitation and security dues (*iuran kebersihan & keamanan*) creates interpersonal discomfort between neighbors due to lack of transparent, automated digital tracking.
4. **Severe Privacy Vulnerabilities under Law No. 27 of 2022 (UU PDP):** Citizen National Identity Numbers (*NIK*) and Family Card numbers are frequently exposed in public spreadsheets and unencrypted chat groups without access logging or data masking.

### 1.2 The WargaIn v2 Solution
**WargaIn v2** is an enterprise-grade, privacy-first community governance platform engineered to decouple administrative records, physical domicile, and daily grassroots services into a unified national hierarchical tree architecture (Province down to RT).

```
+-------------------------------------------------------------------------+
|                              WARGAIN v2                                 |
|                                                                         |
|   +--------------------+  +--------------------+  +------------------+  |
|   |       SIAPA        |  |  TERCATAT DI MANA  |  | TINGGAL DI MANA  |  |
|   |    (Individual)    |  |   (Family Card)    |  |  (Physical Unit) |  |
|   |   HMAC-Indexed &   |  |   Administrative   |  |  Domicile Status |  |
|   |   AES-Encrypted    |  |   Representation   |  |   per RT Node    |  |
|   +--------------------+  +--------------------+  +------------------+  |
|                                                                         |
|   +-----------------------------------------------------------------+   |
|   |                      DAILY VALUE DRIVERS                        |   |
|   |   - QR-Verified Digital Introduction Letters (Surat Pengantar)  |   |
|   |   - Automated Frictionless Neighborhood Dues & Cashflow Ledger  |   |
|   |   - Privacy-Preserving Aggregate Public Portal (UU PDP-Aligned) |   |
|   +-----------------------------------------------------------------+   |
+-------------------------------------------------------------------------+
```

---

## 2. Core Architectural Principles

WargaIn v2 adheres to seven non-negotiable architectural axioms:

1. **Strict Tri-Axial Domain Separation (*Pemisahan Tiga Sumbu*):**
   - **Person (`Warga`):** Represents biological individuals, recognized globally via an irreversible HMAC Blind Index of the NIK, with PII strictly owned by their local RW.
   - **Administrative Record (`KartuKeluarga` & `KeanggotaanKK`):** Represents legal civil registry status.
   - **Physical Domicile (`Hunian` & `Domisili`):** Represents geographical dwelling units anchored to an RT node.
2. **Unified National Hierarchical Tree (*Pohon Wilayah Nasional*):**
   - Nodes represent `PROVINSI`, `KOTA_KABUPATEN`, `KECAMATAN`, `KELURAHAN_DESA`, `RW`, and `RT`.
   - Upper tiers (Kelurahan, Kecamatan, Kota, Provinsi) **only observe mathematically aggregated metrics** (rollups) and are programmatically prohibited from accessing raw individual PII.
3. **Event-Sourced Mutation via Maker-Checker:**
   - Vital status (Birth, Death, Inward Migration, Outward Migration, Internal Relocation) is immutable history. State changes are realized exclusively through verified `Mutasi` events requiring separate proposer and approver actors.
4. **Privacy by Design (UU PDP No. 27/2022 Compliance):**
   - Raw NIK is encrypted at rest using AES-256-GCM.
   - National de-duplication is achieved via HMAC-SHA256 blind indexing.
   - User interfaces mandate masked display (`3273********0001`).
   - Every read of raw PII creates an immutable audit record (`LogAksesNIK`).
   - Public aggregate statistics enforce **Small-Cell Suppression** ($N < 5$ individuals are obfuscated).
5. **Daily Utility as Adoption Catalyst:**
   - Digital introduction letters with cryptographic QR verification and neighborhood billing are foundational core features, not auxiliary add-ons.
6. **Mobile-First Zero-Friction Accessibility (PWA):**
   - Citizens interact via lightweight, high-contrast, responsive web pages (accessible directly from WhatsApp deep-links) without mandatory app store downloads.
7. **Single-Developer Ergonomic Sustainability:**
   - Built as a clean modular monolith using **Django 5.x + PostgreSQL + Tailwind CSS** to maximize developer productivity, operational security, and maintainability.

---

## 3. User Personas & Access Control Matrix

Access control is governed by a **Role-and-Scope Matrix**, where permissions are bound to a specific node within the Wilayah Tree:

| Role Identifier | Node Scope | Permitted Capabilities | Explicit Prohibitions |
|---|---|---|---|
| `SUPER_ADMIN` | Platform-Wide | System diagnostics, reference tree provisioning, dispute resolution. | Decrypting or inspecting citizen PII without logged warrant. |
| `LURAH` / `KEPALA_DESA` | Kelurahan/Desa Node | Viewing aggregate rollups across child RWs, approving new RW claims, broadcast public alerts. | Inspecting individual citizen PII or household records. |
| `KETUA_RW` | RW Node | Approving mutation events, approving escalations of Surat Pengantar, managing RW officials, full RW data access. | Altering or deleting append-only audit trail logs. |
| `SEKRETARIS_RW` | RW Node | Data entry (KK, Warga, Hunian), managing agenda and announcements. | Self-approving mutation events they proposed (*Maker-Checker*). |
| `BENDAHARA_RW` | RW Node | Managing dues rules, tracking billing status, ledger recording. | Accessing sensitive citizen PII outside billing necessities. |
| `KETUA_RT` | RT Node | Viewing/proposing mutations for their specific RT, approving RT-level Surat Pengantar. | Viewing data belonging to neighboring RTs. |
| `SEKSI_LINGKUNGAN` | RW Node (Module-Specific) | Managing sub-modules (e.g. Posyandu schedule, security patrol). | Accessing full KK records or unmasked NIK. |
| `WARGA` | Self & Family Record | Viewing self-data, submitting letter requests, submitting billing confirmations. | Accessing data of other citizens or households. |
| `TAMU_PUBLIK` | Public Portal Route | Viewing verified public announcements, community agenda, macro statistics. | Accessing any individual-level data. |

---

## 4. Multi-Phase Product Roadmap

```
PHASE 1: Core RW/RT Foundation (Target: Pilot RW)
├── Hierarchical Wilayah Tree (National nodes down to RT)
├── Tri-Axial Core (Warga, KartuKeluarga, Hunian, Domisili)
├── UU PDP Cryptography (HMAC Blind Index + AES-256-GCM NIK)
├── Event-Driven Mutation Engine (Maker-Checker Approval)
├── Digital Introduction Letter (Surat Pengantar + Public QR Verification)
└── Public Portal & Action-Driven Backoffice Admin

PHASE 2: Community Operations & Citizen Self-Service
├── PWA Optimization (Mobile-First WhatsApp deep-linking)
├── Frictionless Neighborhood Billing & E-Receipt Generation
├── Citizen Self-Service Portal (Letter submission via WhatsApp OTP)
└── Overcapacity Housing & Sanitation Alert Widgets

PHASE 3: Inter-Neighborhood & Municipal Scale
├── Cross-RW Migration Handshake (Zero-Knowledge Inter-RW Transfer)
├── Kelurahan Rollup Dashboard (Pre-computed aggregate caching)
└── Multi-tenant Domain Mapping (Custom subdomains per Kelurahan)
```
