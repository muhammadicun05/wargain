# WargaIn v2 — Arsitektur, ERD, dan Proses Bisnis

Oct 31, 2026 · @Icun

WargaIn v2 memisahkan data administratif (KK), domisili aktual (hunian), dan layanan harian (surat, iuran) dalam satu platform nasional berjenjang wilayah (provinsi sampai RT) yang tidak terikat stack tertentu.

## Prinsip desain dan asumsi

Versi awal berpusat pada KK dan hanya mencatat data. Versi ini berpusat pada tiga hal yang dipisahkan tegas: siapa (orang), tercatat di mana (KK), dan tinggal di mana (hunian).

**Prinsip**

1. **Pisahkan administratif dari aktual.** Keanggotaan KK tidak sama dengan tempat tinggal. Keduanya dicatat di entitas berbeda.
2. **Satu pohon wilayah nasional.** Provinsi, kota, kecamatan, kelurahan atau desa, RW, dan RT adalah node dalam satu pohon. Data warga dimiliki RW, sedangkan tingkat di atasnya hanya melihat angka agregat.
3. **Rancang dari atas, bangun dari bawah.** Model dan alamat URL mendukung seluruh hierarki sejak awal, tetapi fitur diaktifkan bertahap mulai dari RW.
4. **Privasi sebagai default.** NIK dienkripsi, ditampilkan tersamar, dan setiap akses baca ke data pribadi tercatat.
5. **Orang dikenali secara nasional, datanya tidak.** Identitas orang dikenali lewat hash NIK supaya perpindahan antar-RW tidak membuat duplikat, tetapi tidak ada RW yang bisa membaca data RW lain.
6. **Perubahan data = peristiwa.** Mutasi (lahir, wafat, pindah) disimpan sebagai peristiwa dengan tanggal efektif, dokumen bukti, dan persetujuan, lalu status warga diturunkan darinya.
7. **Layanan harian adalah alasan orang memakai sistem.** Surat pengantar dan iuran masuk fase awal, bukan tambahan di akhir.
8. **Alat bantu lingkungan, bukan sumber data resmi.** Dukcapil tetap menjadi data induk kependudukan.

**Asumsi yang dipakai dokumen ini**

- Target: aplikasi nasional dengan alamat berjenjang `wargain/provinsi/kota/kecamatan/kelurahan-atau-desa/rw/rt`. Implementasi awal dimulai dari satu RW atau satu kelurahan lewat kerja sama.
- Wilayah selain RW dan RT (banjar, nagari, gampong, dan sejenisnya) ditunda. Jenis node dibuat bisa diperluas agar model tidak perlu diubah kelak.
- Pengembang tunggal: monolit modular, stack yang paling dikuasai, dan layanan terkelola bila tersedia agar beban operasional tetap kecil.
- Pengguna fase 1: pengurus RW dan RT, serta kelurahan bila bermitra. Warga masuk sebagai pengguna pada fase 2.
- Stack netral. Basis data relasional dipilih karena data terstruktur dan butuh integritas. Kemampuan wajib: transaksi, kunci asing, isolasi atau partisi per wilayah, dan kolom terenkripsi.

## Aktor dan hak akses

Hak akses ditentukan oleh peran dan cakupan wilayah: seorang pengguna bisa punya beberapa peran, masing-masing terikat ke RW atau RT tertentu.

| Peran | Cakupan (node wilayah) | Boleh | Tidak boleh |
| --- | --- | --- | --- |
| Ketua RW | Satu RW | Menyetujui mutasi dan surat, kelola pengurus, lihat semua data dan laporan RW | Mengubah log audit |
| Sekretaris RW | Satu RW | Input dan ubah data KK, warga, hunian; kelola agenda dan konten | Menyetujui mutasi yang ia usulkan sendiri |
| Bendahara RW | Satu RW | Kelola tagihan, pembayaran, dan laporan kas | Melihat data pribadi di luar kebutuhan penagihan |
| Ketua RT | Satu RT | Melihat dan mengusulkan perubahan data RT-nya, menyetujui surat tingkat RT | Melihat data RT lain |
| Seksi (keamanan, posyandu, dll.) | Satu RW, per modul | Mengelola data modulnya saja | Mengakses data KK dan NIK lengkap |
| Warga | Data sendiri dan keluarganya | Melihat data sendiri, mengajukan koreksi dan surat, melihat tagihan | Melihat data warga lain |
| Lurah atau kepala desa | Kelurahan atau desa beserta RW di bawahnya | Melihat agregat, menyetujui klaim RW baru, mengirim pengumuman ke semua RW | Membuka data pribadi warga |
| Camat, dinas kota, dinas provinsi | Kecamatan, kota, atau provinsi | Melihat agregat dan laporan wilayahnya, mengirim pengumuman | Membuka data pribadi warga |
| Tamu publik | Halaman publik | Melihat pengumuman, agenda, statistik teragregasi | Semua data individu |
| Operator platform | Lintas wilayah | Dukungan teknis, pengisian pohon wilayah, penanganan sengketa klaim | Membuka data pribadi tanpa izin tercatat dari RW |

