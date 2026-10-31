import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.kependudukan.models import Warga
from apps.wilayah.models import WilayahNode

class JenisMutasi(models.TextChoices):
    PINDAH_MASUK = 'PINDAH_MASUK', 'Pindah Masuk'
    PINDAH_KELUAR = 'PINDAH_KELUAR', 'Pindah Keluar'
    MENINGGAL = 'MENINGGAL', 'Meninggal Dunia'
    LAHIR = 'LAHIR', 'Kelahiran'

class StatusApproval(models.TextChoices):
    PENDING = 'PENDING', 'Menunggu Persetujuan'
    DISETUJUI = 'DISETUJUI', 'Disetujui'
    DITOLAK = 'DITOLAK', 'Ditolak'

class Mutasi(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warga = models.ForeignKey(Warga, on_delete=models.PROTECT, related_name='riwayat_mutasi')
    jenis_mutasi = models.CharField(max_length=20, choices=JenisMutasi.choices)
    tanggal_efektif = models.DateField()
    alasan = models.TextField()
    nomor_surat_keterangan = models.CharField(max_length=100, blank=True, null=True)
    target_node = models.ForeignKey(
        WilayahNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mutasi_masuk_target'
    )
    status_approval = models.CharField(
        max_length=20,
        choices=StatusApproval.choices,
        default=StatusApproval.PENDING,
        db_index=True
    )
    disetujui_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    disetujui_pada = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mutasi Kependudukan'
        verbose_name_plural = 'Mutasi Kependudukan'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_jenis_mutasi_display()} - {self.warga.nama_lengkap} ({self.get_status_approval_display()})"
