from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.wilayah.models import WilayahNode, WilayahLevel, PengurusProfile, PengurusRole
from apps.kependudukan.models import IdentitasOrang, Warga, StatusKeberadaan, JenisKelamin, Agama, StatusPerkawinan, KartuKeluarga, KeanggotaanKK, HubunganKeluarga
from apps.kependudukan.crypto import hmac_blind_index
from apps.hunian.models import Hunian, Domisili, StatusKepemilikan, PeranDiHunian
from apps.layanan.models import SuratPengantar, KategoriLayanan, StatusSurat
from apps.iuran.models import PosIuran, TagihanIuran, StatusPembayaran, MetodePembayaran
from apps.audit.models import AuditLog, AuditAction
from apps.informasi.models import Pengumuman, KategoriPengumuman, StatusPengumuman, LingkupDistribusi
from decimal import Decimal
import datetime

class PortalEndToEndTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Wilayah Hierarchy
        self.rw = WilayahNode.objects.create(level=WilayahLevel.RW, nama="RW 07")
        self.rt01 = WilayahNode.objects.create(parent=self.rw, level=WilayahLevel.RT, nama="RT 01")
        self.rt02 = WilayahNode.objects.create(parent=self.rw, level=WilayahLevel.RT, nama="RT 02")

        # 2. Dwellings
        self.hunian = Hunian.objects.create(
            rt=self.rt01,
            nomor_rumah="No. 14A",
            alamat_lengkap="Jl. Jalaprang No. 14A",
            status_kepemilikan=StatusKepemilikan.MILIK_SENDIRI
        )
        self.hunian_rt2 = Hunian.objects.create(
            rt=self.rt02,
            nomor_rumah="Blok B/2",
            alamat_lengkap="Jl. Sukaluyu Blok B/2",
            status_kepemilikan=StatusKepemilikan.MILIK_SENDIRI
        )

        # 3. Citizens
        raw_nik = "3273011508850001"
        b_idx = hmac_blind_index(raw_nik)
        identitas = IdentitasOrang.objects.create(nik_blind_index=b_idx)
        self.warga_budi = Warga.objects.create(
            identitas=identitas,
            rw=self.rw,
            nama_lengkap="Budi Santoso",
            tempat_lahir="Bandung",
            tanggal_lahir=datetime.date(1985, 8, 15),
            jenis_kelamin=JenisKelamin.LAKI_LAKI,
            agama=Agama.ISLAM,
            status_perkawinan=StatusPerkawinan.KAWIN,
            status_keberadaan=StatusKeberadaan.AKTIF
        )
        self.warga_budi.set_nik(raw_nik)
        self.warga_budi.save()

        Domisili.objects.create(
            hunian=self.hunian,
            warga=self.warga_budi,
            peran_di_hunian=PeranDiHunian.KEPALA_RUMAH_TANGGA,
            is_active=True
        )

        # 4. Accounts
        # a. Ketua RW
        self.user_rw = User.objects.create_user(username="rw07_ketua", password="password123", first_name="Ketua", last_name="RW")
        PengurusProfile.objects.create(user=self.user_rw, wilayah_node=self.rw, role=PengurusRole.KETUA_RW)

        # b. Ketua RT 01
        self.user_rt = User.objects.create_user(username="rt01_ketua", password="password123", first_name="Ketua", last_name="RT 01")
        PengurusProfile.objects.create(user=self.user_rt, wilayah_node=self.rt01, role=PengurusRole.KETUA_RT)

        # c. Bendahara RT 01
        self.user_bendahara = User.objects.create_user(username="rt01_bendahara", password="password123", first_name="Bendahara", last_name="RT 01")
        PengurusProfile.objects.create(user=self.user_bendahara, wilayah_node=self.rt01, role=PengurusRole.BENDAHARA_RT)

        # d. Regular Citizen Account (Budi Santoso)
        self.user_warga = User.objects.create_user(username="warga_budi", password="password123", first_name="Budi", last_name="Santoso")
        PengurusProfile.objects.create(user=self.user_warga, wilayah_node=self.rt01, role=PengurusRole.WARGA, warga=self.warga_budi)

    def test_login_and_dashboard_access_for_officers(self):
        # Unauthenticated redirects
        resp = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(resp.status_code, 302)

        # Ketua RT Login
        self.client.login(username="rt01_ketua", password="password123")
        dash_resp = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Dashboard Lingkungan RT/RW")
        self.assertContains(dash_resp, "Total Warga Aktif")

    def test_warga_user_has_citizen_portal_and_restricted_from_officer_features(self):
        """
        Verify that a citizen account (WARGA):
        1. Sees Citizen Portal (not officer command center).
        2. Is strictly blocked from accessing other people's resident list, dwellings, unmasking, and treasurer tools.
        """
        self.client.login(username="warga_budi", password="password123")

        # 1. Citizen Dashboard
        dash_resp = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Portal Warga")
        self.assertContains(dash_resp, "Budi Santoso")
        self.assertContains(dash_resp, "No. 14A")

        # 2. Blocked from Officer Resident Register (/warga/)
        warga_list_resp = self.client.get(reverse('portal:warga_list'))
        self.assertEqual(warga_list_resp.status_code, 302)
        self.assertRedirects(warga_list_resp, reverse('portal:dashboard'))

        # 3. Blocked from Adding New Citizens (/warga/tambah/)
        warga_add_resp = self.client.get(reverse('portal:warga_create'))
        self.assertEqual(warga_add_resp.status_code, 302)
        self.assertRedirects(warga_add_resp, reverse('portal:dashboard'))

        # 4. Blocked from Viewing All Dwellings (/hunian/)
        hunian_resp = self.client.get(reverse('portal:hunian_list'))
        self.assertEqual(hunian_resp.status_code, 302)
        self.assertRedirects(hunian_resp, reverse('portal:dashboard'))

        # 5. Blocked from Unmasking PII
        unmask_resp = self.client.post(
            reverse('portal:warga_unmask', kwargs={'warga_id': self.warga_budi.id}),
            {'alasan': 'Hacking test'}
        )
        self.assertEqual(unmask_resp.status_code, 403)

        # 6. Blocked from Approving Letters
        surat = SuratPengantar.objects.create(
            nomor_surat="099/RT01/2026",
            pemohon_warga=self.warga_budi,
            rt=self.rt01,
            rw=self.rw,
            kategori_layanan=KategoriLayanan.SKCK,
            keperluan="Tes"
        )
        approve_resp = self.client.post(
            reverse('portal:surat_approve', kwargs={'surat_id': surat.id}),
            {'action': 'approve_rt'}
        )
        self.assertEqual(approve_resp.status_code, 302)
        self.assertRedirects(approve_resp, reverse('portal:surat_list'))
        surat.refresh_from_db()
        self.assertEqual(surat.status_surat, StatusSurat.PENGAJUAN)

        # 7. Blocked from Recording Dues Payments
        pos = PosIuran.objects.create(node=self.rt01, nama_pos="Kas RT", nominal=Decimal("10000.00"))
        tagihan = TagihanIuran.objects.create(
            hunian=self.hunian,
            pos_iuran=pos,
            periode_bulan="2026-10",
            jumlah_tagihan=Decimal("10000.00"),
            jatuh_tempo=datetime.date(2026, 10, 20)
        )
        pay_attempt = self.client.post(
            reverse('portal:iuran_bayar', kwargs={'tagihan_id': tagihan.id}),
            {'metode_pembayaran': 'TUNAI'}
        )
        self.assertEqual(pay_attempt.status_code, 302)
        self.assertRedirects(pay_attempt, reverse('portal:dashboard'))
        tagihan.refresh_from_db()
        self.assertEqual(tagihan.status_pembayaran, StatusPembayaran.BELUM_BAYAR)

        # 8. Allowed: Access own household dues (/iuran-saya/)
        iuran_saya_resp = self.client.get(reverse('portal:iuran_saya'))
        self.assertEqual(iuran_saya_resp.status_code, 200)
        self.assertContains(iuran_saya_resp, "Status Kas")
        self.assertContains(iuran_saya_resp, "No. 14A")

    def test_bendahara_permissions(self):
        """
        Verify that a Treasurer (BENDAHARA_RT):
        1. Can access dues collection desk and settle payments.
        2. Cannot approve administrative letters.
        """
        self.client.login(username="rt01_bendahara", password="password123")

        # Access dues desk
        desk_resp = self.client.get(reverse('portal:iuran_desk'))
        self.assertEqual(desk_resp.status_code, 200)

        # Settle payment
        pos = PosIuran.objects.create(node=self.rt01, nama_pos="Sampah RT", nominal=Decimal("20000.00"))
        tagihan = TagihanIuran.objects.create(
            hunian=self.hunian,
            pos_iuran=pos,
            periode_bulan="2026-10",
            jumlah_tagihan=Decimal("20000.00"),
            jatuh_tempo=datetime.date(2026, 10, 20)
        )
        pay_resp = self.client.post(
            reverse('portal:iuran_bayar', kwargs={'tagihan_id': tagihan.id}),
            {'metode_pembayaran': 'TUNAI'}
        )
        self.assertEqual(pay_resp.status_code, 302)
        tagihan.refresh_from_db()
        self.assertEqual(tagihan.status_pembayaran, StatusPembayaran.LUNAS)

        # Blocked from approving letters
        surat = SuratPengantar.objects.create(
            nomor_surat="088/RT01/2026",
            pemohon_warga=self.warga_budi,
            rt=self.rt01,
            rw=self.rw,
            kategori_layanan=KategoriLayanan.SKCK,
            keperluan="Melamar Kerja"
        )
        approve_resp = self.client.post(
            reverse('portal:surat_approve', kwargs={'surat_id': surat.id}),
            {'action': 'approve_rt'}
        )
        self.assertEqual(approve_resp.status_code, 302)
        surat.refresh_from_db()
        self.assertEqual(surat.status_surat, StatusSurat.PENGAJUAN)

    def test_warga_create_and_unmask_with_audit_by_officer(self):
        self.client.login(username="rt01_ketua", password="password123")

        new_nik = "3273012204880002"
        create_resp = self.client.post(reverse('portal:warga_create'), {
            'nik': new_nik,
            'nama_lengkap': 'Siti Aminah',
            'tempat_lahir': 'Bandung',
            'tanggal_lahir': '1988-04-22',
            'jenis_kelamin': 'P',
            'agama': 'ISLAM',
            'status_perkawinan': 'KAWIN',
            'pekerjaan': 'Ibu Rumah Tangga',
            'nomor_telepon': '081234567891',
            'hunian_id': str(self.hunian.id),
            'peran_di_hunian': 'ANGGOTA'
        })
        self.assertRedirects(create_resp, reverse('portal:warga_list'))

        warga_siti = Warga.objects.get(nama_lengkap='Siti Aminah')
        self.assertEqual(warga_siti.nik_masked, "327301******0002")

        unmask_resp = self.client.post(
            reverse('portal:warga_unmask', kwargs={'warga_id': warga_siti.id}),
            {'alasan': 'Verifikasi Berkas KTP'}
        )
        self.assertEqual(unmask_resp.status_code, 200)
        data = unmask_resp.json()
        self.assertEqual(data['raw_nik'], new_nik)

        audit_entry = AuditLog.objects.filter(
            action=AuditAction.READ_PII,
            entity_id=str(warga_siti.id)
        ).first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.actor, self.user_rt)

    def test_surat_lifecycle_and_public_qr_verification(self):
        self.client.login(username="rt01_ketua", password="password123")

        surat_resp = self.client.post(reverse('portal:surat_create'), {
            'pemohon_warga_id': str(self.warga_budi.id),
            'kategori_layanan': KategoriLayanan.SKCK,
            'keperluan': 'Melamar Pekerjaan PT KAI'
        })
        self.assertRedirects(surat_resp, reverse('portal:surat_list'))

        surat = SuratPengantar.objects.get(pemohon_warga=self.warga_budi)
        self.assertEqual(surat.status_surat, StatusSurat.PENGAJUAN)

        # RT Approval
        self.client.post(reverse('portal:surat_approve', kwargs={'surat_id': surat.id}), {
            'action': 'approve_rt'
        })
        surat.refresh_from_db()
        self.assertEqual(surat.status_surat, StatusSurat.DISETUJUI_RT)

        # RW Approval
        self.client.login(username="rw07_ketua", password="password123")
        self.client.post(reverse('portal:surat_approve', kwargs={'surat_id': surat.id}), {
            'action': 'approve_rw'
        })
        surat.refresh_from_db()
        self.assertEqual(surat.status_surat, StatusSurat.DISETUJUI_RW)

        # Print / View layout
        print_resp = self.client.get(reverse('portal:surat_print', kwargs={'surat_id': surat.id}))
        self.assertEqual(print_resp.status_code, 200)
        self.assertContains(print_resp, "SURAT PENGANTAR")

        # Public QR Verification
        self.client.logout()
        verif_resp = self.client.get(
            reverse('portal:verifikasi_surat', kwargs={'token': surat.verification_token})
        )
        self.assertEqual(verif_resp.status_code, 200)
        self.assertContains(verif_resp, "Dokumen Asli")
        self.assertEqual(surat.verifikasi_logs.count(), 1)

    def test_role_boundary_enforcement_and_separation_of_duties(self):
        """
        Verify strict role boundaries:
        1. Bendahara CANNOT approve letters.
        2. Ketua RT CANNOT publish RW letters.
        3. Ketua RT CANNOT act as cashier / collect dues (reserved for Bendahara).
        4. Bendahara CANNOT unmask sensitive NIK.
        """
        # Create a test letter
        surat = SuratPengantar.objects.create(
            nomor_surat="001/RT01-RW07/X/2026",
            pemohon_warga=self.warga_budi,
            rt=self.rt01,
            rw=self.rw,
            kategori_layanan=KategoriLayanan.DOMISILI,
            status_surat=StatusSurat.PENGAJUAN
        )

        # 1. Bendahara tries to approve letter -> BLOCKED
        self.client.login(username="rt01_bendahara", password="password123")
        resp = self.client.post(reverse('portal:surat_approve', kwargs={'surat_id': surat.id}), {
            'action': 'approve_rt'
        })
        surat.refresh_from_db()
        self.assertEqual(surat.status_surat, StatusSurat.PENGAJUAN, "Bendahara must not approve letters")

        # 2. Bendahara tries to unmask NIK -> BLOCKED (403)
        unmask_resp = self.client.post(reverse('portal:warga_unmask', kwargs={'warga_id': self.warga_budi.id}), {
            'alasan': 'Iseng cek data'
        })
        self.assertEqual(unmask_resp.status_code, 403, "Bendahara must not unmask NIK")

        # 3. Ketua RT tries to publish RW letter -> BLOCKED
        self.client.login(username="rt01_ketua", password="password123")
        surat.status_surat = StatusSurat.DISETUJUI_RT
        surat.save()
        resp_rw = self.client.post(reverse('portal:surat_approve', kwargs={'surat_id': surat.id}), {
            'action': 'approve_rw'
        })
        surat.refresh_from_db()
        self.assertEqual(surat.status_surat, StatusSurat.DISETUJUI_RT, "Ketua RT must not publish RW letters")

        # 4. Ketua RT tries to collect dues -> BLOCKED (Redirected with error)
        pos = PosIuran.objects.create(node=self.rt01, nama_pos="Kebersihan", nominal=Decimal('25000'))
        tagihan = TagihanIuran.objects.create(
            hunian=self.hunian,
            pos_iuran=pos,
            periode_bulan="2026-10",
            jatuh_tempo=datetime.date(2026, 10, 20),
            jumlah_tagihan=Decimal('25000')
        )
        pay_resp = self.client.post(reverse('portal:iuran_bayar', kwargs={'tagihan_id': tagihan.id}))
        tagihan.refresh_from_db()
        self.assertEqual(tagihan.status_pembayaran, StatusPembayaran.BELUM_BAYAR, "Ketua RT must not act as cashier")

        # 5. Bendahara collects dues -> SUCCESS
        self.client.login(username="rt01_bendahara", password="password123")
        pay_success = self.client.post(reverse('portal:iuran_bayar', kwargs={'tagihan_id': tagihan.id}))
        tagihan.refresh_from_db()
        self.assertEqual(tagihan.status_pembayaran, StatusPembayaran.LUNAS, "Bendahara should successfully collect dues")

    def test_mading_digital_lifecycle_and_moderation(self):
        """
        Test Mading Digital (Opsi B):
        1. Officer publishes emergency notice -> immediate publication.
        2. Citizen posts community news -> enters MENUNGGU_MODERASI.
        3. Officer approves warta -> status changes to TERBIT.
        4. Verified visible on Mading feed and dashboard.
        """
        # 1. Ketua RT publishes an announcement
        self.client.login(username="rt01_ketua", password="password123")
        post_resp = self.client.post(reverse('portal:mading_create'), {
            'judul': 'Kerja Bakti Bersih Saluran Air',
            'kategori': KategoriPengumuman.AGENDA,
            'lingkup': LingkupDistribusi.RT,
            'isi': 'Diharapkan membawa cangkul dan sapu lidi.',
            'lokasi_kegiatan': 'Pos Ronda RT 01',
            'is_pinned': '1'
        })
        self.assertEqual(post_resp.status_code, 302)
        pengumuman_rt = Pengumuman.objects.get(judul='Kerja Bakti Bersih Saluran Air')
        self.assertEqual(pengumuman_rt.status, StatusPengumuman.TERBIT)
        self.assertTrue(pengumuman_rt.is_pinned)

        # 2. Citizen posts community news (Opsi B - Moderation queue)
        self.client.login(username="warga_budi", password="password123")
        warga_post_resp = self.client.post(reverse('portal:mading_create'), {
            'judul': 'Kucing Anggora Abu-abu Hilang',
            'kategori': KategoriPengumuman.KABAR_WARGA,
            'isi': 'Telah hilang kucing anggora jinak di sekitar No. 14A.'
        })
        self.assertEqual(warga_post_resp.status_code, 302)
        warta_budi = Pengumuman.objects.get(judul='Kucing Anggora Abu-abu Hilang')
        self.assertEqual(warta_budi.status, StatusPengumuman.MENUNGGU_KONFIRMASI, "Citizen post must require confirmation")

        # Public list doesn't show unapproved post yet
        list_resp = self.client.get(reverse('portal:mading_list'))
        self.assertContains(list_resp, "Kerja Bakti Bersih Saluran Air")
        self.assertNotContains(list_resp, "Kucing Anggora Abu-abu Hilang")

        # 3. Ketua RT moderates and approves
        self.client.login(username="rt01_ketua", password="password123")
        mod_resp = self.client.post(reverse('portal:mading_moderasi', kwargs={'pengumuman_id': warta_budi.id}), {
            'action': 'approve'
        })
        warta_budi.refresh_from_db()
        self.assertEqual(warta_budi.status, StatusPengumuman.TERBIT)

        # Now visible on Mading
        list_resp2 = self.client.get(reverse('portal:mading_list'))
        self.assertContains(list_resp2, "Kucing Anggora Abu-abu Hilang")

        # Detail page and WhatsApp share link
        detail_resp = self.client.get(reverse('portal:mading_detail', kwargs={'pengumuman_id': warta_budi.id}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Sebarkan ke WhatsApp")

    def test_citizen_registration_smart_match(self):
        """
        Test Opsi 1: Smart Match.
        When an unlinked citizen whose NIK is already registered by RT signs up,
        the system matches the NIK instantly, activates account (is_active=True), and logs in.
        """
        # Create an unlinked resident in RT 01
        nik_warga = "3273012010900005"
        b_idx = hmac_blind_index(nik_warga)
        identitas = IdentitasOrang.objects.create(nik_blind_index=b_idx)
        warga_siti = Warga.objects.create(
            identitas=identitas,
            rw=self.rw,
            nama_lengkap="Siti Aminah",
            tempat_lahir="Bandung",
            tanggal_lahir=datetime.date(1990, 10, 20),
            jenis_kelamin=JenisKelamin.PEREMPUAN,
            agama=Agama.ISLAM,
            status_perkawinan=StatusPerkawinan.KAWIN,
            status_keberadaan=StatusKeberadaan.AKTIF
        )
        warga_siti.set_nik(nik_warga)
        warga_siti.save()

        # Siti signs up via /daftar/
        resp = self.client.post(reverse('portal:register'), {
            'nama_lengkap': 'Siti Aminah',
            'nik': nik_warga,
            'nomor_wa': '081234567890',
            'rt_id': str(self.rt01.id),
            'nomor_rumah': 'No. 14B',
            'username': 'siti_aminah',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('portal:dashboard'))

        # Check user is active and linked to warga_siti
        user_siti = User.objects.get(username='siti_aminah')
        self.assertTrue(user_siti.is_active)
        profile_siti = PengurusProfile.objects.get(user=user_siti)
        self.assertEqual(profile_siti.warga, warga_siti)
        self.assertEqual(profile_siti.role, PengurusRole.WARGA)

    def test_citizen_registration_new_resident_and_rt_confirmation(self):
        """
        Test Opsi 1: New Resident Registration & RT Confirmation Queue.
        1. New resident signs up -> account queued (is_active=False).
        2. Attempted login before confirmation -> warning message.
        3. Ketua RT sees pending request on dashboard & approves.
        4. Resident can now log in successfully.
        """
        new_nik = "3273011111950009"
        reg_resp = self.client.post(reverse('portal:register'), {
            'nama_lengkap': 'Ahmad Fauzi',
            'nik': new_nik,
            'nomor_wa': '082211334455',
            'rt_id': str(self.rt01.id),
            'nomor_rumah': 'Blok C No. 3',
            'username': 'ahmad_fauzi',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(reg_resp.status_code, 302)
        self.assertRedirects(reg_resp, reverse('portal:login'))

        # User created with is_active=False
        user_ahmad = User.objects.get(username='ahmad_fauzi')
        self.assertFalse(user_ahmad.is_active)

        # Attempt to login before RT confirmation -> blocked with warning
        login_resp = self.client.post(reverse('portal:login'), {
            'username': 'ahmad_fauzi',
            'password': 'password123'
        })
        self.assertEqual(login_resp.status_code, 200)
        self.assertContains(login_resp, "Menunggu Konfirmasi dari Ketua RT")

        # Ketua RT logs in and views dashboard
        self.client.login(username="rt01_ketua", password="password123")
        dash_resp = self.client.get(reverse('portal:dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "Ahmad Fauzi")
        self.assertContains(dash_resp, "Konfirmasi Pendaftaran Akun Warga Baru")

        # Ketua RT approves the registration
        profile_ahmad = PengurusProfile.objects.get(user=user_ahmad)
        approve_resp = self.client.post(reverse('portal:konfirmasi_warga_baru', kwargs={'profile_id': profile_ahmad.id}), {
            'action': 'approve'
        })
        self.assertEqual(approve_resp.status_code, 302)

        # User is now active
        user_ahmad.refresh_from_db()
        self.assertTrue(user_ahmad.is_active)

        # Resident logs in successfully
        self.client.logout()
        res_login = self.client.post(reverse('portal:login'), {
            'username': 'ahmad_fauzi',
            'password': 'password123'
        })
        self.assertEqual(res_login.status_code, 302)
        self.assertRedirects(res_login, reverse('portal:dashboard'))

    def test_pwa_capabilities(self):
        """
        Verify Progressive Web App (PWA) manifest, service worker, and offline page.
        """
        # 1. Manifest
        manifest_resp = self.client.get(reverse('portal:manifest'))
        self.assertEqual(manifest_resp.status_code, 200)
        self.assertIn('application/manifest+json', manifest_resp['Content-Type'])
        self.assertContains(manifest_resp, '"standalone"')
        self.assertContains(manifest_resp, '"WargaIn"')
        self.assertContains(manifest_resp, '"#064e3b"')

        # 2. Service Worker
        sw_resp = self.client.get(reverse('portal:service_worker'))
        self.assertEqual(sw_resp.status_code, 200)
        self.assertIn('application/javascript', sw_resp['Content-Type'])
        self.assertEqual(sw_resp['Service-Worker-Allowed'], '/')

        # 3. Offline Fallback
        offline_resp = self.client.get(reverse('portal:offline'))
        self.assertEqual(offline_resp.status_code, 200)
        self.assertContains(offline_resp, "Sedang Offline")
        self.assertContains(offline_resp, "Nomor Darurat Warga")

