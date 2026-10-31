from django.contrib import admin
from apps.kependudukan.models import IdentitasOrang, Warga, KartuKeluarga, KeanggotaanKK

@admin.register(IdentitasOrang)
class IdentitasOrangAdmin(admin.ModelAdmin):
    list_display = ('id', 'nik_blind_index', 'created_at')
    search_fields = ('nik_blind_index',)
    readonly_fields = ('id', 'nik_blind_index', 'created_at')

@admin.register(Warga)
class WargaAdmin(admin.ModelAdmin):
    list_display = ('nama_lengkap', 'nik_masked', 'jenis_kelamin', 'status_keberadaan', 'rw', 'created_at')
    list_filter = ('status_keberadaan', 'jenis_kelamin', 'agama', 'rw')
    search_fields = ('nama_lengkap', 'nik_masked')
    readonly_fields = ('nik_masked', 'created_at', 'updated_at')

class KeanggotaanKKInline(admin.TabularInline):
    model = KeanggotaanKK
    extra = 1

@admin.register(KartuKeluarga)
class KartuKeluargaAdmin(admin.ModelAdmin):
    list_display = ('nomor_kk_masked', 'rw', 'alamat_kk', 'created_at')
    search_fields = ('nomor_kk_masked', 'alamat_kk')
    inlines = [KeanggotaanKKInline]

@admin.register(KeanggotaanKK)
class KeanggotaanKKAdmin(admin.ModelAdmin):
    list_display = ('warga', 'kartu_keluarga', 'status_hubungan', 'tanggal_bergabung')
    list_filter = ('status_hubungan',)
    search_fields = ('warga__nama_lengkap', 'kartu_keluarga__nomor_kk_masked')
