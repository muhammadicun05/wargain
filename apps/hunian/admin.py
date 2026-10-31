from django.contrib import admin
from apps.hunian.models import Hunian, Domisili

class DomisiliInline(admin.TabularInline):
    model = Domisili
    extra = 1

@admin.register(Hunian)
class HunianAdmin(admin.ModelAdmin):
    list_display = ('nomor_rumah', 'rt', 'status_kepemilikan', 'created_at')
    list_filter = ('status_kepemilikan', 'rt')
    search_fields = ('nomor_rumah', 'alamat_lengkap')
    inlines = [DomisiliInline]

@admin.register(Domisili)
class DomisiliAdmin(admin.ModelAdmin):
    list_display = ('warga', 'hunian', 'peran_di_hunian', 'is_active', 'tanggal_mulai')
    list_filter = ('peran_di_hunian', 'is_active')
    search_fields = ('warga__nama_lengkap', 'hunian__nomor_rumah')
