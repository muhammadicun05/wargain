from django.test import TestCase
from apps.kependudukan.crypto import hmac_blind_index, encrypt_pii, decrypt_pii, mask_nik, mask_kk
from apps.wilayah.models import WilayahNode, WilayahLevel
from apps.kependudukan.models import IdentitasOrang, Warga, KartuKeluarga, KeanggotaanKK, HubunganKeluarga
from apps.hunian.models import Hunian, Domisili, StatusKepemilikan, PeranDiHunian
import datetime

class CryptoAndPDPTestCase(TestCase):
    def test_hmac_blind_index_is_deterministic_and_safe(self):
        nik = "3273011508850001"
        idx1 = hmac_blind_index(nik)
        idx2 = hmac_blind_index("3273-0115-0885-0001")  # strips punctuation
        self.assertEqual(len(idx1), 64)
        self.assertEqual(idx1, idx2)

    def test_aes_gcm_encryption_and_decryption_roundtrip(self):
        raw_nik = "3273011508850001"
        encrypted = encrypt_pii(raw_nik)
        # Check that encrypted is not plaintext
        self.assertNotIn(raw_nik.encode(), encrypted)
        # Check that payload contains IV + ciphertext + tag (length >= 28)
        self.assertGreaterEqual(len(encrypted), 28)
        # Decrypt
        decrypted = decrypt_pii(encrypted)
        self.assertEqual(decrypted, raw_nik)

    def test_masking_nik_and_kk(self):
        nik = "3273011508850001"
        kk = "3273012010150001"
        self.assertEqual(mask_nik(nik), "327301******0001")
        self.assertEqual(mask_kk(kk), "327301******0001")


class TriAxialSeparationTestCase(TestCase):
    def setUp(self):
        self.rw = WilayahNode.objects.create(
            level=WilayahLevel.RW,
            nama="RW 07"
        )
        self.rt = WilayahNode.objects.create(
            parent=self.rw,
            level=WilayahLevel.RT,
            nama="RT 01"
        )

    def test_boarding_student_has_domicile_without_local_kk(self):
        """
        Tests the Tri-Axial model: A student living in a kos has an active Domisili
        in RT 01, but does NOT need an artificial local KartuKeluarga.
        """
        raw_nik = "3302011005950004"
        blind_idx = hmac_blind_index(raw_nik)
        identitas = IdentitasOrang.objects.create(nik_blind_index=blind_idx)
        
        warga = Warga.objects.create(
            identitas=identitas,
            rw=self.rw,
            nama_lengkap="Hendra Wijaya",
            tempat_lahir="Purwokerto",
            tanggal_lahir=datetime.date(2003, 5, 10),
            jenis_kelamin="L",
            agama="ISLAM",
            status_perkawinan="BELUM_KAWIN",
            pekerjaan="Mahasiswa"
        )
        warga.set_nik(raw_nik)
        warga.save()

        hunian_kos = Hunian.objects.create(
            rt=self.rt,
            nomor_rumah="Kos Kamar 01",
            alamat_lengkap="Jl. Jalaprang No. 20",
            status_kepemilikan=StatusKepemilikan.KOS
        )

        domisili = Domisili.objects.create(
            hunian=hunian_kos,
            warga=warga,
            peran_di_hunian=PeranDiHunian.PENGHUNI_KOS,
            is_active=True
        )

        # Assert citizen has active domicile in RT 01
        self.assertEqual(hunian_kos.penghuni_aktif.count(), 1)
        self.assertEqual(hunian_kos.penghuni_aktif.first().warga, warga)

        # Assert citizen does NOT possess local KK link
        self.assertEqual(KeanggotaanKK.objects.filter(warga=warga).count(), 0)
        
        # Verify NIK is stored encrypted and masked safely
        self.assertEqual(warga.nik_masked, "330201******0004")
        self.assertEqual(warga.get_unmasked_nik(), raw_nik)