Tiga aturan lintas peran: peran di sebuah node berlaku untuk node di bawahnya, tetapi akses ke data pribadi tidak ikut turun (peran tingkat atas hanya menerima agregat kecuali RW memberi akses yang tercatat); usulan perubahan data sensitif harus disetujui orang lain (maker-checker); dan setiap pembukaan data NIK oleh pengguna mana pun masuk log akses.

## Arsitektur sistem

&#91;embedded content: arsitektur sistem · 5 lapis\]

Semua klien masuk lewat gerbang yang memetakan alamat URL ke satu node wilayah, memeriksa peran pengguna di node itu, lalu mengunci semua query ke wilayah tersebut. Modul Kependudukan adalah inti yang dipakai modul lain; pekerjaan berat seperti kirim pesan dan buat PDF berjalan di latar belakang lewat antrian tugas.

**Pilihan arsitektur dan alasannya**

- **Monolit modular dulu, bukan layanan mikro.** Pengembang tunggal dan satu basis data jauh lebih mudah dijaga. Batas antar-modul ditegakkan lewat kode, sehingga bisa dipecah kelak bila beban menuntut.
- **Alamat berjenjang dipetakan ke kode wilayah.** `wargain/provinsi/kota/kecamatan/kelurahan-atau-desa/rw/rt` hanya pintu masuk. Sistem menyimpan kode resmi, bukan nama, dan slug lama dialihkan bila nama wilayah berubah. Alamat tidak pernah dipakai sebagai dasar hak akses; hak akses selalu dicek dari peran di node.
- **Pohon wilayah diisi dari data resmi sampai kelurahan atau desa.** RW dan RT tidak ada di data resmi, jadi dibuat lewat klaim yang diverifikasi.
- **Basis data relasional tunggal, terpartisi per wilayah,** dengan isolasi baris. Integritas relasi (KK, anggota, hunian, mutasi) adalah kebutuhan inti, dan partisi memungkinkan dipecah ke beberapa server kelak.
- **Ringkasan agregat dihitung berkala (rollup) per node,** sehingga halaman kelurahan, kecamatan, kota, dan provinsi tidak pernah membaca data individu.
- **Klien web responsif (PWA)** untuk portal warga dan panel pengurus: tanpa pemasangan aplikasi, bisa dibuka dari tautan WhatsApp, dan cukup di ponsel murah.
- **Log audit terpisah dan hanya bisa ditambah**, supaya pengurus yang punya akses admin pun tidak bisa menghapus jejaknya.
- **Integrasi lewat antarmuka tipis** (notifikasi, pembayaran): penyedia layanan bisa diganti tanpa mengubah modul domain.

## Model data

&#91;embedded content: ERD inti · 11 entitas, relasi satu-ke-banyak\]

Panah menunjuk ke sisi "banyak". Wilayah adalah pohon yang menjadi pemilik data: tiap node punya induk, jenis (provinsi sampai RT), kode resmi, dan slug. Hunian menempel pada node RT. Identitas orang menyimpan hash NIK sehingga orang yang sama dikenali di RW berbeda, sedangkan data warganya tetap milik satu RW. Seorang warga bisa punya beberapa keanggotaan KK dan beberapa domisili sepanjang waktu, tetapi hanya satu yang aktif pada satu waktu.

Entitas pendukung yang tidak digambar agar diagram tetap terbaca: Pengurus, Dokumen bukti, Jenis surat, Jenis iuran, Pembayaran, Pengumuman, Agenda, Klaim wilayah, Permintaan pindah antar-RW, Ringkasan agregat, serta Log audit dan Log akses. Semuanya tercantum di katalog berikut.

## Katalog entitas dan aturan data

Tiga entitas baru menyelesaikan masalah terbesar versi awal: **Hunian** (bangunan), **Domisili** (siapa tinggal di hunian mana) dan **Keanggotaan KK** (siapa tercatat di KK mana). Untuk skala nasional ditambah **Wilayah** (pohon provinsi sampai RT) dan **Identitas orang** (hash NIK).

