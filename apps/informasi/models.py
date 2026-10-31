import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.wilayah.models import WilayahNode, WilayahLevel
from apps.kependudukan.models import Warga


class KategoriPengumuman(models.TextChoices):
    GENTING = 'GENTING', 'Genting / Peringatan'
    AGENDA = 'AGENDA', 'Agenda Kegiatan'
    RESMI = 'RESMI', 'Pengumuman Resmi'
    KABAR_WARGA = 'KABAR_WARGA', 'Warta & Kabar Warga'


class StatusPengumuman(models.TextChoices):
    TERBIT = 'TERBIT', 'Terbit'
    MENUNGGU_KONFIRMASI = 'MENUNGGU_KONFIRMASI', 'Menunggu Konfirmasi'
    DITOLAK = 'DITOLAK', 'Ditolak'
    DIARSIPKAN = 'DIARSIPKAN', 'Diarsipkan'


# Alias kompatibilitas
StatusPengumuman.MENUNGGU_MODERASI = StatusPengumuman.MENUNGGU_KONFIRMASI


class LingkupDistribusi(models.TextChoices):
    RW = 'RW', 'Seluruh RW (Semua RT)'
    RT = 'RT', 'Khusus Lingkungan RT'


class Pengumuman(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wilayah_node = models.ForeignKey(
        WilayahNode,
        on_delete=models.CASCADE,
        related_name='daftar_pengumuman'
    )
    lingkup = models.CharField(
        max_length=10,
        choices=LingkupDistribusi.choices,
        default=LingkupDistribusi.RT,
        db_index=True
    )
    penulis = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tulisan_pengumuman'
    )
    penulis_warga = models.ForeignKey(
        Warga,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pengumuman_warga'
    )
    judul = models.CharField(max_length=200)
    kategori = models.CharField(
        max_length=20,
        choices=KategoriPengumuman.choices,
        default=KategoriPengumuman.RESMI,
        db_index=True
    )
    isi = models.TextField()
    
    # Metadata Agenda (Opsional jika kategori Agenda)
    tanggal_kegiatan = models.DateTimeField(null=True, blank=True)
    lokasi_kegiatan = models.CharField(max_length=150, blank=True, null=True)

    # Pin / Sticky
    is_pinned = models.BooleanField(default=False, db_index=True)

    # Status Konfirmasi
    status = models.CharField(
        max_length=25,
        choices=StatusPengumuman.choices,
        default=StatusPengumuman.TERBIT,
        db_index=True
    )
    catatan_konfirmasi = models.TextField(blank=True, null=True, db_column='catatan_moderasi')

    @property
    def catatan_moderasi(self):
        return self.catatan_konfirmasi

    @catatan_moderasi.setter
    def catatan_moderasi(self, val):
        self.catatan_konfirmasi = val
    disetujui_oleh = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pengumuman_dimoderasi'
    )
    disetujui_pada = models.DateTimeField(null=True, blank=True)

    # Batas Waktu Tampil
    berlaku_sampai = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pengumuman Mading'
        verbose_name_plural = 'Daftar Pengumuman Mading'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"[{self.get_kategori_display()}] {self.judul}"

    def is_expired(self) -> bool:
        if not self.berlaku_sampai:
            return False
        return self.berlaku_sampai < timezone.now().date()
