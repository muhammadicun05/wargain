import uuid
from django.db import models
from apps.wilayah.models import WilayahNode
from apps.kependudukan.models import Warga

class StatusKepemilikan(models.TextChoices):
    MILIK_SENDIRI = 'MILIK_SENDIRI', 'Milik Sendiri'
    SEWA_KONTRAK = 'SEWA_KONTRAK', 'Sewa / Kontrak'
    KOS = 'KOS', 'Kamar Kos'
    DINAS = 'DINAS', 'Rumah Dinas'
    MENUMPANG = 'MENUMPANG', 'Menumpang / Keluarga'

class PeranDiHunian(models.TextChoices):
    KEPALA_RUMAH_TANGGA = 'KEPALA_RUMAH_TANGGA', 'Kepala Rumah Tangga'
    ANGGOTA = 'ANGGOTA', 'Anggota Keluarga'
    PENYEWA_UTAMA = 'PENYEWA_UTAMA', 'Penyewa Utama'
    PENGHUNI_KOS = 'PENGHUNI_KOS', 'Penghuni Kos'

class Hunian(models.Model):
    """
    Physical dwelling unit anchored to a specific RT node.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rt = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='daftar_hunian')
    nomor_rumah = models.CharField(max_length=50, db_index=True)
    alamat_lengkap = models.TextField()
    status_kepemilikan = models.CharField(
        max_length=30,
        choices=StatusKepemilikan.choices,
        default=StatusKepemilikan.MILIK_SENDIRI
    )
    koordinat = models.JSONField(null=True, blank=True, help_text='{"lat": -6.90, "lng": 107.61}')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hunian / Rumah'
        verbose_name_plural = 'Hunian / Rumah'
        ordering = ['nomor_rumah']

    def __str__(self):
        return f"{self.nomor_rumah} ({self.rt.nama})"

    @property
    def penghuni_aktif(self):
        return self.penghuni.filter(is_active=True).select_related('warga')

    @property
    def kepala_hunian(self):
        dom = self.penghuni.filter(
            is_active=True,
            peran_di_hunian__in=[PeranDiHunian.KEPALA_RUMAH_TANGGA, PeranDiHunian.PENYEWA_UTAMA]
        ).first()
        return dom.warga if dom else None


class Domisili(models.Model):
    """
    Temporal occupancy mapping an individual to a physical dwelling.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hunian = models.ForeignKey(Hunian, on_delete=models.CASCADE, related_name='penghuni')
    warga = models.ForeignKey(Warga, on_delete=models.PROTECT, related_name='riwayat_domisili')
    peran_di_hunian = models.CharField(
        max_length=30,
        choices=PeranDiHunian.choices,
        default=PeranDiHunian.ANGGOTA
    )
    tanggal_mulai = models.DateField(auto_now_add=True)
    tanggal_selesai = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Domisili Penghuni'
        verbose_name_plural = 'Domisili Penghuni'
        indexes = [
            models.Index(fields=['hunian', 'is_active']),
            models.Index(fields=['warga', 'is_active']),
        ]

    def __str__(self):
        return f"{self.warga.nama_lengkap} di {self.hunian.nomor_rumah} ({self.get_peran_di_hunian_display()})"