| Entitas | Fungsi | Atribut kunci |
| --- | --- | --- |
| Wilayah | Pohon nasional dan pemilik data | induk, jenis (provinsi, kota, kecamatan, kelurahan atau desa, RW, RT), kode wilayah resmi, nama, slug, riwayat slug, status klaim |
| Klaim wilayah | Verifikasi pembuat node RW atau RT | wilayah, pemohon, bukti (misalnya SK pengurus), penyetuju, status |
| Hunian | Bangunan atau unit fisik | node RT, alamat, jenis (rumah, kos, kontrakan, ruko), pemilik, koordinat (opsional) |
| Kartu Keluarga | Dokumen administratif keluarga | nomor KK, alamat di KK, status KK (aktif, pindah, gabung) |
| Identitas orang | Pengenal nasional tanpa isi data | hash NIK (blind index), tanggal dibuat |
| Warga | Satu orang yang tercatat di satu RW | identitas orang, NIK (terenkripsi), nama, gender, tempat dan tanggal lahir, agama, pendidikan, pekerjaan, status hidup |
| Keanggotaan KK | Hubungan warga dengan KK | warga, KK, hubungan keluarga, tanggal mulai, tanggal selesai |
| Domisili | Hubungan warga dengan hunian | warga, hunian, jenis tinggal, tanggal mulai, tanggal selesai, penanggung jawab |
| Mutasi | Peristiwa kependudukan | jenis, warga, tanggal efektif, alasan, status persetujuan, pengusul, penyetuju |
| Permintaan pindah antar-RW | Serah terima antar dua RW | identitas orang, RW asal, RW tujuan, status, persetujuan kedua pihak |
| Dokumen bukti | Lampiran mutasi, klaim, atau surat | entitas terkait, tipe berkas, penyimpanan, pengunggah |
| Peran pengguna | Akun, peran, dan cakupan | pengguna, peran, node wilayah, masa berlaku |
| Pengurus | Susunan pengurus per periode | warga, jabatan, periode, kontak resmi |
| Jenis surat dan Permohonan surat | Layanan surat pengantar | pemohon, jenis, tujuan, status, nomor surat, penyetuju, berkas PDF |
| Jenis iuran, Tagihan, Pembayaran | Kas dan iuran | hunian atau KK penanggung, periode, jumlah, status, bukti bayar |
| Pengumuman dan Agenda | Informasi publik dan kegiatan | judul, isi, kategori, jadwal, node asal, node tujuan (bisa banyak RW sekaligus) |
| Ringkasan agregat | Angka per node hasil rollup | node, periode, metrik, nilai (sel kecil disembunyikan) |
| Log audit dan Log akses | Jejak perubahan dan pembukaan data | pelaku, tindakan, entitas, nilai lama dan baru, waktu |

**Aturan data yang dijaga sistem**

1. Seorang warga hanya boleh punya **satu keanggotaan KK aktif** dan **satu domisili utama aktif** pada satu waktu.
2. Setiap KK aktif punya **tepat satu kepala keluarga**. Bila kepala wafat atau pindah, sistem menahan mutasi sampai pengganti ditetapkan.
3. **Penghuni kos** tidak punya keanggotaan KK di RW ini. KK asalnya dicatat sebagai keterangan, dan penanggung jawabnya adalah pemilik atau pengelola hunian, bukan KK tertentu.
4. Pemilik hunian boleh **tidak tinggal di RW**. Pemilik dicatat sebagai warga atau sebagai kontak luar dengan nomor telepon.
5. **Status warga diturunkan dari mutasi**, tidak diedit langsung. Mengubah status berarti membuat mutasi dengan tanggal efektif.
6. Satu hunian boleh berisi **beberapa rumah tangga** (kontrak, menumpang). Satu KK boleh tinggal di **beberapa hunian** secara historis.
7. Data dihapus lunak (soft delete) dan riwayatnya disimpan. Penghapusan permanen hanya lewat prosedur retensi.
8. **Node RW dan RT baru tidak aktif sebelum klaimnya disetujui.** Node sampai tingkat kelurahan atau desa diisi dari data resmi.
9. Satu identitas orang boleh muncul di beberapa RW (misalnya KK di satu RW, kos di RW lain), tetapi hanya **satu RW yang menjadi tempat tercatat tetap (KK)** pada satu waktu. Menggantinya hanya lewat pindah antar-RW yang disetujui kedua RW.
10. RW tidak pernah melihat isi data RW lain. Bila identitas yang sama sudah tercatat tetap di tempat lain, sistem hanya menyatakan hal itu tanpa menyebut RW atau isi datanya.

## Proses bisnis

&#91;embedded content: alur surat pengantar · 4 pelaku, 6 langkah\]

