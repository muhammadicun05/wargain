from django.contrib import admin
from apps.iuran.models import PosIuran, TagihanIuran, PembayaranIuran

@admin.register(PosIuran)
class PosIuranAdmin(admin.ModelAdmin):
    list_display = ('nama_pos', 'nominal', 'periode_frekuensi', 'node', 'is_active')
    list_filter = ('periode_frekuensi', 'is_active', 'node')
    search_fields = ('nama_pos',)

class PembayaranIuranInline(admin.TabularInline):
    model = PembayaranIuran
    extra = 0

@admin.register(TagihanIuran)
class TagihanIuranAdmin(admin.ModelAdmin):
    list_display = ('hunian', 'pos_iuran', 'periode_bulan', 'jumlah_tagihan', 'status_pembayaran', 'jatuh_tempo')
    list_filter = ('status_pembayaran', 'periode_bulan', 'pos_iuran')
    search_fields = ('hunian__nomor_rumah', 'pos_iuran__nama_pos')
    inlines = [PembayaranIuranInline]

@admin.register(PembayaranIuran)
class PembayaranIuranAdmin(admin.ModelAdmin):
    list_display = ('nomor_kuitansi', 'tagihan', 'jumlah_dibayar', 'metode_pembayaran', 'diverifikasi_oleh', 'tanggal_pembayaran')
    list_filter = ('metode_pembayaran', 'tanggal_pembayaran')
    search_fields = ('nomor_kuitansi', 'tagihan__hunian__nomor_rumah')
