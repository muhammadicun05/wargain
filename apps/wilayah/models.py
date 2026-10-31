import uuid
from django.db import models
from django.contrib.auth.models import User

class WilayahLevel(models.TextChoices):
    PROVINSI = 'PROVINSI', 'Provinsi'
    KOTA = 'KOTA', 'Kota / Kabupaten'
    KECAMATAN = 'KECAMATAN', 'Kecamatan'
    KELURAHAN = 'KELURAHAN', 'Kelurahan / Desa'
    RW = 'RW', 'Rukun Warga (RW)'
    RT = 'RT', 'Rukun Tetangga (RT)'

class WilayahNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    level = models.CharField(max_length=20, choices=WilayahLevel.choices, db_index=True)
    kode_pos = models.CharField(max_length=5, blank=True, null=True)
    kode_wilayah = models.CharField(max_length=25, blank=True, null=True, db_index=True)
    nama = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Simpul Wilayah'
        verbose_name_plural = 'Simpul Wilayah'
        ordering = ['level', 'nama']

    def __str__(self):
        if self.parent:
            return f"{self.nama} ({self.get_level_display()} - {self.parent.nama})"
        return f"{self.nama} ({self.get_level_display()})"

    def get_full_hierarchy_name(self) -> str:
        parts = [self.nama]
        curr = self.parent
        while curr:
            parts.append(curr.nama)
            curr = curr.parent
        return ", ".join(parts)


class PengurusRole(models.TextChoices):
    KETUA_RW = 'KETUA_RW', 'Ketua RW'
    SEKRETARIS_RW = 'SEKRETARIS_RW', 'Sekretaris RW'
    BENDAHARA_RW = 'BENDAHARA_RW', 'Bendahara RW'
    KETUA_RT = 'KETUA_RT', 'Ketua RT'
    SEKRETARIS_RT = 'SEKRETARIS_RT', 'Sekretaris RT'
    BENDAHARA_RT = 'BENDAHARA_RT', 'Bendahara RT'
    WARGA = 'WARGA', 'Warga Biasa'

class PengurusProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pengurus_profile')
    wilayah_node = models.ForeignKey(WilayahNode, on_delete=models.PROTECT, related_name='pengurus')
    role = models.CharField(max_length=30, choices=PengurusRole.choices, default=PengurusRole.WARGA)
    nomor_wa = models.CharField(max_length=20, blank=True, null=True)
    warga = models.ForeignKey('kependudukan.Warga', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil Pengurus'
        verbose_name_plural = 'Profil Pengurus'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()} ({self.wilayah_node.nama})"
