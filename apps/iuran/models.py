import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.wilayah.models import WilayahNode
from apps.hunian.models import Hunian

class PeriodeFrekuensi(models.TextChoices):
    BULANAN = 'BULANAN', 'Bulanan'
    TAHUNAN = 'TAHUNAN', 'Tahunan'
    INSIDENTAL = 'INSIDENTAL', 'Insidental / Sekali Bayar'

class StatusPembayaran(models.TextChoices):
    BELUM_BAYAR = 'BELUM_BAYAR', 'Belum Bayar'
    SEBAGIAN = 'SEBAGIAN', 'Dibayar Sebagian'
    LUNAS = 'LUNAS', 'Lunas'
    KERINGANAN = 'KERINGANAN', 'Keringanan / Bebas Iuran'

class MetodePembayaran(models.TextChoices):
    TUNAI = 'TUNAI', 'Tunai / Cash'
    TRANSFER_BANK = 'TRANSFER_BANK', 'Transfer Bank'
    QRIS = 'QRIS', 'QRIS Digital'

class PosIuran(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='pos_iuran_list')
    nama_pos = models.CharField(max_length=100)
    nominal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    periode_frekuensi = models.CharField(
        max_length=20,
        choices=PeriodeFrekuensi.choices,
        default=PeriodeFrekuensi.BULANAN
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pos Iuran'
        verbose_name_plural = 'Pos Iuran'

    def __str__(self):
        return f"{self.nama_pos} - Rp {self.nominal:,.0f} ({self.node.nama})"


class TagihanIuran(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hunian = models.ForeignKey(Hunian, on_delete=models.CASCADE, related_name='tagihan_list')
    pos_iuran = models.ForeignKey(PosIuran, on_delete=models.PROTECT, related_name='tagihan_list')
    periode_bulan = models.CharField(max_length=7, db_index=True, help_text="Format: YYYY-MM")
    jumlah_tagihan = models.DecimalField(max_digits=12, decimal_places=2)
    status_pembayaran = models.CharField(
        max_length=20,
        choices=StatusPembayaran.choices,
        default=StatusPembayaran.BELUM_BAYAR,
        db_index=True
    )
    jatuh_tempo = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tagihan Iuran'
        verbose_name_plural = 'Tagihan Iuran'
        unique_together = ('hunian', 'pos_iuran', 'periode_bulan')
        indexes = [
            models.Index(fields=['pos_iuran', 'periode_bulan', 'status_pembayaran']),
        ]

    def __str__(self):
        return f"{self.pos_iuran.nama_pos} - {self.hunian.nomor_rumah} ({self.periode_bulan}): {self.get_status_pembayaran_display()}"

    @property
    def total_terbayar(self):
        from django.db.models import Sum
        res = self.pembayaran_list.aggregate(total=Sum('jumlah_dibayar'))['total']
        return res or 0


class PembayaranIuran(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tagihan = models.ForeignKey(TagihanIuran, on_delete=models.PROTECT, related_name='pembayaran_list')
    jumlah_dibayar = models.DecimalField(max_digits=12, decimal_places=2)
    metode_pembayaran = models.CharField(
        max_length=20,
        choices=MetodePembayaran.choices,
        default=MetodePembayaran.TUNAI
    )
    diverifikasi_oleh = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    bukti_transfer = models.ImageField(upload_to='bukti_transfer/', blank=True, null=True)
    nomor_kuitansi = models.CharField(max_length=50, unique=True, db_index=True)
    tanggal_pembayaran = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pembayaran Iuran'
        verbose_name_plural = 'Pembayaran Iuran'
        ordering = ['-tanggal_pembayaran']

    def __str__(self):
        return f"{self.nomor_kuitansi} - Rp {self.jumlah_dibayar:,.0f} ({self.tagihan.hunian.nomor_rumah})"
