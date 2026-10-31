import uuid
import secrets
from django.db import models
from apps.kependudukan.models import Warga
from apps.wilayah.models import WilayahNode

class KategoriLayanan(models.TextChoices):
    KTP = 'KTP', 'Permohonan KTP Baru / Rusak / Hilang'
    KK = 'KK', 'Permohonan Kartu Keluarga'
    SKCK = 'SKCK', 'Pengantar SKCK (Catatan Kepolisian)'
    DOMISILI = 'DOMISILI', 'Surat Keterangan Domisili'
    KEMATIAN = 'KEMATIAN', 'Surat Keterangan Kematian'
    LAINNYA = 'LAINNYA', 'Keterangan Umum Lainnya'

class StatusSurat(models.TextChoices):
    PENGAJUAN = 'PENGAJUAN', 'Menunggu Persetujuan RT'
    DISETUJUI_RT = 'DISETUJUI_RT', 'Disetujui RT / Menunggu RW'
    DISETUJUI_RW = 'DISETUJUI_RW', 'Disetujui & Diterbitkan'
    DITOLAK = 'DITOLAK', 'Ditolak'
    DIBATALKAN = 'DIBATALKAN', 'Dibatalkan'

def generate_verification_token() -> str:
    """Generates a high-entropy URL-safe cryptographic token."""
    return secrets.token_urlsafe(32)

class SuratPengantar(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nomor_surat = models.CharField(max_length=100, unique=True, db_index=True)
    pemohon_warga = models.ForeignKey(Warga, on_delete=models.PROTECT, related_name='surat_permohonan')
    rt = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='surat_rt')
    rw = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='surat_rw')
    kategori_layanan = models.CharField(max_length=30, choices=KategoriLayanan.choices)
    keperluan = models.TextField()
    status_surat = models.CharField(
        max_length=25,
        choices=StatusSurat.choices,
        default=StatusSurat.PENGAJUAN,
        db_index=True
    )
    verification_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_verification_token,
        db_index=True
    )
    catatan_penolakan = models.TextField(blank=True, null=True)
    diterbitkan_pada = models.DateTimeField(null=True, blank=True)
    berlaku_sampai = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Surat Pengantar'
        verbose_name_plural = 'Surat Pengantar'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nomor_surat} - {self.pemohon_warga.nama_lengkap} ({self.get_status_surat_display()})"

    def is_valid_and_active(self) -> bool:
        from django.utils import timezone
        if self.status_surat != StatusSurat.DISETUJUI_RW:
            return False
        if self.berlaku_sampai and timezone.now().date() > self.berlaku_sampai:
            return False
        return True


class VerifikasiSuratLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    surat = models.ForeignKey(SuratPengantar, on_delete=models.CASCADE, related_name='verifikasi_logs')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Log Verifikasi Surat'
        verbose_name_plural = 'Log Verifikasi Surat'
        ordering = ['-verified_at']

    def __str__(self):
        return f"Verifikasi {self.surat.nomor_surat} pada {self.verified_at}"
