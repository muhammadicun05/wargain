import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.wilayah.models import WilayahNode, WilayahLevel, PengurusProfile, PengurusRole
from apps.kependudukan.models import IdentitasOrang, Warga, KartuKeluarga, KeanggotaanKK, JenisKelamin, Agama, StatusPerkawinan, StatusKeberadaan, HubunganKeluarga
from apps.kependudukan.crypto import hmac_blind_index
from apps.hunian.models import Hunian, Domisili, StatusKepemilikan, PeranDiHunian
from apps.layanan.models import SuratPengantar, KategoriLayanan, StatusSurat
from apps.iuran.models import PosIuran, TagihanIuran, PembayaranIuran, PeriodeFrekuensi, StatusPembayaran, MetodePembayaran
from apps.audit.models import AuditLog, AuditAction

class Command(BaseCommand):
    help = 'Seeds realistic pilot neighborhood data for RW 07 Kelurahan Sukaluyu Bandung.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Memulai seeding data percontohan WargaIn v2..."))

        # 1. Superuser
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@wargain.id',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Administrator',
                'last_name': 'Pusat'
            }
        )
        if created:
            admin_user.set_password('admin1234')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' / 'admin1234' dibuat."))

        # 2. Hierarchy: Jabar -> Bandung -> Cibeunying Kaler -> Sukaluyu -> RW 07 -> RTs
        prov, _ = WilayahNode.objects.get_or_create(
            level=WilayahLevel.PROVINSI,
            nama='Jawa Barat',
            defaults={'kode_pos': '40000', 'kode_wilayah': '32'}
        )
        kota, _ = WilayahNode.objects.get_or_create(
            parent=prov,
            level=WilayahLevel.KOTA,
            nama='Kota Bandung',
            defaults={'kode_pos': '40100', 'kode_wilayah': '32.73'}
        )
        kec, _ = WilayahNode.objects.get_or_create(
            parent=kota,
            level=WilayahLevel.KECAMATAN,
            nama='Cibeunying Kaler',
            defaults={'kode_pos': '40123', 'kode_wilayah': '32.73.01'}
        )
        kel, _ = WilayahNode.objects.get_or_create(
            parent=kec,
            level=WilayahLevel.KELURAHAN,
            nama='Sukaluyu',
            defaults={'kode_pos': '40123', 'kode_wilayah': '32.73.01.1001'}
        )
        rw07, _ = WilayahNode.objects.get_or_create(
            parent=kel,
            level=WilayahLevel.RW,
            nama='RW 07',
            defaults={'kode_pos': '40123', 'metadata': {'alamat_sekretariat': 'Jl. Jalaprang No. 1'}}
        )

        rt01, _ = WilayahNode.objects.get_or_create(
            parent=rw07,
            level=WilayahLevel.RT,
            nama='RT 01',
            defaults={'kode_pos': '40123'}
        )
        rt02, _ = WilayahNode.objects.get_or_create(
            parent=rw07,
            level=WilayahLevel.RT,
            nama='RT 02',
            defaults={'kode_pos': '40123'}
        )
        rt03, _ = WilayahNode.objects.get_or_create(
            parent=rw07,
            level=WilayahLevel.RT,
            nama='RT 03',
            defaults={'kode_pos': '40123'}
        )

        # 3. User Accounts for Leaders
        def create_user_with_role(username, password, first_name, last_name, node, role, phone):
            usr, u_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f'{username}@wargain.id'
                }
            )
            if u_created:
                usr.set_password(password)
                usr.save()
            PengurusProfile.objects.update_or_create(
                user=usr,
                defaults={
                    'wilayah_node': node,
                    'role': role,
                    'nomor_wa': phone
                }
            )
            return usr

        create_user_with_role('rw07_ketua', 'wargain2026', 'Drs. H.', 'Mulyana', rw07, PengurusRole.KETUA_RW, '081220000001')
        create_user_with_role('rt01_ketua', 'wargain2026', 'Bambang', 'Sutrisno', rt01, PengurusRole.KETUA_RT, '081220000002')
        create_user_with_role('rt01_bendahara', 'wargain2026', 'Endang', 'Kusnadi', rt01, PengurusRole.BENDAHARA_RT, '081220000003')
        warga_user = create_user_with_role('warga_budi', 'wargain2026', 'Budi', 'Santoso', rt01, PengurusRole.WARGA, '081234567890')

        # 4. Hunian (Dwellings) in RT 01 & RT 02
        h_14a, _ = Hunian.objects.get_or_create(
            rt=rt01,
            nomor_rumah='No. 14A',
            defaults={
                'alamat_lengkap': 'Jl. Jalaprang No. 14A, Sukaluyu',
                'status_kepemilikan': StatusKepemilikan.MILIK_SENDIRI,
                'koordinat': {'lat': -6.8972, 'lng': 107.6251}
            }
        )
        h_14b, _ = Hunian.objects.get_or_create(
            rt=rt01,
            nomor_rumah='No. 14B',
            defaults={
                'alamat_lengkap': 'Jl. Jalaprang No. 14B, Sukaluyu',
                'status_kepemilikan': StatusKepemilikan.SEWA_KONTRAK,
                'koordinat': {'lat': -6.8973, 'lng': 107.6252}
            }
        )
        h_kos1, _ = Hunian.objects.get_or_create(
            rt=rt01,
            nomor_rumah='Kos Wisma Jalaprang Kmr 01',
            defaults={
                'alamat_lengkap': 'Jl. Jalaprang No. 20, Kamar 01',
                'status_kepemilikan': StatusKepemilikan.KOS,
                'koordinat': {'lat': -6.8975, 'lng': 107.6255}
            }
        )
        h_kos2, _ = Hunian.objects.get_or_create(
            rt=rt01,
            nomor_rumah='Kos Wisma Jalaprang Kmr 02',
            defaults={
                'alamat_lengkap': 'Jl. Jalaprang No. 20, Kamar 02',
                'status_kepemilikan': StatusKepemilikan.KOS,
                'koordinat': {'lat': -6.8975, 'lng': 107.6255}
            }
        )
        h_16, _ = Hunian.objects.get_or_create(
            rt=rt01,
            nomor_rumah='No. 16',
            defaults={
                'alamat_lengkap': 'Jl. Jalaprang No. 16, Sukaluyu',
                'status_kepemilikan': StatusKepemilikan.MILIK_SENDIRI
            }
        )
        h_rt02_1, _ = Hunian.objects.get_or_create(
            rt=rt02,
            nomor_rumah='Blok A/1',
            defaults={
                'alamat_lengkap': 'Jl. Sukaluyu Raya Blok A/1',
                'status_kepemilikan': StatusKepemilikan.MILIK_SENDIRI
            }
        )

        # 5. Helper function to create Warga with Blind Index and AES-GCM
        def enroll_warga(raw_nik, nama, tgl_lahir, jk, agama, status_kawin, pekerjaan, telepon=None):
            b_idx = hmac_blind_index(raw_nik)
            identitas, _ = IdentitasOrang.objects.get_or_create(nik_blind_index=b_idx)
            warga, created = Warga.objects.get_or_create(
                identitas=identitas,
                rw=rw07,
                defaults={
                    'nama_lengkap': nama,
                    'tempat_lahir': 'Bandung',
                    'tanggal_lahir': tgl_lahir,
                    'jenis_kelamin': jk,
                    'agama': agama,
                    'status_perkawinan': status_kawin,
                    'pekerjaan': pekerjaan,
                    'status_keberadaan': StatusKeberadaan.AKTIF,
                    'nomor_telepon': telepon
                }
            )
            warga.set_nik(raw_nik)
            warga.save()
            return warga

        w_budi = enroll_warga('3273011508850001', 'Budi Santoso', datetime.date(1985, 8, 15), JenisKelamin.LAKI_LAKI, Agama.ISLAM, StatusPerkawinan.KAWIN, 'Karyawan Swasta', '081234567890')
        PengurusProfile.objects.filter(user=warga_user).update(warga=w_budi)
        w_siti = enroll_warga('3273012204880002', 'Siti Aminah', datetime.date(1988, 4, 22), JenisKelamin.PEREMPUAN, Agama.ISLAM, StatusPerkawinan.KAWIN, 'Ibu Rumah Tangga', '081234567891')
        w_rizky = enroll_warga('3273010506120003', 'Rizky Pratama', datetime.date(2012, 6, 5), JenisKelamin.LAKI_LAKI, Agama.ISLAM, StatusPerkawinan.BELUM_KAWIN, 'Pelajar SMP')
        
        # Tri-axial demo: Student from Central Java renting a kos room
        w_hendra = enroll_warga('3302011005950004', 'Hendra Wijaya', datetime.date(2003, 5, 10), JenisKelamin.LAKI_LAKI, Agama.ISLAM, StatusPerkawinan.BELUM_KAWIN, 'Mahasiswa ITB', '085712345678')
        
        # Tenant renting No. 14B
        w_dewi = enroll_warga('3273011809930005', 'Dewi Sartika', datetime.date(1993, 9, 18), JenisKelamin.PEREMPUAN, Agama.ISLAM, StatusPerkawinan.BELUM_KAWIN, 'Desainer UI/UX', '081398765432')
        
        # Senior citizen living in No. 16
        w_ahmad = enroll_warga('3273010101600006', 'H. Ahmad Dahlan', datetime.date(1960, 1, 1), JenisKelamin.LAKI_LAKI, Agama.ISLAM, StatusPerkawinan.KAWIN, 'Pensiunan Guru', '081122334455')

        # 6. Kartu Keluarga (Civil Registries)
        kk_budi, _ = KartuKeluarga.objects.get_or_create(
            rw=rw07,
            nomor_kk_masked='327301******0001',
            defaults={'alamat_kk': 'Jl. Jalaprang No. 14A RT 01 RW 07 Sukaluyu'}
        )
        kk_budi.set_nomor_kk('3273012010150001')
        kk_budi.save()

        KeanggotaanKK.objects.get_or_create(kartu_keluarga=kk_budi, warga=w_budi, defaults={'status_hubungan': HubunganKeluarga.KEPALA_KELUARGA})
        KeanggotaanKK.objects.get_or_create(kartu_keluarga=kk_budi, warga=w_siti, defaults={'status_hubungan': HubunganKeluarga.ISTRI})
        KeanggotaanKK.objects.get_or_create(kartu_keluarga=kk_budi, warga=w_rizky, defaults={'status_hubungan': HubunganKeluarga.ANAK})

        kk_ahmad, _ = KartuKeluarga.objects.get_or_create(
            rw=rw07,
            nomor_kk_masked='327301******0002',
            defaults={'alamat_kk': 'Jl. Jalaprang No. 16 RT 01 RW 07 Sukaluyu'}
        )
        kk_ahmad.set_nomor_kk('3273011005800002')
        kk_ahmad.save()
        KeanggotaanKK.objects.get_or_create(kartu_keluarga=kk_ahmad, warga=w_ahmad, defaults={'status_hubungan': HubunganKeluarga.KEPALA_KELUARGA})

        # Notice: Hendra Wijaya and Dewi Sartika do NOT belong to local KKs, yet have active physical domisili below:

        # 7. Domisili (Physical Dwelling Linkage)
        Domisili.objects.get_or_create(hunian=h_14a, warga=w_budi, defaults={'peran_di_hunian': PeranDiHunian.KEPALA_RUMAH_TANGGA, 'is_active': True})
        Domisili.objects.get_or_create(hunian=h_14a, warga=w_siti, defaults={'peran_di_hunian': PeranDiHunian.ANGGOTA, 'is_active': True})
        Domisili.objects.get_or_create(hunian=h_14a, warga=w_rizky, defaults={'peran_di_hunian': PeranDiHunian.ANGGOTA, 'is_active': True})

        Domisili.objects.get_or_create(hunian=h_14b, warga=w_dewi, defaults={'peran_di_hunian': PeranDiHunian.PENYEWA_UTAMA, 'is_active': True})
        Domisili.objects.get_or_create(hunian=h_kos1, warga=w_hendra, defaults={'peran_di_hunian': PeranDiHunian.PENGHUNI_KOS, 'is_active': True})
        Domisili.objects.get_or_create(hunian=h_16, warga=w_ahmad, defaults={'peran_di_hunian': PeranDiHunian.KEPALA_RUMAH_TANGGA, 'is_active': True})

        # 8. Pos Iuran & Billing
        pos_sampah, _ = PosIuran.objects.get_or_create(
            node=rt01,
            nama_pos='Iuran Kebersihan & Sampah RT 01',
            defaults={'nominal': Decimal('30000.00'), 'periode_frekuensi': PeriodeFrekuensi.BULANAN, 'is_active': True}
        )
        pos_keamanan, _ = PosIuran.objects.get_or_create(
            node=rw07,
            nama_pos='Kas Keamanan & Ronda Malam RW 07',
            defaults={'nominal': Decimal('25000.00'), 'periode_frekuensi': PeriodeFrekuensi.BULANAN, 'is_active': True}
        )

        curr_month = timezone.now().strftime('%Y-%m')
        due_date = timezone.now().date().replace(day=20)

        # Generate Tagihan for No. 14A, 14B, Kos
        for h in [h_14a, h_14b, h_kos1, h_16]:
            for pos in [pos_sampah, pos_keamanan]:
                TagihanIuran.objects.get_or_create(
                    hunian=h,
                    pos_iuran=pos,
                    periode_bulan=curr_month,
                    defaults={'jumlah_tagihan': pos.nominal, 'status_pembayaran': StatusPembayaran.BELUM_BAYAR, 'jatuh_tempo': due_date}
                )

        # Settle payment for No. 14A (Budi Santoso)
        t_14a_sampah = TagihanIuran.objects.get(hunian=h_14a, pos_iuran=pos_sampah, periode_bulan=curr_month)
        t_14a_sampah.status_pembayaran = StatusPembayaran.LUNAS
        t_14a_sampah.save()

        PembayaranIuran.objects.get_or_create(
            tagihan=t_14a_sampah,
            nomor_kuitansi=f'KWT-{curr_month.replace("-", "")}-0001',
            defaults={
                'jumlah_dibayar': t_14a_sampah.jumlah_tagihan,
                'metode_pembayaran': MetodePembayaran.TUNAI,
                'diverifikasi_oleh': User.objects.get(username='rt01_bendahara')
            }
        )

        t_14a_keamanan = TagihanIuran.objects.get(hunian=h_14a, pos_iuran=pos_keamanan, periode_bulan=curr_month)
        t_14a_keamanan.status_pembayaran = StatusPembayaran.LUNAS
        t_14a_keamanan.save()

        PembayaranIuran.objects.get_or_create(
            tagihan=t_14a_keamanan,
            nomor_kuitansi=f'KWT-{curr_month.replace("-", "")}-0002',
            defaults={
                'jumlah_dibayar': t_14a_keamanan.jumlah_tagihan,
                'metode_pembayaran': MetodePembayaran.TRANSFER_BANK,
                'diverifikasi_oleh': User.objects.get(username='rt01_bendahara')
            }
        )

        # 9. Surat Pengantar & QR Token
        surat1, _ = SuratPengantar.objects.get_or_create(
            nomor_surat='045/RT01-RW07/X/2026',
            defaults={
                'pemohon_warga': w_budi,
                'rt': rt01,
                'rw': rw07,
                'kategori_layanan': KategoriLayanan.SKCK,
                'keperluan': 'Persyaratan Melamar Pekerjaan BUMN Telkom',
                'status_surat': StatusSurat.DISETUJUI_RW,
                'verification_token': 'skck-budi-santoso-token-2026-x9a8b7c6',
                'diterbitkan_pada': timezone.now() - datetime.timedelta(days=2),
                'berlaku_sampai': timezone.now().date() + datetime.timedelta(days=28)
            }
        )

        surat2, _ = SuratPengantar.objects.get_or_create(
            nomor_surat='046/RT01-RW07/X/2026',
            defaults={
                'pemohon_warga': w_hendra,
                'rt': rt01,
                'rw': rw07,
                'kategori_layanan': KategoriLayanan.DOMISILI,
                'keperluan': 'Keterangan Domisili Kos untuk Pembukaan Rekening Bank Mandiri',
                'status_surat': StatusSurat.PENGAJUAN
            }
        )

        # 10. Audit Log Initial Entry
        AuditLog.objects.create(
            actor=admin_user,
            action=AuditAction.INSERT,
            entity_name='WilayahNode',
            entity_id=str(rw07.id),
            new_values={'nama': 'RW 07 Sukaluyu', 'initial_seed': True},
            ip_address='127.0.0.1',
            user_agent='WargaIn Initial Data Seeder'
        )

        self.stdout.write(self.style.SUCCESS("Seeding berhasil diselesaikan secara sempurna!"))
        self.stdout.write(self.style.SUCCESS("Akun Login:"))
        self.stdout.write(" - Admin Portal: admin / admin1234")
        self.stdout.write(" - Ketua RW 07: rw07_ketua / wargain2026")
        self.stdout.write(" - Ketua RT 01: rt01_ketua / wargain2026")
        self.stdout.write(" - Bendahara RT 01: rt01_bendahara / wargain2026")
        self.stdout.write(" - Akun Warga: warga_budi / wargain2026")
