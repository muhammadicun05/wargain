from django.contrib import admin
from apps.informasi.models import Pengumuman


@admin.register(Pengumuman)
class PengumumanAdmin(admin.ModelAdmin):
    list_display = ('judul', 'wilayah_node', 'lingkup', 'kategori', 'status', 'is_pinned', 'created_at')
    list_filter = ('lingkup', 'kategori', 'status', 'is_pinned', 'wilayah_node')
    search_fields = ('judul', 'isi', 'lokasi_kegiatan')
    date_hierarchy = 'created_at'
