from django.contrib import admin
from apps.wilayah.models import WilayahNode, PengurusProfile

@admin.register(WilayahNode)
class WilayahNodeAdmin(admin.ModelAdmin):
    list_display = ('nama', 'level', 'parent', 'kode_pos', 'kode_wilayah', 'created_at')
    list_filter = ('level',)
    search_fields = ('nama', 'kode_pos', 'kode_wilayah')

@admin.register(PengurusProfile)
class PengurusProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'wilayah_node', 'role', 'nomor_wa')
    list_filter = ('role', 'wilayah_node__level')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'nomor_wa')
