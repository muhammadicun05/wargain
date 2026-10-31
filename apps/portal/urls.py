from django.urls import path
from apps.portal import views

app_name = 'portal'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_alt'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('daftar/', views.register_view, name='register'),
    path('warga/konfirmasi/<uuid:profile_id>/', views.konfirmasi_warga_baru_view, name='konfirmasi_warga_baru'),

    # PWA (Progressive Web App) Routes
    path('manifest.webmanifest', views.manifest_view, name='manifest'),
    path('manifest.json', views.manifest_view, name='manifest_json'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('offline/', views.offline_view, name='offline'),

    # Kependudukan & Tri-axial Registry
    path('warga/', views.warga_list_view, name='warga_list'),
    path('warga/tambah/', views.warga_create_view, name='warga_create'),
    path('warga/<uuid:warga_id>/', views.warga_detail_view, name='warga_detail'),
    path('warga/<uuid:warga_id>/unmask/', views.api_unmask_nik, name='warga_unmask'),

    # Hunian & Domicile
    path('hunian/', views.hunian_list_view, name='hunian_list'),

    # Layanan Surat & Verification
    path('surat/', views.surat_list_view, name='surat_list'),
    path('surat/buat/', views.surat_create_view, name='surat_create'),
    path('surat/<uuid:surat_id>/approve/', views.surat_approve_view, name='surat_approve'),
    path('surat/<uuid:surat_id>/cetak/', views.surat_print_view, name='surat_print'),
    path('verifikasi/<str:token>/', views.public_verifikasi_surat_view, name='verifikasi_surat'),

    # Iuran, Kas, & Digital Kuitansi
    path('iuran/', views.iuran_desk_view, name='iuran_desk'),
    path('iuran-saya/', views.iuran_saya_view, name='iuran_saya'),
    path('iuran/bayar/<uuid:tagihan_id>/', views.iuran_bayar_view, name='iuran_bayar'),
    path('kuitansi/<str:nomor_kuitansi>/', views.kuitansi_view, name='kuitansi'),

    # Mading / Pusat Informasi Warga
    path('mading/', views.mading_list_view, name='mading_list'),
    path('mading/buat/', views.mading_create_view, name='mading_create'),
    path('mading/<uuid:pengumuman_id>/', views.mading_detail_view, name='mading_detail'),
    path('mading/<uuid:pengumuman_id>/konfirmasi/', views.mading_moderasi_view, name='mading_konfirmasi'),
    path('mading/<uuid:pengumuman_id>/moderasi/', views.mading_moderasi_view, name='mading_moderasi'),
]
