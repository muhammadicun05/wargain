from django.contrib import admin
from apps.audit.models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'entity_name', 'entity_id', 'ip_address')
    list_filter = ('action', 'entity_name', 'timestamp')
    search_fields = ('entity_name', 'entity_id', 'actor__username', 'ip_address')
    readonly_fields = ('id', 'actor', 'action', 'entity_name', 'entity_id', 'old_values', 'new_values', 'ip_address', 'user_agent', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