Surat yang cukup tingkat RT berhenti di Ketua RT, lalu langsung diterbitkan. Surat yang butuh RW (misalnya untuk kelurahan) naik ke pengurus RW. Setiap penerbitan masuk log audit, dan kode QR pada surat membuka halaman verifikasi keaslian.

**Mutasi kependudukan (maker-checker)**

1. Pengusul (sekretaris atau Ketua RT) membuat mutasi: jenis, warga, tanggal efektif, alasan, dan dokumen bukti.
2. Sistem memeriksa aturan, misalnya kepala keluarga yang wafat atau pindah harus diganti dulu, dan KK tidak boleh kosong tanpa ditutup.
3. Ketua RW menyetujui atau menolak. Orang yang mengusulkan tidak boleh menyetujui usulannya sendiri.
4. Setelah disetujui, sistem menutup keanggotaan KK dan domisili yang terkait, menurunkan status warga, dan mencatat nilai lama dan baru di log audit.
5. Jenis mutasi yang didukung: lahir, wafat, pindah keluar, pindah masuk, pindah hunian dalam RW, perubahan hubungan keluarga, dan perubahan data KK.

**Iuran dan kas**

1. Bendahara menetapkan jenis iuran: nominal, periode, dan penanggung (hunian atau KK).
2. Sistem membuat tagihan berkala dan mengirim pengingat lewat WhatsApp.
3. Pembayaran lewat QRIS atau transfer dicocokkan otomatis. Pembayaran tunai dicatat bendahara dengan bukti.
4. Laporan kas bulanan tersedia untuk pengurus. Ringkasan teragregasi boleh dibuka untuk warga.

**Aktivasi RW baru (klaim wilayah)**

1. Pohon wilayah sampai kelurahan atau desa sudah tersedia dari data resmi. Calon Ketua RW memilih kelurahan atau desanya.
2. Ia membuat node RW dan RT, lalu mengajukan klaim dengan bukti, misalnya surat keputusan pengurus.
3. Lurah atau kepala desa menyetujui klaim. Bila kelurahan belum bermitra, operator platform yang memverifikasi.
4. Data lama diimpor dari Excel: pratinjau, validasi NIK dan KK, deteksi duplikat, lalu koreksi sebelum disimpan.
5. Ketua RW memeriksa ringkasan hasil impor dan mengaktifkan RW. Warga lalu diundang ke portal lewat tautan dan kode verifikasi.

**Pindah antar-RW**

1. Pengurus RW asal membuat mutasi pindah keluar dan memilih RW tujuan.
2. Sistem membuat permintaan pindah berdasarkan hash NIK. RW tujuan menerima pemberitahuan tanpa melihat isi data RW asal.
3. Kedua RW menyetujui. Setelah itu data dasar (nama, tanggal lahir, hubungan keluarga) diserahkan, dan RW tujuan melengkapi sisanya sendiri. Riwayat internal RW asal tidak ikut.
4. Keanggotaan KK dan domisili di RW asal ditutup dengan tanggal efektif yang sama. RW tujuan membuat keanggotaan dan domisili baru.
5. Kedua RW mencatat peristiwanya di log audit masing-masing.

## Keamanan dan kepatuhan UU PDP

NIK, nomor KK, dan data disabilitas adalah data pribadi, sebagian termasuk data spesifik menurut UU No. 27 Tahun 2022. Kontrol di bawah ini dirancang sebagai bagian arsitektur, bukan tambalan. Sebelum dipakai di RW sungguhan, rancangan ini sebaiknya ditinjau oleh konsultan hukum atau praktisi PDP.

| Risiko | Kontrol | Lapisan |
| --- | --- | --- |
| Data satu RW terbaca RW lain | Isolasi baris per tenant di basis data (row-level security) ditambah cek di aplikasi | Data dan aplikasi |
| NIK bocor dari basis data atau cadangan | Enkripsi kolom NIK, kunci disimpan terpisah, tampilan tersamar (`3273********0001`) | Data |
| Penyalahgunaan akses oleh pengurus | Log akses baca untuk data pribadi, peninjauan log berkala oleh Ketua RW | Aplikasi dan audit |
| Akun pengurus diambil alih | Autentikasi dua faktor untuk semua peran pengurus, batas percobaan masuk, sesi pendek | Aplikasi |
| Ekspor dan cetak dibagikan lewat chat | Ekspor hanya untuk peran tertentu, tercatat, diberi watermark berisi nama dan waktu | Aplikasi |
| Statistik publik membuka identitas | Sel dengan kurang dari 5 orang digabung atau disembunyikan | Aplikasi |
| Perubahan sepihak data sensitif | Maker-checker pada mutasi dan perubahan KK, log audit yang tidak bisa diubah | Proses |
| Data tidak dihapus setelah tidak diperlukan | Kebijakan retensi per entitas, penghapusan dan anonimisasi terjadwal | Proses |
| Insiden kebocoran | Prosedur tanggap insiden dan pemberitahuan kepada warga dan pihak berwenang sesuai ketentuan | Proses |
| Warga tidak tahu datanya dipakai untuk apa | Pemberitahuan privasi, dasar pemrosesan dicatat, warga bisa meminta akses dan koreksi lewat portal | Hukum dan produk |

