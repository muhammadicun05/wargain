from django.contrib import admin
from apps.mutasi.models import Mutasi

@admin.register(Mutasi)
class MutasiAdmin(admin.ModelAdmin):
    list_display = ('warga', 'jenis_mutasi', 'tanggal_efektif', 'status_approval', 'disetujui_oleh', 'disetujui_pada')
    list_filter = ('jenis_mutasi', 'status_approval')
    search_fields = ('warga__nama_lengkap', 'alasan', 'nomor_surat_keterangan')
