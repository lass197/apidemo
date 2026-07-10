# SGHL — démarrage développement (Windows PowerShell)
# Usage : .\start-dev.ps1

$python = "C:\Users\HP\lasspython\Scripts\python.exe"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== SGHL — preparation ===" -ForegroundColor Cyan
Set-Location "$root\backend"
& $python manage.py migrate
& $python manage.py seed_sghl

Write-Host "`n=== Backend Django : http://127.0.0.1:8000 ===" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; $python manage.py runserver 8000"

Write-Host "=== Frontend staff : http://localhost:5173 ===" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host "=== Console admin  : http://localhost:5174/admin/ ===" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\admin'; npm run dev"

Write-Host "`nComptes :"
Write-Host "  Staff   → sec.dupont / Secretaire@2026  (port 5173)"
Write-Host "  Admin   → admin / Admin@SGHL2026        (port 5174 ou /admin/)"
Write-Host "  Patient → alice.moreau / Patient@2026   (app Flutter mobile)"