Selain itu: cadangan harian terenkripsi dengan uji pemulihan berkala, pemisahan lingkungan uji dari data asli (data uji harus sintetis), dan pemindaian kerentanan dependensi pada setiap rilis.

**Tambahan untuk skala nasional dan pengembang tunggal**

- **Hash NIK memakai kunci rahasia** (HMAC) yang disimpan terpisah dari basis data, bukan hash polos. NIK punya format yang mudah ditebak, sehingga hash polos bisa dibalik dengan menebak.
- **Tidak ada pencarian NIK lintas RW.** Satu-satunya jalur lintas RW adalah permintaan pindah yang disetujui kedua pihak.
- **Peran tingkat atas hanya melihat agregat**, dengan sel kecil disembunyikan, terutama di halaman tingkat RW dan RT.
- **Lokasi data dan kewajiban sebagai penyelenggara sistem elektronik** perlu dipastikan lewat konsultasi hukum sebelum beroperasi di luar pilot.
- **Risiko satu orang.** Kunci enkripsi dan akses produksi hanya di satu tangan, jadi siapkan salinan kunci yang aman, dokumentasi pemulihan, 2FA di semua akun infrastruktur, dan hindari membuka data produksi untuk debugging.

## Modul dan roadmap

&#91;embedded content: roadmap · 3 fase, 3 gerbang\]

Model data dan alamat berjenjang dirancang penuh sejak fase 1, tetapi yang diaktifkan hanya tingkat RW dan RT. Urutan fitur mengikuti nilai bagi pengurus: surat pengantar masuk fase 1 karena itu alasan paling kuat bagi pengurus untuk memakai sistem. Iuran menyusul di fase 2 karena menyentuh uang dan butuh kepercayaan yang dibangun lebih dulu. Peran kelurahan ke atas, pindah antar-RW, peta hunian, aduan, ronda, posyandu, dan bansos sengaja ditunda sampai inti terbukti dipakai. Untuk pengembang tunggal, tiap fase sebaiknya dipakai nyata dulu sebelum fase berikutnya dimulai.

## Keputusan terbuka

Sudah diputuskan: hierarki nasional dirancang penuh dari atas dan dibangun mulai dari RW; wilayah selain RW dan RT ditunda; identitas lintas-RW lewat hash NIK; pengembang tunggal; kerja sama awal dari RW atau kelurahan. Sisanya masih terbuka, dan tiga pertama paling memengaruhi desain.

- [ ] **Sumber data wilayah**: dari mana kode wilayah dan pohon sampai kelurahan atau desa diambil, dan seberapa sering diperbarui?
- [ ] **Mekanisme klaim RW**: bukti apa yang diterima, dan siapa yang menyetujui bila kelurahan belum bermitra?
- [ ] **Badan penyelenggara**: platform dioperasikan atas nama siapa (pribadi, perusahaan, atau koperasi)? Ini memengaruhi kewajiban PDP dan kerja sama dengan kelurahan.
- [ ] **Model bisnis dan pembayar**: RW atau kelurahan membayar langganan, gratis dengan biaya per transaksi iuran, atau proyek per klien?
- [ ] **Mitra pilot**: RW atau kelurahan mana, berapa KK, dan siapa yang mau jadi pengguna pertama?
- [ ] **Verifikasi warga**: login lewat OTP WhatsApp, undangan dari pengurus, atau verifikasi tatap muka di awal?
- [ ] **Lokasi data**: apakah data wajib disimpan di server dalam negeri (memengaruhi pilihan penyedia hosting)?
- [ ] **Stack dan hosting**: pilih yang paling kamu kuasai; arsitektur di atas tidak bergantung pada satu stack.
- [ ] **Template surat**: format surat pengantar yang dipakai kelurahan pilot, dan apakah tanda tangan digital diterima atau tetap perlu cap basah.
- [ ] **Pembayaran iuran**: pencatatan manual dulu, atau langsung QRIS dan virtual account?
- [ ] **Peta hunian**: perlu sejak fase 1, atau cukup alamat teks lebih dulu?
