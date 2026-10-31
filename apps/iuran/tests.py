from decimal import Decimal
import datetime
from django.test import TestCase
from apps.wilayah.models import WilayahNode, WilayahLevel
from apps.hunian.models import Hunian
from apps.iuran.models import PosIuran, TagihanIuran, PembayaranIuran, StatusPembayaran, MetodePembayaran

class IuranBillingAndReceiptTestCase(TestCase):
    def setUp(self):
        self.rw = WilayahNode.objects.create(level=WilayahLevel.RW, nama="RW 07")
        self.rt = WilayahNode.objects.create(parent=self.rw, level=WilayahLevel.RT, nama="RT 01")
        self.hunian = Hunian.objects.create(
            rt=self.rt,
            nomor_rumah="No. 14A",
            alamat_lengkap="Jl. Jalaprang No. 14A"
        )
        self.pos = PosIuran.objects.create(
            node=self.rt,
            nama_pos="Iuran Sampah RT 01",
            nominal=Decimal("30000.00")
        )

    def test_invoice_creation_and_full_payment_settlement(self):
        tagihan = TagihanIuran.objects.create(
            hunian=self.hunian,
            pos_iuran=self.pos,
            periode_bulan="2026-10",
            jumlah_tagihan=self.pos.nominal,
            jatuh_tempo=datetime.date(2026, 10, 20)
        )
        self.assertEqual(tagihan.status_pembayaran, StatusPembayaran.BELUM_BAYAR)
        self.assertEqual(tagihan.total_terbayar, 0)

        # Record payment
        bayar = PembayaranIuran.objects.create(
            tagihan=tagihan,
            jumlah_dibayar=Decimal("30000.00"),
            metode_pembayaran=MetodePembayaran.TUNAI,
            nomor_kuitansi="KWT-202610-0099"
        )
        tagihan.status_pembayaran = StatusPembayaran.LUNAS
        tagihan.save()

        self.assertEqual(tagihan.total_terbayar, Decimal("30000.00"))
        self.assertEqual(tagihan.status_pembayaran, StatusPembayaran.LUNAS)
        self.assertEqual(bayar.tagihan, tagihan)
