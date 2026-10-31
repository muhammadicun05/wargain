import uuid
from django.db import models
from apps.wilayah.models import WilayahNode
from apps.kependudukan.crypto import hmac_blind_index, encrypt_pii, decrypt_pii, mask_nik, mask_kk

class IdentitasOrang(models.Model):
    """
    Zero-knowledge identity anchor using HMAC Blind Indexing.
    Contains no raw PII. Enables cross-tenant deduplication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nik_blind_index = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Identitas Orang (Blind Index)'
        verbose_name_plural = 'Identitas Orang (Blind Index)'

    def __str__(self):
        return f"BlindID({self.nik_blind_index[:12]}...)"


class JenisKelamin(models.TextChoices):
    LAKI_LAKI = 'L', 'Laki-Laki'
    PEREMPUAN = 'P', 'Perempuan'

class Agama(models.TextChoices):
    ISLAM = 'ISLAM', 'Islam'
    KRISTEN = 'KRISTEN', 'Kristen Protestan'
    KATOLIK = 'KATOLIK', 'Katolik'
    HINDU = 'HINDU', 'Hindu'
    BUDDHA = 'BUDDHA', 'Buddha'
    KONGHUCU = 'KONGHUCU', 'Konghucu'

class StatusPerkawinan(models.TextChoices):
    BELUM_KAWIN = 'BELUM_KAWIN', 'Belum Kawin'
    KAWIN = 'KAWIN', 'Kawin'
    CERAI_HIDUP = 'CERAI_HIDUP', 'Cerai Hidup'
    CERAI_MATI = 'CERAI_MATI', 'Cerai Mati'

class StatusKeberadaan(models.TextChoices):
    AKTIF = 'AKTIF', 'Aktif'
    MUTASI_KELUAR = 'MUTASI_KELUAR', 'Mutasi Keluar'
    MENINGGAL = 'MENINGGAL', 'Meninggal Dunia'
    DIARSIPKAN = 'DIARSIPKAN', 'Diarsipkan'

class Warga(models.Model):
    """
    Tenant-scoped citizen entity.
    NIK is encrypted using AES-256-GCM.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identitas = models.ForeignKey(IdentitasOrang, on_delete=models.PROTECT, related_name='warga_profiles')
    rw = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='warga_list')
    nik_encrypted = models.BinaryField()
    nik_masked = models.CharField(max_length=16, db_index=True)
    nama_lengkap = models.CharField(max_length=150, db_index=True)
    tempat_lahir = models.CharField(max_length=100)
    tanggal_lahir = models.DateField()
    jenis_kelamin = models.CharField(max_length=1, choices=JenisKelamin.choices)
    agama = models.CharField(max_length=20, choices=Agama.choices)
    status_perkawinan = models.CharField(max_length=20, choices=StatusPerkawinan.choices)
    pekerjaan = models.CharField(max_length=100, blank=True)
    status_keberadaan = models.CharField(
        max_length=20,
        choices=StatusKeberadaan.choices,
        default=StatusKeberadaan.AKTIF,
        db_index=True
    )
    nomor_telepon = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Data Warga'
        verbose_name_plural = 'Data Warga'
        ordering = ['nama_lengkap']
        indexes = [
            models.Index(fields=['rw', 'status_keberadaan']),
        ]

    def __str__(self):
        return f"{self.nama_lengkap} ({self.nik_masked})"

    def set_nik(self, raw_nik: str):
        """Sets encrypted payload and masked representation."""
        self.nik_encrypted = encrypt_pii(raw_nik)
        self.nik_masked = mask_nik(raw_nik)

    def get_unmasked_nik(self) -> str:
        """Decrypts NIK. Call only with corresponding audit trail!"""
        if self.nik_encrypted:
            return decrypt_pii(bytes(self.nik_encrypted))
        return ""


class KartuKeluarga(models.Model):
    """
    Civil family registration record.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rw = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='kartu_keluarga_list')
    nomor_kk_encrypted = models.BinaryField()
    nomor_kk_masked = models.CharField(max_length=16, db_index=True)
    alamat_kk = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kartu Keluarga'
        verbose_name_plural = 'Kartu Keluarga'

    def __str__(self):
        return f"No. KK: {self.nomor_kk_masked}"

    def set_nomor_kk(self, raw_kk: str):
        self.nomor_kk_encrypted = encrypt_pii(raw_kk)
        self.nomor_kk_masked = mask_kk(raw_kk)

    def get_unmasked_nomor_kk(self) -> str:
        if self.nomor_kk_encrypted:
            return decrypt_pii(bytes(self.nomor_kk_encrypted))
        return ""

    @property
    def kepala_keluarga(self):
        membership = self.anggota.filter(status_hubungan=HubunganKeluarga.KEPALA_KELUARGA).first()
        return membership.warga if membership else None


class HubunganKeluarga(models.TextChoices):
    KEPALA_KELUARGA = 'KEPALA_KELUARGA', 'Kepala Keluarga'
    SUAMI = 'SUAMI', 'Suami'
    ISTRI = 'ISTRI', 'Istri'
    ANAK = 'ANAK', 'Anak'
    MENANTU = 'MENANTU', 'Menantu'
    CUCU = 'CUCU', 'Cucu'
    ORANGTUA = 'ORANGTUA', 'Orang Tua'
    MERTUA = 'MERTUA', 'Mertua'
    FAMILI_LAIN = 'FAMILI_LAIN', 'Famili Lain'
    PEMBANTU = 'PEMBANTU', 'Pembantu / ART'
    LAINNYA = 'LAINNYA', 'Lainnya'

class KeanggotaanKK(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kartu_keluarga = models.ForeignKey(KartuKeluarga, on_delete=models.CASCADE, related_name='anggota')
    warga = models.ForeignKey(Warga, on_delete=models.PROTECT, related_name='keanggotaan_kk')
    status_hubungan = models.CharField(max_length=30, choices=HubunganKeluarga.choices)
    tanggal_bergabung = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Keanggotaan Kartu Keluarga'
        verbose_name_plural = 'Keanggotaan Kartu Keluarga'
        unique_together = ('kartu_keluarga', 'warga')

    def __str__(self):
        return f"{self.warga.nama_lengkap} - {self.get_status_hubungan_display()}"
