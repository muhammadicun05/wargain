@echo off
setlocal
title WargaIn v2 - Development Server
echo ========================================================
echo   WargaIn: Aplikasi Tata Kelola RT/RW
echo   Django 5 + PostgreSQL 18 + Tailwind CSS
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto :no_venv

echo [1/3] Menjalankan pengecekan migrasi database...
.\.venv\Scripts\python.exe manage.py migrate
if errorlevel 1 goto :migration_failed

echo.
echo [2/3] Membuka browser ke http://127.0.0.1:8000 ...
start http://127.0.0.1:8000

echo.
echo [3/3] Menjalankan Django Development Server pada port 8000...
echo Tekan CTRL+C untuk menghentikan server.
echo.
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
goto :eof

:no_venv
echo [ERROR] Virtual environment (.venv) tidak ditemukan pada direktori ini!
echo Silakan pastikan folder .venv sudah tersedia.
pause
exit /b 1

:migration_failed
echo.
echo [ERROR] Terjadi kegagalan saat migrasi database PostgreSQL.
echo Pastikan service PostgreSQL aktif pada port 5432 dan database wargain_v2 ada.
pause
exit /b 1
