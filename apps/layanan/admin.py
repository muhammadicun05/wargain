from django.contrib import admin
from apps.layanan.models import SuratPengantar, VerifikasiSuratLog

class VerifikasiSuratLogInline(admin.TabularInline):
    model = VerifikasiSuratLog
    extra = 0
    readonly_fields = ('ip_address', 'user_agent', 'verified_at')

@admin.register(SuratPengantar)
class SuratPengantarAdmin(admin.ModelAdmin):
    list_display = ('nomor_surat', 'pemohon_warga', 'kategori_layanan', 'status_surat', 'diterbitkan_pada')
    list_filter = ('kategori_layanan', 'status_surat', 'rt', 'rw')
    search_fields = ('nomor_surat', 'pemohon_warga__nama_lengkap', 'keperluan', 'verification_token')
    readonly_fields = ('verification_token', 'created_at')
    inlines = [VerifikasiSuratLogInline]

@admin.register(VerifikasiSuratLog)
class VerifikasiSuratLogAdmin(admin.ModelAdmin):
    list_display = ('surat', 'ip_address', 'verified_at')
    readonly_fields = ('surat', 'ip_address', 'user_agent', 'verified_at')
