import datetime
import json
import os
from decimal import Decimal
import urllib.parse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.urls import reverse

from apps.wilayah.models import WilayahNode, WilayahLevel, PengurusProfile, PengurusRole
from apps.kependudukan.models import IdentitasOrang, Warga, KartuKeluarga, KeanggotaanKK, StatusKeberadaan, JenisKelamin, Agama, StatusPerkawinan, HubunganKeluarga
from apps.kependudukan.crypto import hmac_blind_index, encrypt_pii, decrypt_pii, mask_nik, mask_kk
from apps.hunian.models import Hunian, Domisili, StatusKepemilikan, PeranDiHunian
from apps.layanan.models import SuratPengantar, VerifikasiSuratLog, KategoriLayanan, StatusSurat
from apps.iuran.models import PosIuran, TagihanIuran, PembayaranIuran, StatusPembayaran, MetodePembayaran
from apps.mutasi.models import Mutasi, StatusApproval
from apps.informasi.models import Pengumuman, KategoriPengumuman, StatusPengumuman, LingkupDistribusi
from apps.audit.models import AuditLog, AuditAction
from apps.portal.utils import generate_qr_base64, get_client_ip


def get_user_scope(user):
    """
    Determines administrative scope (rw, rt, role, warga_entity) for the user.
    """
    if user.is_superuser:
        rw = WilayahNode.objects.filter(level=WilayahLevel.RW).first()
        return rw, None, 'ADMIN', None

    profile = getattr(user, 'pengurus_profile', None)
    if not profile:
        rw = WilayahNode.objects.filter(level=WilayahLevel.RW).first()
        return rw, None, PengurusRole.WARGA, None

    node = profile.wilayah_node
    role = profile.role
    warga = profile.warga

    # Auto-resolve warga entity if linked by name/username
    if not warga:
        warga = Warga.objects.filter(Q(nama_lengkap__icontains=user.first_name) | Q(nomor_telepon=profile.nomor_wa)).first()

    if node.level == WilayahLevel.RW:
        return node, None, role, warga
    elif node.level == WilayahLevel.RT:
        return node.parent, node, role, warga
    return None, None, role, warga


def is_officer(user) -> bool:
    """Returns True if user is superuser or holds an RT/RW officer position."""
    if user.is_superuser:
        return True
    profile = getattr(user, 'pengurus_profile', None)
    return bool(profile and profile.role != PengurusRole.WARGA)


def is_treasurer(user) -> bool:
    """Returns True only if user is authorized as cashier/treasurer (Bendahara or Superuser)."""
    if user.is_superuser:
        return True
    profile = getattr(user, 'pengurus_profile', None)
    return bool(profile and profile.role in [
        PengurusRole.BENDAHARA_RT, PengurusRole.BENDAHARA_RW
    ])


def is_rt_signer(user, rt_node=None) -> bool:
    """Returns True if user is Ketua or Sekretaris of the specified RT (or Superuser)."""
    if user.is_superuser:
        return True
    profile = getattr(user, 'pengurus_profile', None)
    if not profile or profile.role not in [PengurusRole.KETUA_RT, PengurusRole.SEKRETARIS_RT]:
        return False
    if rt_node and profile.wilayah_node != rt_node:
        return False
    return True


def is_rw_signer(user, rw_node=None) -> bool:
    """Returns True if user is Ketua or Sekretaris of the RW (or Superuser)."""
    if user.is_superuser:
        return True
    profile = getattr(user, 'pengurus_profile', None)
    if not profile or profile.role not in [PengurusRole.KETUA_RW, PengurusRole.SEKRETARIS_RW]:
        return False
    if rw_node and profile.wilayah_node != rw_node:
        return False
    return True


def is_pii_unmasker(user) -> bool:
    """Only Executive RT/RW Leaders (Chair/Secretary) or Superuser can decrypt raw NIK."""
    if user.is_superuser:
        return True
    profile = getattr(user, 'pengurus_profile', None)
    return bool(profile and profile.role in [
        PengurusRole.KETUA_RT, PengurusRole.SEKRETARIS_RT,
        PengurusRole.KETUA_RW, PengurusRole.SEKRETARIS_RW
    ])


