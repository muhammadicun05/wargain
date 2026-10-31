import uuid
from django.db import models
from django.contrib.auth.models import User

class AuditAction(models.TextChoices):
    READ_PII = 'READ_PII', 'Pembacaan Data Pribadi Sensitif (PII)'
    INSERT = 'INSERT', 'Penambahan Data'
    UPDATE = 'UPDATE', 'Perubahan Data'
    DELETE = 'DELETE', 'Penghapusan / Pengarsipan'
    AUTH_LOGIN = 'AUTH_LOGIN', 'Login Pengguna'
    AUTH_LOGOUT = 'AUTH_LOGOUT', 'Logout Pengguna'
    EXPORT = 'EXPORT', 'Ekspor Data Wilayah'

class AuditLog(models.Model):
    """
    Immutable, append-only log capturing administrative actions and PII reads
    as mandated by Indonesian Personal Data Protection Act (UU No. 27/2022).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_entries')
    action = models.CharField(max_length=30, choices=AuditAction.choices)
    entity_name = models.CharField(max_length=60, db_index=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Audit Log UU PDP'
        verbose_name_plural = 'Audit Log UU PDP'
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "Anonymous/System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {actor_name} -> {self.get_action_display()} on {self.entity_name} ({self.entity_id})"
