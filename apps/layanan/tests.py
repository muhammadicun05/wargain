from django.test import TestCase
from apps.wilayah.models import WilayahNode, WilayahLevel
from apps.kependudukan.models import IdentitasOrang, Warga
from apps.kependudukan.crypto import hmac_blind_index
from apps.layanan.models import SuratPengantar, VerifikasiSuratLog, KategoriLayanan, StatusSurat
import datetime

class SuratPengantarAndVerificationTestCase(TestCase):
    def setUp(self):
        self.rw = WilayahNode.objects.create(level=WilayahLevel.RW, nama="RW 07")
        self.rt = WilayahNode.objects.create(parent=self.rw, level=WilayahLevel.RT, nama="RT 01")
        
        identitas = IdentitasOrang.objects.create(nik_blind_index=hmac_blind_index("3273011508850001"))
        self.warga = Warga.objects.create(
            identitas=identitas,
            rw=self.rw,
            nama_lengkap="Budi Santoso",
            tempat_lahir="Bandung",
            tanggal_lahir=datetime.date(1985, 8, 15),
            jenis_kelamin="L",
            agama="ISLAM",
            status_perkawinan="KAWIN"
        )
        self.warga.set_nik("3273011508850001")
        self.warga.save()

    def test_surat_pengantar_lifecycle_and_verification(self):
        surat = SuratPengantar.objects.create(
            nomor_surat="045/RT01-RW07/X/2026",
            pemohon_warga=self.warga,
            rt=self.rt,
            rw=self.rw,
            kategori_layanan=KategoriLayanan.SKCK,
            keperluan="Melamar Pekerjaan"
        )
        # Check initial status and presence of unique cryptographic token
        self.assertEqual(surat.status_surat, StatusSurat.PENGAJUAN)
        self.assertTrue(len(surat.verification_token) >= 32)
        self.assertFalse(surat.is_valid_and_active())

        # RT Approval
        surat.status_surat = StatusSurat.DISETUJUI_RT
        surat.save()
        self.assertFalse(surat.is_valid_and_active())

        # RW Approval & Issuance
        surat.status_surat = StatusSurat.DISETUJUI_RW
        surat.berlaku_sampai = datetime.date.today() + datetime.timedelta(days=30)
        surat.save()
        self.assertTrue(surat.is_valid_and_active())

        # Verification Log recording
        vlog = VerifikasiSuratLog.objects.create(
            surat=surat,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Verifier"
        )
        self.assertEqual(surat.verifikasi_logs.count(), 1)
        self.assertEqual(vlog.surat, surat)