def login_view(request):
    if request.user.is_authenticated:
        return redirect('portal:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            AuditLog.objects.create(
                actor=user,
                action=AuditAction.AUTH_LOGIN,
                entity_name='User',
                entity_id=str(user.id),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            messages.success(request, f"Selamat datang kembali, {user.first_name or user.username}!")
            return redirect('portal:dashboard')
        else:
            existing_user = User.objects.filter(username=username).first()
            if existing_user and not existing_user.is_active and existing_user.check_password(password):
                messages.warning(
                    request,
                    "Akun Anda telah terdaftar namun masih Menunggu Konfirmasi dari Ketua RT setempat demi verifikasi keamanan lingkungan."
                )
            else:
                messages.error(request, "Username atau password salah. Silakan coba lagi.")

    return render(request, 'portal/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.AUTH_LOGOUT,
            entity_name='User',
            entity_id=str(request.user.id),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    logout(request)
    messages.info(request, "Anda telah keluar dari sistem.")
    return redirect('portal:login')


@login_required
def dashboard_view(request):
    rw, rt, role, warga = get_user_scope(request.user)

    # ==========================================
    # 1. CITIZEN PORTAL DASHBOARD (Role: WARGA)
    # ==========================================
    if role == PengurusRole.WARGA:
        domisili = warga.riwayat_domisili.filter(is_active=True).first() if warga else None
        hunian = domisili.hunian if domisili else None
        keanggotaan_kk = warga.keanggotaan_kk.select_related('kartu_keluarga').first() if warga else None
        kk = keanggotaan_kk.kartu_keluarga if keanggotaan_kk else None
        family_members = kk.anggota.select_related('warga').all() if kk else []

        curr_month = timezone.now().strftime('%Y-%m')
        tagihan_list = hunian.tagihan_list.filter(periode_bulan=curr_month).select_related('pos_iuran') if hunian else []
        all_lunas = all(t.status_pembayaran == StatusPembayaran.LUNAS for t in tagihan_list) if tagihan_list else True

        surat_saya = warga.surat_permohonan.all().select_related('rt', 'rw') if warga else []

        # Mading Lingkungan untuk Warga
        today = timezone.now().date()
        mading_scope = Q(lingkup=LingkupDistribusi.RW, wilayah_node=rw)
        if rt:
            mading_scope |= Q(lingkup=LingkupDistribusi.RT, wilayah_node=rt)
        
        active_mading = Pengumuman.objects.filter(
            mading_scope,
            status=StatusPengumuman.TERBIT
        ).filter(
            Q(berlaku_sampai__isnull=True) | Q(berlaku_sampai__gte=today)
        )
        pengumuman_genting = active_mading.filter(kategori=KategoriPengumuman.GENTING).first()
        mading_terbaru = active_mading[:3]

        context = {
            'role': role,
            'warga': warga,
            'domisili': domisili,
            'hunian': hunian,
            'kk': kk,
            'family_members': family_members,
            'tagihan_list': tagihan_list,
            'all_lunas': all_lunas,
            'surat_saya': surat_saya,
            'curr_month_label': timezone.now().strftime('%B %Y'),
            'pengumuman_genting': pengumuman_genting,
            'mading_terbaru': mading_terbaru,
        }
        return render(request, 'portal/warga_dashboard.html', context)

    # ==========================================
    # 2. OFFICER COMMAND CENTER (RT, RW, Admin)
    # ==========================================
    warga_qs = Warga.objects.filter(status_keberadaan=StatusKeberadaan.AKTIF)
    hunian_qs = Hunian.objects.all()
    surat_qs = SuratPengantar.objects.all()
    mutasi_qs = Mutasi.objects.all()
    tagihan_qs = TagihanIuran.objects.all()

    if rt:
        # Scoped strictly to RT
        warga_qs = warga_qs.filter(riwayat_domisili__hunian__rt=rt, riwayat_domisili__is_active=True)
        hunian_qs = hunian_qs.filter(rt=rt)
        surat_qs = surat_qs.filter(rt=rt)
        tagihan_qs = tagihan_qs.filter(hunian__rt=rt)
    elif rw:
        # Scoped to entire RW
        warga_qs = warga_qs.filter(rw=rw)
        hunian_qs = hunian_qs.filter(rt__parent=rw)
        surat_qs = surat_qs.filter(rw=rw)
        tagihan_qs = tagihan_qs.filter(hunian__rt__parent=rw)

    curr_month = timezone.now().strftime('%Y-%m')
    curr_month_tagihan = tagihan_qs.filter(periode_bulan=curr_month)

    total_target_iuran = curr_month_tagihan.aggregate(t=Sum('jumlah_tagihan'))['t'] or Decimal('0.00')
    total_lunas_iuran = curr_month_tagihan.filter(status_pembayaran=StatusPembayaran.LUNAS).aggregate(t=Sum('jumlah_tagihan'))['t'] or Decimal('0.00')
    iuran_persen = int((total_lunas_iuran / total_target_iuran) * 100) if total_target_iuran > 0 else 0

    pending_surat = surat_qs.filter(status_surat__in=[StatusSurat.PENGAJUAN, StatusSurat.DISETUJUI_RT])
    pending_mutasi = mutasi_qs.filter(status_approval=StatusApproval.PENDING)

    # Mading Lingkungan untuk Pengurus
    today = timezone.now().date()
    mading_scope = Q(lingkup=LingkupDistribusi.RW, wilayah_node=rw)
    if rt:
        mading_scope |= Q(lingkup=LingkupDistribusi.RT, wilayah_node=rt)
    
    active_mading = Pengumuman.objects.filter(
        mading_scope,
        status=StatusPengumuman.TERBIT
    ).filter(
        Q(berlaku_sampai__isnull=True) | Q(berlaku_sampai__gte=today)
    )
    pengumuman_genting = active_mading.filter(kategori=KategoriPengumuman.GENTING).first()
    mading_terbaru = active_mading[:3]

    pending_mading_count = 0
    if rt:
        pending_mading_count = Pengumuman.objects.filter(wilayah_node=rt, status=StatusPengumuman.MENUNGGU_KONFIRMASI).count()
    elif rw:
        pending_mading_count = Pengumuman.objects.filter(wilayah_node__in=[rw] + list(rw.children.all()), status=StatusPengumuman.MENUNGGU_KONFIRMASI).count()

    # Pending Warga Registration Confirmation (Opsi 1)
    pending_warga_pendaftaran_qs = PengurusProfile.objects.filter(
        role=PengurusRole.WARGA,
        user__is_active=False
    ).select_related('user', 'warga', 'wilayah_node')
    if rt:
        pending_warga_pendaftaran_qs = pending_warga_pendaftaran_qs.filter(wilayah_node=rt)
    elif rw:
        pending_warga_pendaftaran_qs = pending_warga_pendaftaran_qs.filter(
            Q(wilayah_node=rw) | Q(wilayah_node__parent=rw)
        )
    pending_warga_count = pending_warga_pendaftaran_qs.count()
    pending_warga_list = pending_warga_pendaftaran_qs[:10]

    context = {
        'rw': rw,
        'rt': rt,
        'role': role,
        'total_warga': warga_qs.distinct().count(),
        'total_warga_l': warga_qs.filter(jenis_kelamin=JenisKelamin.LAKI_LAKI).distinct().count(),
        'total_warga_p': warga_qs.filter(jenis_kelamin=JenisKelamin.PEREMPUAN).distinct().count(),
        'total_hunian': hunian_qs.count(),
        'pending_surat_count': pending_surat.count(),
        'pending_mutasi_count': pending_mutasi.count(),
        'pending_mading_count': pending_mading_count,
        'pending_warga_count': pending_warga_count,
        'pending_warga_list': pending_warga_list,
        'total_target_iuran': total_target_iuran,
        'total_lunas_iuran': total_lunas_iuran,
        'iuran_persen': iuran_persen,
        'recent_surat': pending_surat[:5],
        'curr_month_label': timezone.now().strftime('%B %Y'),
        'pengumuman_genting': pengumuman_genting,
        'mading_terbaru': mading_terbaru,
    }
    return render(request, 'portal/dashboard.html', context)


@login_required
def warga_list_view(request):
    """Buku Register Warga — Khusus Pengurus RT/RW."""
    if not is_officer(request.user):
        messages.error(request, "Akses terbatas: Buku register kependudukan hanya dapat diakses oleh Pengurus RT/RW.")
        return redirect('portal:dashboard')

    rw, rt, role, _ = get_user_scope(request.user)
    warga_qs = Warga.objects.all().select_related('identitas')

    if rt:
        warga_qs = warga_qs.filter(riwayat_domisili__hunian__rt=rt, riwayat_domisili__is_active=True)
    elif rw:
        warga_qs = warga_qs.filter(rw=rw)

    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', StatusKeberadaan.AKTIF)
    rt_filter = request.GET.get('rt', '')

    if status_filter:
        warga_qs = warga_qs.filter(status_keberadaan=status_filter)

    if search:
        b_idx = hmac_blind_index(search)
        warga_qs = warga_qs.filter(
            Q(nama_lengkap__icontains=search) |
            Q(nik_masked__icontains=search) |
            Q(identitas__nik_blind_index=b_idx)
        )

    if rt_filter:
        warga_qs = warga_qs.filter(riwayat_domisili__hunian__rt_id=rt_filter, riwayat_domisili__is_active=True)

    rt_list = WilayahNode.objects.filter(parent=rw, level=WilayahLevel.RT) if rw else []

    context = {
        'warga_list': warga_qs.distinct(),
        'search': search,
        'status_filter': status_filter,
        'rt_filter': rt_filter,
        'rt_list': rt_list,
        'status_choices': StatusKeberadaan.choices,
    }
    return render(request, 'portal/warga_list.html', context)


@login_required
def warga_create_view(request):
    """Pendaftaran Warga Baru — Khusus Pengurus RT/RW."""
    if not is_officer(request.user):
        messages.error(request, "Akses terbatas: Pendaftaran warga baru hanya dapat diproses oleh Pengurus RT/RW.")
        return redirect('portal:dashboard')

    rw, rt, role, _ = get_user_scope(request.user)
    if not rw:
        messages.error(request, "Wilayah RW belum terdaftar.")
        return redirect('portal:warga_list')

    if rt:
        rt_list = [rt]
        hunian_list = Hunian.objects.filter(rt=rt)
    else:
        rt_list = WilayahNode.objects.filter(parent=rw, level=WilayahLevel.RT)
        hunian_list = Hunian.objects.filter(rt__in=rt_list)

    if request.method == 'POST':
        nik = request.POST.get('nik', '').strip()
        nama_lengkap = request.POST.get('nama_lengkap', '').strip()
        tempat_lahir = request.POST.get('tempat_lahir', '').strip()
        tanggal_lahir = request.POST.get('tanggal_lahir')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        agama = request.POST.get('agama')
        status_perkawinan = request.POST.get('status_perkawinan')
        pekerjaan = request.POST.get('pekerjaan', '').strip()
        nomor_telepon = request.POST.get('nomor_telepon', '').strip()
        hunian_id = request.POST.get('hunian_id')
        peran_di_hunian = request.POST.get('peran_di_hunian', PeranDiHunian.ANGGOTA)

        if len(nik) != 16 or not nik.isdigit():
            messages.error(request, "NIK harus berupa 16 digit angka sesuai KTP.")
            return render(request, 'portal/warga_form.html', {
                'rt_list': rt_list, 'hunian_list': hunian_list,
                'jk_choices': JenisKelamin.choices, 'agama_choices': Agama.choices,
                'status_kawin_choices': StatusPerkawinan.choices, 'peran_choices': PeranDiHunian.choices
            })

        blind_idx = hmac_blind_index(nik)
        identitas, _ = IdentitasOrang.objects.get_or_create(nik_blind_index=blind_idx)

        warga, created = Warga.objects.get_or_create(
            identitas=identitas,
            rw=rw,
            defaults={
                'nama_lengkap': nama_lengkap,
                'tempat_lahir': tempat_lahir,
                'tanggal_lahir': tanggal_lahir,
                'jenis_kelamin': jenis_kelamin,
                'agama': agama,
                'status_perkawinan': status_perkawinan,
                'pekerjaan': pekerjaan,
                'nomor_telepon': nomor_telepon,
                'status_keberadaan': StatusKeberadaan.AKTIF
            }
        )
        warga.set_nik(nik)
        warga.save()

        if hunian_id:
            hunian = get_object_or_404(Hunian, id=hunian_id)
            Domisili.objects.create(
                hunian=hunian,
                warga=warga,
                peran_di_hunian=peran_di_hunian,
                is_active=True
            )

        AuditLog.objects.create(
            actor=request.user,
            action=AuditAction.INSERT,
            entity_name='Warga',
            entity_id=str(warga.id),
            new_values={'nama_lengkap': nama_lengkap, 'nik_masked': warga.nik_masked},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        messages.success(request, f"Data warga {nama_lengkap} ({warga.nik_masked}) berhasil didaftarkan!")
        return redirect('portal:warga_list')

    return render(request, 'portal/warga_form.html', {
        'rt_list': rt_list,
        'hunian_list': hunian_list,
        'jk_choices': JenisKelamin.choices,
        'agama_choices': Agama.choices,
        'status_kawin_choices': StatusPerkawinan.choices,
        'peran_choices': PeranDiHunian.choices
    })


@login_required
def warga_detail_view(request, warga_id):
    """Rincian Profil Warga — Warga hanya bisa melihat profil sendiri, RT hanya melihat warganya."""
    rw, rt, role, my_warga = get_user_scope(request.user)

    if role == PengurusRole.WARGA:
        if not my_warga or my_warga.id != warga_id:
            messages.error(request, "Akses ditolak: Anda hanya dapat melihat profil kependudukan Anda sendiri.")
            return redirect('portal:dashboard')

    warga = get_object_or_404(Warga, id=warga_id)
    domisili_aktif = warga.riwayat_domisili.filter(is_active=True).first()

    # Isolasi Wilayah: Pengurus RT tidak dapat mengintip data warga RT lain
    if rt and domisili_aktif and domisili_aktif.hunian.rt != rt and not request.user.is_superuser:
        messages.error(request, f"Akses ditolak: Data warga ini berada di luar yurisdiksi {rt.nama}.")
        return redirect('portal:warga_list')

    keanggotaan_kk = warga.keanggotaan_kk.select_related('kartu_keluarga').first()

    context = {
        'warga': warga,
        'domisili_aktif': domisili_aktif,
        'keanggotaan_kk': keanggotaan_kk,
        'riwayat_surat': warga.surat_permohonan.all()[:5],
        'is_officer': is_officer(request.user),
        'can_unmask': is_pii_unmasker(request.user),
    }
    return render(request, 'portal/warga_detail.html', context)


@login_required
def api_unmask_nik(request, warga_id):
    """Pembukaan NIK lengkap terenkripsi — Khusus Pimpinan RT/RW dengan Audit Trail."""
    if not is_pii_unmasker(request.user):
        return JsonResponse({'error': 'Akses ditolak: Hanya Pimpinan RT/RW (Ketua/Sekretaris) atau Admin yang berwenang membuka NIK mentah.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    warga = get_object_or_404(Warga, id=warga_id)
    rw, rt, _, _ = get_user_scope(request.user)
    dom = warga.riwayat_domisili.filter(is_active=True).first()

    if rt and dom and dom.hunian.rt != rt and not request.user.is_superuser:
        return JsonResponse({'error': f'Akses ditolak: Warga berada di luar yurisdiksi {rt.nama}.'}, status=403)

    alasan = request.POST.get('alasan', '').strip()

    if not alasan:
        return JsonResponse({'error': 'Alasan pembukaan data pribadi wajib diisi.'}, status=400)

    raw_nik = warga.get_unmasked_nik()

    AuditLog.objects.create(
        actor=request.user,
        action=AuditAction.READ_PII,
        entity_name='Warga',
        entity_id=str(warga.id),
        new_values={'alasan': alasan, 'field': 'nik'},
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    return JsonResponse({
        'status': 'success',
        'raw_nik': raw_nik,
        'message': 'Data NIK berhasil didekripsi. Akses telah dicatat pada Audit Log UU PDP.'
    })


@login_required
def hunian_list_view(request):
    """Pemetaan Hunian & Kos — Khusus Pengurus RT/RW."""
    if not is_officer(request.user):
        messages.error(request, "Akses terbatas: Pemetaan hunian wilayah hanya dapat diakses oleh Pengurus RT/RW.")
        return redirect('portal:dashboard')

    rw, rt, _, _ = get_user_scope(request.user)
    hunian_qs = Hunian.objects.all().prefetch_related('penghuni__warga', 'rt')

    if rt:
        hunian_qs = hunian_qs.filter(rt=rt)
    elif rw:
        hunian_qs = hunian_qs.filter(rt__parent=rw)

    context = {
        'hunian_list': hunian_qs,
        'rt': rt,
        'rw': rw
    }
    return render(request, 'portal/hunian_list.html', context)


@login_required
def surat_list_view(request):
    """Daftar Surat Pengantar (Warga hanya melihat surat sendiri; Pengurus melihat yurisdiksinya)."""
    rw, rt, role, warga = get_user_scope(request.user)
    surat_qs = SuratPengantar.objects.all().select_related('pemohon_warga', 'rt', 'rw')

    if role == PengurusRole.WARGA:
        if warga:
            surat_qs = surat_qs.filter(pemohon_warga=warga)
        else:
            surat_qs = surat_qs.none()
    elif rt:
        surat_qs = surat_qs.filter(rt=rt)
    elif rw:
        surat_qs = surat_qs.filter(rw=rw)

    status_filter = request.GET.get('status', '')
    if status_filter:
        surat_qs = surat_qs.filter(status_surat=status_filter)

    context = {
        'surat_list': surat_qs,
        'status_filter': status_filter,
        'status_choices': StatusSurat.choices,
        'role': role,
        'rt': rt,
        'rw': rw,
        'is_officer': is_officer(request.user),
        'is_rt_signer': is_rt_signer(request.user, rt),
        'is_rw_signer': is_rw_signer(request.user, rw),
    }
    return render(request, 'portal/surat_list.html', context)


@login_required
def surat_create_view(request):
    """Pengajuan Surat Pengantar (Warga mengajukan untuk diri/keluarga; Pengurus untuk warga wilayah)."""
    rw, rt, role, warga = get_user_scope(request.user)

    if role == PengurusRole.WARGA:
        if warga:
            family_ids = [warga.id]
            keanggotaan = warga.keanggotaan_kk.first()
            if keanggotaan:
                family_ids = list(keanggotaan.kartu_keluarga.anggota.values_list('warga_id', flat=True))
            warga_list = Warga.objects.filter(id__in=family_ids)
        else:
            warga_list = Warga.objects.none()
    else:
        warga_list = Warga.objects.filter(status_keberadaan=StatusKeberadaan.AKTIF)
        if rt:
            warga_list = warga_list.filter(riwayat_domisili__hunian__rt=rt, riwayat_domisili__is_active=True)
        elif rw:
            warga_list = warga_list.filter(rw=rw)

    if request.method == 'POST':
        pemohon_id = request.POST.get('pemohon_warga_id')
        kategori = request.POST.get('kategori_layanan')
        keperluan = request.POST.get('keperluan', '').strip()

        pemohon = get_object_or_404(Warga, id=pemohon_id)

        # Ensure citizen can only apply for self/family
        if role == PengurusRole.WARGA and pemohon not in warga_list:
            messages.error(request, "Anda hanya dapat mengajukan permohonan surat untuk diri Anda sendiri atau keluarga.")
            return redirect('portal:surat_create')

        dom = pemohon.riwayat_domisili.filter(is_active=True).first()
        rt_node = dom.hunian.rt if dom else WilayahNode.objects.filter(parent=rw, level=WilayahLevel.RT).first()
        rw_node = rt_node.parent if rt_node else rw

        count_surat = SuratPengantar.objects.count() + 1
        romawi_bulan = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"][timezone.now().month - 1]
        nomor_surat = f"{count_surat:03d}/{rt_node.nama.replace(' ', '')}-{rw_node.nama.replace(' ', '')}/{romawi_bulan}/{timezone.now().year}"

        surat = SuratPengantar.objects.create(
            nomor_surat=nomor_surat,
            pemohon_warga=pemohon,
            rt=rt_node,
            rw=rw_node,
            kategori_layanan=kategori,
            keperluan=keperluan,
            status_surat=StatusSurat.PENGAJUAN
        )

        messages.success(request, f"Permohonan surat pengantar No. {nomor_surat} berhasil diajukan!")
        return redirect('portal:surat_list')

    return render(request, 'portal/surat_form.html', {
        'warga_list': warga_list,
        'kategori_choices': KategoriLayanan.choices,
        'role': role
    })


@login_required
def surat_approve_view(request, surat_id):
    """Persetujuan Surat Pengantar — Berjenjang RT dan RW Sesuai Yurisdiksi."""
    surat = get_object_or_404(SuratPengantar, id=surat_id)
    action = request.POST.get('action')

    if action == 'approve_rt':
        if not is_rt_signer(request.user, surat.rt):
            messages.error(request, f"Akses ditolak: Persetujuan tingkat RT hanya berwenang diproses oleh Ketua/Sekretaris {surat.rt.nama}.")
            return redirect('portal:surat_list')
        surat.status_surat = StatusSurat.DISETUJUI_RT
        surat.save()
        messages.success(request, f"Surat {surat.nomor_surat} disetujui RT dan diteruskan ke RW.")

    elif action == 'approve_rw':
        if not is_rw_signer(request.user, surat.rw):
            messages.error(request, f"Akses ditolak: Penerbitan resmi tingkat RW hanya berwenang diproses oleh Ketua/Sekretaris {surat.rw.nama}.")
            return redirect('portal:surat_list')
        surat.status_surat = StatusSurat.DISETUJUI_RW
        surat.diterbitkan_pada = timezone.now()
        surat.berlaku_sampai = timezone.now().date() + datetime.timedelta(days=30)
        surat.save()
        messages.success(request, f"Surat {surat.nomor_surat} resmi disetujui & diterbitkan dengan QR Code!")

    elif action == 'reject':
        if not (is_rt_signer(request.user, surat.rt) or is_rw_signer(request.user, surat.rw)):
            messages.error(request, "Akses ditolak: Penolakan surat hanya dapat diproses oleh pimpinan RT atau RW setempat.")
            return redirect('portal:surat_list')
        alasan = request.POST.get('catatan_penolakan', 'Persyaratan belum lengkap.')
        surat.status_surat = StatusSurat.DITOLAK
        surat.catatan_penolakan = alasan
        surat.save()
        messages.warning(request, f"Surat {surat.nomor_surat} ditolak.")

    return redirect('portal:surat_list')


def surat_print_view(request, surat_id):
    """Tata Letak Cetak Resmi Surat Pengantar dengan QR Code."""
    surat = get_object_or_404(SuratPengantar, id=surat_id)
    verification_url = request.build_absolute_uri(
        reverse('portal:verifikasi_surat', kwargs={'token': surat.verification_token})
    )
    qr_base64 = generate_qr_base64(verification_url)

    context = {
        'surat': surat,
        'qr_base64': qr_base64,
        'verification_url': verification_url,
    }
    return render(request, 'portal/surat_print.html', context)


def public_verifikasi_surat_view(request, token):
    """Portal Verifikasi Publik Pemindai QR Code."""
    surat = SuratPengantar.objects.filter(verification_token=token).select_related('pemohon_warga', 'rt', 'rw').first()

    if not surat:
        return render(request, 'portal/surat_verifikasi.html', {'is_valid': False})

    VerifikasiSuratLog.objects.create(
        surat=surat,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

    is_valid = surat.is_valid_and_active()

    context = {
        'is_valid': is_valid,
        'surat': surat,
        'pemohon': surat.pemohon_warga,
    }
    return render(request, 'portal/surat_verifikasi.html', context)


@login_required
def iuran_desk_view(request):
    """Meja Kas & Penerimaan Iuran — Khusus Bendahara & Pengurus RT/RW."""
    rw, rt, role, _ = get_user_scope(request.user)

    if role == PengurusRole.WARGA:
        return redirect('portal:iuran_saya')

    curr_month = timezone.now().strftime('%Y-%m')
    tagihan_qs = TagihanIuran.objects.filter(periode_bulan=curr_month).select_related('hunian__rt', 'pos_iuran')
    
    if rt:
        tagihan_qs = tagihan_qs.filter(hunian__rt=rt)
    elif rw:
        tagihan_qs = tagihan_qs.filter(hunian__rt__parent=rw)

    status_filter = request.GET.get('status', '')
    if status_filter:
        tagihan_qs = tagihan_qs.filter(status_pembayaran=status_filter)

    total_terkumpul = PembayaranIuran.objects.filter(
        tagihan__periode_bulan=curr_month
    )
    if rt:
        total_terkumpul = total_terkumpul.filter(tagihan__hunian__rt=rt)
    elif rw:
        total_terkumpul = total_terkumpul.filter(tagihan__hunian__rt__parent=rw)

    total_terkumpul_amount = total_terkumpul.aggregate(t=Sum('jumlah_dibayar'))['t'] or Decimal('0.00')

    context = {
        'tagihan_list': tagihan_qs,
        'curr_month': curr_month,
        'curr_month_label': timezone.now().strftime('%B %Y'),
        'status_filter': status_filter,
        'total_terkumpul': total_terkumpul_amount,
        'is_treasurer': is_treasurer(request.user),
    }
    return render(request, 'portal/iuran_desk.html', context)


@login_required
def iuran_saya_view(request):
    """Status Kas & Iuran Rumah Tangga Pribadi — Untuk Akun Warga."""
    _, _, _, warga = get_user_scope(request.user)
    domisili = warga.riwayat_domisili.filter(is_active=True).first() if warga else None
    hunian = domisili.hunian if domisili else None

    tagihan_list = hunian.tagihan_list.all().select_related('pos_iuran').order_by('-periode_bulan') if hunian else []
    pembayaran_list = PembayaranIuran.objects.filter(tagihan__hunian=hunian).select_related('tagihan__pos_iuran') if hunian else []

    context = {
        'warga': warga,
        'hunian': hunian,
        'tagihan_list': tagihan_list,
        'pembayaran_list': pembayaran_list,
    }
    return render(request, 'portal/warga_iuran.html', context)


@login_required
def iuran_bayar_view(request, tagihan_id):
    """Pencatatan Pembayaran Iuran — Khusus Bendahara / Pengurus."""
    if not is_treasurer(request.user):
        messages.error(request, "Akses ditolak: Hanya Bendahara atau Pengurus yang berwenang mencatat penerimaan kas.")
        return redirect('portal:dashboard')

    tagihan = get_object_or_404(TagihanIuran, id=tagihan_id)

    if request.method == 'POST':
        metode = request.POST.get('metode_pembayaran', MetodePembayaran.TUNAI)
        jumlah = tagihan.jumlah_tagihan

        count_bayar = PembayaranIuran.objects.count() + 1
        no_kuitansi = f"KWT-{tagihan.periode_bulan.replace('-', '')}-{count_bayar:04d}"

        pembayaran = PembayaranIuran.objects.create(
            tagihan=tagihan,
            jumlah_dibayar=jumlah,
            metode_pembayaran=metode,
            diverifikasi_oleh=request.user,
            nomor_kuitansi=no_kuitansi
        )

        tagihan.status_pembayaran = StatusPembayaran.LUNAS
        tagihan.save()

        messages.success(request, f"Pembayaran No. Kuitansi {no_kuitansi} berhasil dicatat!")
        return redirect(f"{reverse('portal:kuitansi', kwargs={'nomor_kuitansi': no_kuitansi})}?wa_share=1")

    return redirect('portal:iuran_desk')


def kuitansi_view(request, nomor_kuitansi):
    """Kuitansi Pembayaran Digital Publik."""
    pembayaran = get_object_or_404(PembayaranIuran, nomor_kuitansi=nomor_kuitansi)
    receipt_url = request.build_absolute_uri(reverse('portal:kuitansi', kwargs={'nomor_kuitansi': nomor_kuitansi}))
    qr_base64 = generate_qr_base64(receipt_url)

    wa_text = f"Kuitansi Resmi WargaIn: Pembayaran {pembayaran.tagihan.pos_iuran.nama_pos} ({pembayaran.tagihan.hunian.nomor_rumah}) LUNAS Rp {pembayaran.jumlah_dibayar:,.0f}. Bukti: {receipt_url}"
    wa_link = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

    context = {
        'pembayaran': pembayaran,
        'tagihan': pembayaran.tagihan,
        'qr_base64': qr_base64,
        'wa_link': wa_link,
        'just_paid': request.GET.get('wa_share') == '1'
    }
    return render(request, 'portal/kuitansi.html', context)


# ==============================================================================
# MODUL MADING / PUSAT INFORMASI WARGA
# ==============================================================================

@login_required
def mading_list_view(request):
    """Pusat Informasi & Mading Digital Warga RT/RW."""
    rw, rt, role, warga = get_user_scope(request.user)
    today = timezone.now().date()

    # Filter cakupan wilayah: Pengumuman RW + Pengumuman RT sendiri
    scope_q = Q(lingkup=LingkupDistribusi.RW, wilayah_node=rw)
    if rt:
        scope_q |= Q(lingkup=LingkupDistribusi.RT, wilayah_node=rt)
    elif rw:
        scope_q |= Q(lingkup=LingkupDistribusi.RT, wilayah_node__in=list(rw.children.all()))

    pengumuman_qs = Pengumuman.objects.filter(scope_q)

    tab = request.GET.get('tab', 'terbit')
    kategori_filter = request.GET.get('kategori', '')
    search = request.GET.get('q', '').strip()

    pending_konfirmasi_count = 0
    if is_officer(request.user):
        pending_qs = Pengumuman.objects.filter(status=StatusPengumuman.MENUNGGU_KONFIRMASI)
        if rt:
            pending_qs = pending_qs.filter(wilayah_node=rt)
        elif rw:
            pending_qs = pending_qs.filter(wilayah_node__in=[rw] + list(rw.children.all()))
        pending_konfirmasi_count = pending_qs.count()

    if tab in ['konfirmasi', 'moderasi'] and is_officer(request.user):
        pengumuman_qs = pending_qs
    elif tab == 'arsip':
        pengumuman_qs = pengumuman_qs.filter(
            Q(status=StatusPengumuman.DIARSIPKAN) |
            Q(status=StatusPengumuman.TERBIT, berlaku_sampai__lt=today)
        )
    else:
        # Default: Terbit & Belum Kedaluwarsa
        pengumuman_qs = pengumuman_qs.filter(
            status=StatusPengumuman.TERBIT
        ).filter(
            Q(berlaku_sampai__isnull=True) | Q(berlaku_sampai__gte=today)
        )

    if kategori_filter:
        pengumuman_qs = pengumuman_qs.filter(kategori=kategori_filter)

    if search:
        pengumuman_qs = pengumuman_qs.filter(
            Q(judul__icontains=search) | Q(isi__icontains=search) | Q(lokasi_kegiatan__icontains=search)
        )

    context = {
        'pengumuman_list': pengumuman_qs.select_related('penulis', 'penulis_warga', 'wilayah_node'),
        'tab': tab,
        'kategori_filter': kategori_filter,
        'kategori_choices': KategoriPengumuman.choices,
        'search': search,
        'role': role,
        'rt': rt,
        'rw': rw,
        'is_officer': is_officer(request.user),
        'pending_konfirmasi_count': pending_konfirmasi_count,
        'pending_moderasi_count': pending_konfirmasi_count,
    }
    return render(request, 'portal/mading_list.html', context)


@login_required
def mading_detail_view(request, pengumuman_id):
    """Rincian Pengumuman Mading & Tombol Sebarkan ke WhatsApp."""
    pengumuman = get_object_or_404(Pengumuman, id=pengumuman_id)
    rw, rt, role, _ = get_user_scope(request.user)

    page_url = request.build_absolute_uri()
    
    # Rangkai Pesan WhatsApp Siap Sebar
    wa_lines = [
        f"📢 *MADING WARGA: {pengumuman.judul}*",
        f"Kategori: {pengumuman.get_kategori_display()}",
        f"Wilayah: {pengumuman.wilayah_node.nama}",
        "",
        f"{pengumuman.isi[:250]}..." if len(pengumuman.isi) > 250 else pengumuman.isi,
    ]
    if pengumuman.tanggal_kegiatan:
        wa_lines.append(f"📅 Waktu: {pengumuman.tanggal_kegiatan.strftime('%d %B %Y, Pukul %H:%M WIB')}")
    if pengumuman.lokasi_kegiatan:
        wa_lines.append(f"📍 Lokasi: {pengumuman.lokasi_kegiatan}")

    wa_lines.extend(["", f"Baca selengkapnya di Mading Warga: {page_url}"])
    wa_text = "\n".join(wa_lines)
    wa_share_link = f"https://wa.me/?text={urllib.parse.quote(wa_text)}"

    context = {
        'pengumuman': pengumuman,
        'wa_share_link': wa_share_link,
        'is_officer': is_officer(request.user),
        'is_rt_signer': is_rt_signer(request.user, pengumuman.wilayah_node),
        'is_rw_signer': is_rw_signer(request.user, pengumuman.wilayah_node),
        'just_published': request.GET.get('wa_share') == '1',
    }
    return render(request, 'portal/mading_detail.html', context)


@login_required
def mading_create_view(request):
    """Pembuatan Pengumuman / Kirim Warta Warga (Opsi B: Warga dimoderasi, Pengurus langsung terbit)."""
    rw, rt, role, warga = get_user_scope(request.user)
    user_is_officer = is_officer(request.user)

    if request.method == 'POST':
        judul = request.POST.get('judul', '').strip()
        kategori = request.POST.get('kategori', KategoriPengumuman.RESMI)
        isi = request.POST.get('isi', '').strip()
        lingkup = request.POST.get('lingkup', LingkupDistribusi.RT)
        tanggal_kegiatan = request.POST.get('tanggal_kegiatan') or None
        lokasi_kegiatan = request.POST.get('lokasi_kegiatan', '').strip() or None
        berlaku_sampai = request.POST.get('berlaku_sampai') or None
        is_pinned = request.POST.get('is_pinned') == '1' if user_is_officer else False

        if not judul or not isi:
            messages.error(request, "Judul dan isi warta wajib diisi.")
            return redirect('portal:mading_create')

        if not user_is_officer:
            # Warga Mengirim Warta (Status: Menunggu Konfirmasi)
            wilayah_target = rt or rw
            pengumuman = Pengumuman.objects.create(
                wilayah_node=wilayah_target,
                lingkup=LingkupDistribusi.RT,
                penulis=request.user,
                penulis_warga=warga,
                judul=judul,
                kategori=kategori,
                isi=isi,
                tanggal_kegiatan=tanggal_kegiatan,
                lokasi_kegiatan=lokasi_kegiatan,
                berlaku_sampai=berlaku_sampai,
                status=StatusPengumuman.MENUNGGU_KONFIRMASI,
                is_pinned=False
            )
            messages.success(request, "Warta Anda berhasil dikirim dan sedang menunggu konfirmasi pengurus RT.")
            return redirect('portal:mading_list')
        else:
            # Pengurus Membuat Pengumuman (Status: Terbit Langsung)
            wilayah_target = rw if (lingkup == LingkupDistribusi.RW and rw) else (rt or rw)
            pengumuman = Pengumuman.objects.create(
                wilayah_node=wilayah_target,
                lingkup=lingkup,
                penulis=request.user,
                penulis_warga=warga,
                judul=judul,
                kategori=kategori,
                isi=isi,
                tanggal_kegiatan=tanggal_kegiatan,
                lokasi_kegiatan=lokasi_kegiatan,
                berlaku_sampai=berlaku_sampai,
                status=StatusPengumuman.TERBIT,
                is_pinned=is_pinned,
                disetujui_oleh=request.user,
                disetujui_pada=timezone.now()
            )
            messages.success(request, f"Pengumuman '{judul}' berhasil diterbitkan di Mading!")
            return redirect(f"{reverse('portal:mading_detail', kwargs={'pengumuman_id': pengumuman.id})}?wa_share=1")

    context = {
        'is_officer': user_is_officer,
        'kategori_choices': KategoriPengumuman.choices,
        'lingkup_choices': LingkupDistribusi.choices,
        'rt': rt,
        'rw': rw,
        'role': role
    }
    return render(request, 'portal/mading_form.html', context)


@login_required
def mading_moderasi_view(request, pengumuman_id):
    """Persetujuan / Penolakan Warta Warga oleh Pengurus RT/RW."""
    if not is_officer(request.user):
        messages.error(request, "Akses ditolak: Hanya Pengurus yang berwenang mengonfirmasi warta warga.")
        return redirect('portal:mading_list')

    pengumuman = get_object_or_404(Pengumuman, id=pengumuman_id)
    action = request.POST.get('action')

    if action == 'approve':
        pengumuman.status = StatusPengumuman.TERBIT
        pengumuman.disetujui_oleh = request.user
        pengumuman.disetujui_pada = timezone.now()
        pengumuman.save()
        messages.success(request, f"Warta '{pengumuman.judul}' berhasil dikonfirmasi dan terbit di Mading!")
    elif action == 'reject':
        alasan = request.POST.get('catatan_moderasi') or request.POST.get('catatan_konfirmasi') or 'Tidak memenuhi kriteria publikasi lingkungan.'
        pengumuman.status = StatusPengumuman.DITOLAK
        pengumuman.catatan_konfirmasi = alasan
        pengumuman.save()
        messages.warning(request, f"Warta '{pengumuman.judul}' ditolak.")

    return redirect(f"{reverse('portal:mading_list')}?tab=konfirmasi")


# ==============================================================================
# CITIZEN SELF-REGISTRATION (OPSI 1) & CONFIRMATION WORKFLOW
# ==============================================================================

def register_view(request):
    """
    Public Citizen Self-Registration (Opsi 1):
    1. Validates inputs & password confirmation.
    2. Smart Matching: Checks if NIK blind index matches existing Warga in RT.
       - If matched & unlinked: Links user immediately, activates account (is_active=True), auto-logs in!
       - If new/unmatched: Creates resident record, user (is_active=False), and queues for Ketua RT confirmation.
    """
    if request.user.is_authenticated:
        return redirect('portal:dashboard')

    rt_list = WilayahNode.objects.filter(level=WilayahLevel.RT).select_related('parent').order_by('parent__nama', 'nama')

    if request.method == 'POST':
        nama_lengkap = request.POST.get('nama_lengkap', '').strip()
        nik = request.POST.get('nik', '').strip()
        nomor_wa = request.POST.get('nomor_wa', '').strip()
        rt_id = request.POST.get('rt_id', '').strip()
        nomor_rumah = request.POST.get('nomor_rumah', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        form_data = {
            'nama_lengkap': nama_lengkap,
            'nik': nik,
            'nomor_wa': nomor_wa,
            'rt_id': rt_id,
            'nomor_rumah': nomor_rumah,
            'username': username,
        }

        # Validation 1: Required fields
        if not all([nama_lengkap, nik, nomor_wa, rt_id, nomor_rumah, username, password, password_confirm]):
            messages.error(request, "Semua bidang formulir bertanda bintang wajib diisi.")
            return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

        # Validation 2: NIK 16 digits
        if not (nik.isdigit() and len(nik) == 16):
            messages.error(request, "NIK harus berupa 16 digit angka.")
            return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

        # Validation 3: Password match and length
        if len(password) < 6:
            messages.error(request, "Kata sandi minimal 6 karakter.")
            return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

        if password != password_confirm:
            messages.error(request, "Konfirmasi kata sandi tidak cocok.")
            return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

        # Validation 4: Username uniqueness
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Nama pengguna '{username}' sudah digunakan. Silakan pilih username lain.")
            return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

        # Get RT Node
        selected_rt = WilayahNode.objects.filter(id=rt_id, level=WilayahLevel.RT).first()
        if not selected_rt:
            messages.error(request, "Lingkungan RT yang dipilih tidak valid.")
            return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

        # SMART MATCHING via Blind Index
        blind_idx = hmac_blind_index(nik)
        identitas = IdentitasOrang.objects.filter(nik_blind_index=blind_idx).first()

        if identitas:
            warga = Warga.objects.filter(identitas=identitas).first()
            if warga:
                # Check if this warga already has an active user profile
                existing_profile = PengurusProfile.objects.filter(warga=warga, user__is_active=True).first()
                if existing_profile:
                    messages.error(
                        request,
                        "NIK Anda sudah terdaftar dan memiliki akun aktif. Silakan masuk atau hubungi pengurus RT jika Anda lupa kata sandi."
                    )
                    return render(request, 'portal/register.html', {'rt_list': rt_list, 'form_data': form_data})

                # SMART MATCH SUCCESS: Warga found in existing RT records!
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=nama_lengkap,
                    is_active=True
                )
                PengurusProfile.objects.create(
                    user=user,
                    wilayah_node=selected_rt,
                    role=PengurusRole.WARGA,
                    nomor_wa=nomor_wa,
                    warga=warga
                )

                # Ensure domicile is recorded
                hunian, _ = Hunian.objects.get_or_create(
                    rt=selected_rt,
                    nomor_rumah=nomor_rumah,
                    defaults={'alamat_lengkap': f"Lingkungan {selected_rt.nama}, No. {nomor_rumah}"}
                )
                if not Domisili.objects.filter(warga=warga, hunian=hunian, is_active=True).exists():
                    Domisili.objects.create(
                        hunian=hunian,
                        warga=warga,
                        peran_di_hunian=PeranDiHunian.ANGGOTA,
                        is_active=True
                    )

                AuditLog.objects.create(
                    actor=user,
                    action=AuditAction.INSERT,
                    entity_name='User',
                    entity_id=str(user.id),
                    new_values={'username': username, 'verifikasi': 'INSTANT_MATCH_NIK'},
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                # Auto login
                login(request, user)
                messages.success(
                    request,
                    f"Selamat datang, {nama_lengkap}! NIK Anda cocok dengan basis data kependudukan RT. Akun langsung aktif seketika."
                )
                return redirect('portal:dashboard')

        # NEW CITIZEN / UNMATCHED: Queue for RT Confirmation
        identitas = IdentitasOrang.objects.create(nik_blind_index=blind_idx)
        warga = Warga(
            identitas=identitas,
            rw=selected_rt.parent or selected_rt,
            nama_lengkap=nama_lengkap,
            tempat_lahir='-',
            tanggal_lahir=datetime.date(1990, 1, 1),
            jenis_kelamin=JenisKelamin.LAKI_LAKI,
            agama=Agama.ISLAM,
            status_perkawinan=StatusPerkawinan.BELUM_KAWIN,
            nomor_telepon=nomor_wa,
            status_keberadaan=StatusKeberadaan.AKTIF
        )
        warga.set_nik(nik)
        warga.save()

        hunian, _ = Hunian.objects.get_or_create(
            rt=selected_rt,
            nomor_rumah=nomor_rumah,
            defaults={'alamat_lengkap': f"Lingkungan {selected_rt.nama}, No. {nomor_rumah}"}
        )
        Domisili.objects.create(
            hunian=hunian,
            warga=warga,
            peran_di_hunian=PeranDiHunian.KEPALA_RUMAH_TANGGA,
            is_active=True
        )

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=nama_lengkap,
            is_active=False  # Pending RT Confirmation
        )
        PengurusProfile.objects.create(
            user=user,
            wilayah_node=selected_rt,
            role=PengurusRole.WARGA,
            nomor_wa=nomor_wa,
            warga=warga
        )

        AuditLog.objects.create(
            actor=None,
            action=AuditAction.INSERT,
            entity_name='User',
            entity_id=str(user.id),
            new_values={'username': username, 'status': 'MENUNGGU_KONFIRMASI_RT', 'rt': selected_rt.nama},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        messages.info(
            request,
            f"Pendaftaran berhasil! Akun Anda sedang menunggu konfirmasi dari Ketua {selected_rt.nama} demi verifikasi lingkungan. Anda dapat masuk setelah dikonfirmasi."
        )
        return redirect('portal:login')

    return render(request, 'portal/register.html', {'rt_list': rt_list})


@login_required
def konfirmasi_warga_baru_view(request, profile_id):
    """
    Konfirmasi atau tolak pendaftaran akun warga baru oleh Pengurus RT/Sekretaris RT/Admin.
    """
    if not is_officer(request.user):
        messages.error(request, "Akses ditolak: Hanya pengurus RT yang berwenang mengonfirmasi pendaftaran warga.")
        return redirect('portal:dashboard')

    rw, rt, role, _ = get_user_scope(request.user)
    profile = get_object_or_404(PengurusProfile, id=profile_id, role=PengurusRole.WARGA)

    # Scoping check: RT officers only confirm residents in their RT
    if rt and profile.wilayah_node != rt:
        messages.error(request, "Anda hanya dapat mengonfirmasi pendaftaran warga di lingkungan RT Anda sendiri.")
        return redirect('portal:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')  # 'approve' or 'reject'
        user = profile.user
        warga = profile.warga

        if action == 'approve':
            user.is_active = True
            user.save()

            AuditLog.objects.create(
                actor=request.user,
                action=AuditAction.UPDATE,
                entity_name='User',
                entity_id=str(user.id),
                old_values={'is_active': False},
                new_values={'is_active': True, 'action': 'KONFIRMASI_WARGA_DISETUJUI'},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            messages.success(request, f"Akun warga '{user.first_name}' berhasil dikonfirmasi dan diaktifkan.")
        elif action == 'reject':
            alasan = request.POST.get('alasan', 'Data tidak sesuai verifikasi lingkungan').strip()
            username = user.username
            first_name = user.first_name
            user.delete()
            AuditLog.objects.create(
                actor=request.user,
                action=AuditAction.DELETE,
                entity_name='User',
                entity_id=username,
                old_values={'username': username, 'nama': first_name},
                new_values={'action': 'PENDAFTARAN_WARGA_DITOLAK', 'alasan': alasan},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            messages.info(request, f"Pendaftaran akun '{first_name}' telah ditolak.")

    return redirect(request.POST.get('next') or 'portal:dashboard')


# ==============================================================================
# PROGRESSIVE WEB APP (PWA) VIEWS
# ==============================================================================

def manifest_view(request):
    """
    Returns the Web App Manifest (PWA) with MIME type application/manifest+json.
    """
    manifest_data = {
        "name": "WargaIn - Aplikasi Lingkungan RT/RW",
        "short_name": "WargaIn",
        "description": "Tata kelola administrasi kependudukan, iuran kas warga, surat pengantar digital, dan mading informasi RT/RW.",
        "start_url": "/dashboard/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#064e3b",
        "theme_color": "#064e3b",
        "orientation": "portrait-primary",
        "lang": "id-ID",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/icons/icon-maskable-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable"
            },
            {
                "src": "/static/icons/icon.svg",
                "sizes": "512x512",
                "type": "image/svg+xml",
                "purpose": "any"
            }
        ],
        "categories": ["utilities", "productivity", "social"]
    }
    response = HttpResponse(json.dumps(manifest_data, indent=2), content_type="application/manifest+json; charset=utf-8")
    response['Cache-Control'] = 'public, max-age=86400'
    return response


def service_worker_view(request):
    """
    Serves the Service Worker from root domain /sw.js with Service-Worker-Allowed header.
    """
    sw_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'js', 'sw.js')
    if os.path.exists(sw_path):
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = "/* sw.js not found */"
    response = HttpResponse(content, content_type="application/javascript; charset=utf-8")
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def offline_view(request):
    """
    Displays the graceful offline fallback page when device connectivity is lost.
    """
    return render(request, 'portal/offline.html')


