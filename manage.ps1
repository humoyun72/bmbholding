#!/usr/bin/env pwsh
# =============================================================================
#  IntegrityBot — Loyihani boshqarish skripti (Windows PowerShell)
#  Ishlatish: .\manage.ps1 <buyruq> [--profile <profil>]
#
#  Buyruqlar:
#    up          — Servislarni ishga tushirish (dev)
#    down        — Servislarni to'xtatish
#    restart     — Qayta ishga tushirish
#    build       — Imagelarni qayta build qilish
#    logs        — Loglarni ko'rish
#    status      — Konteynerlar holati
#    shell       — Backend konteyneri ichiga kirish
#    migrate     — DB migratsiyalarini qo'llash
#    seed        — Boshlang'ich ma'lumotlar yuklash
#    test        — Testlarni ishga tushirish
#    clean       — Barcha konteyner, volume, imaglarni tozalash
#    prod        — Production rejimida ishga tushirish
#    monitoring  — Monitoring stekini (Prometheus+Grafana) ishga tushirish
#    help        — Yordam ko'rsatish
# =============================================================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [string]$Service = "",
    [switch]$Follow = $false,
    [switch]$Clean = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

# Ranglar
function Write-Color([string]$Text, [string]$Color = "White") {
    Write-Host $Text -ForegroundColor $Color
}

function Info([string]$msg)    { Write-Color "ℹ️  $msg" "Cyan" }
function Success([string]$msg) { Write-Color "✅ $msg" "Green" }
function Warning([string]$msg) { Write-Color "⚠️  $msg" "Yellow" }
function Error([string]$msg)   { Write-Color "❌ $msg" "Red" }
function Header([string]$msg)  {
    Write-Color ""
    Write-Color "═══════════════════════════════════════════" "DarkCyan"
    Write-Color "  $msg" "White"
    Write-Color "═══════════════════════════════════════════" "DarkCyan"
}

# .env faylini tekshirish
function Check-Env {
    if (-not (Test-Path "$ProjectRoot\.env")) {
        Warning ".env fayli topilmadi. .env.example dan nusxa olinmoqda..."
        Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
        Warning ".env faylini to'ldirishni unutmang: POSTGRES_PASSWORD, TELEGRAM_BOT_TOKEN, SECRET_KEY"
        return $false
    }

    # Muhim o'zgaruvchilarni tekshirish
    $envContent = Get-Content "$ProjectRoot\.env" -Raw
    $issues = @()

    if ($envContent -match "POSTGRES_PASSWORD=CHANGE_ME" -or $envContent -notmatch "POSTGRES_PASSWORD=.+") {
        $issues += "POSTGRES_PASSWORD (hali o'zgartirilmagan)"
    }
    if ($envContent -match "SECRET_KEY=CHANGE_ME" -or $envContent -notmatch "SECRET_KEY=.+") {
        $issues += "SECRET_KEY (hali o'zgartirilmagan)"
    }
    if ($envContent -notmatch "TELEGRAM_BOT_TOKEN=[0-9]+:") {
        $issues += "TELEGRAM_BOT_TOKEN (noto'g'ri yoki bo'sh)"
    }

    if ($issues.Count -gt 0) {
        Warning "Quyidagi .env o'zgaruvchilari to'ldirilmagan:"
        foreach ($issue in $issues) {
            Write-Color "   ⚠️  $issue" "Yellow"
        }
        return $false
    }
    return $true
}

# Docker mavjudligini tekshirish
function Check-Docker {
    try {
        $null = docker info 2>&1
        return $true
    } catch {
        Error "Docker ishlamayapti! Docker Desktop ni ishga tushiring."
        return $false
    }
}

# ── BUYRUQLAR ────────────────────────────────────────────────────────────────

function Cmd-Up {
    Header "IntegrityBot — Ishga tushirish (Development)"

    if (-not (Check-Docker)) { return }

    $envOk = Check-Env
    if (-not $envOk) {
        $confirm = Read-Host "Muammolar bor. Davom etish? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") { return }
    }

    Info "Servislar ishga tushirilmoqda..."
    Info "Faqat asosiy servislar: backend, frontend, db, redis"
    Info "(Monitoring, ClamAV, Vault — alohida profileda)"

    Set-Location $ProjectRoot
    docker-compose up -d --build

    if ($LASTEXITCODE -eq 0) {
        Success "Servislar muvaffaqiyatli ishga tushdi!"
        Write-Color ""
        Write-Color "  🌐 Frontend:    http://localhost:5173" "Green"
        Write-Color "  🔧 Backend API: http://localhost:8000" "Green"
        Write-Color "  📚 API Docs:    http://localhost:8000/docs" "Green"
        Write-Color "  🗄️  DB Port:     localhost:5432" "Green"
        Write-Color "  🔴 Redis Port:  localhost:6379" "Green"
        Write-Color ""
        Info "Loglarni ko'rish: .\manage.ps1 logs"
        Info "To'xtatish:       .\manage.ps1 down"
    } else {
        Error "Servislarni ishga tushirishda xatolik!"
        Info "Loglarni tekshiring: .\manage.ps1 logs"
    }
}

function Cmd-Down {
    Header "IntegrityBot — Servislarni to'xtatish"

    if (-not (Check-Docker)) { return }

    Set-Location $ProjectRoot

    if ($Clean) {
        Warning "Volumelar ham o'chiriladi!"
        $confirm = Read-Host "Davom etish? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") { return }
        docker-compose down -v --remove-orphans
    } else {
        docker-compose down --remove-orphans
    }

    if ($LASTEXITCODE -eq 0) {
        Success "Servislar to'xtatildi!"
    }
}

function Cmd-Restart {
    Header "IntegrityBot — Qayta ishga tushirish"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    if ($Service) {
        Info "Servis qayta ishga tushirilmoqda: $Service"
        docker-compose restart $Service
    } else {
        docker-compose restart
    }
    Success "Qayta ishga tushirildi!"
}

function Cmd-Build {
    Header "IntegrityBot — Image build"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    Info "Imagelar qayta build qilinmoqda (cache o'chirilgan)..."
    docker-compose build --no-cache

    if ($LASTEXITCODE -eq 0) {
        Success "Build muvaffaqiyatli!"
    } else {
        Error "Build xatoligi!"
    }
}

function Cmd-Logs {
    Header "IntegrityBot — Loglar"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    if ($Service) {
        Info "Servis loglari: $Service (oxirgi 100 qator)"
        docker-compose logs --tail=100 -f $Service
    } else {
        Info "Barcha servislar loglari (oxirgi 50 qator)"
        docker-compose logs --tail=50 -f
    }
}

function Cmd-Status {
    Header "IntegrityBot — Konteynerlar holati"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    docker-compose ps
    Write-Color ""
    Info "Disk va xotira:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
}

function Cmd-Shell {
    Header "IntegrityBot — Backend shell"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    $svc = if ($Service) { $Service } else { "backend" }
    Info "Konteynerga ulanilmoqda: $svc"
    docker-compose exec $svc /bin/bash
}

function Cmd-Migrate {
    Header "IntegrityBot — DB Migratsiya"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    Info "Migratsiyalar qo'llanilmoqda..."
    docker-compose exec backend alembic upgrade head

    if ($LASTEXITCODE -eq 0) {
        Success "Migratsiyalar muvaffaqiyatli qo'llandi!"
    } else {
        Error "Migratsiya xatoligi!"
        Info "Loglarni tekshiring: .\manage.ps1 logs -Service backend"
    }
}

function Cmd-Seed {
    Header "IntegrityBot — Boshlang'ich ma'lumotlar"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    Info "Admin foydalanuvchi va boshlang'ich ma'lumotlar yuklanmoqda..."
    docker-compose exec backend python -c "
import asyncio
from app.core.database import engine, Base
from app.services.auth import create_default_admin
asyncio.run(create_default_admin())
print('Done!')
"
    Success "Ma'lumotlar yuklandi!"
}

function Cmd-Test {
    Header "IntegrityBot — Testlar"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    Info "Testlar ishga tushirilmoqda..."
    docker-compose exec backend python -m pytest tests/ -v --tb=short

    if ($LASTEXITCODE -eq 0) {
        Success "Barcha testlar o'tdi!"
    } else {
        Warning "Ba'zi testlar muvaffaqiyatsiz!"
    }
}

function Cmd-Prod {
    Header "IntegrityBot — Production rejimi"

    if (-not (Check-Docker)) { return }

    $envOk = Check-Env
    if (-not $envOk) {
        Error "Production uchun .env to'liq to'ldirilishi shart!"
        return
    }

    Set-Location $ProjectRoot

    Info "Production servislar ishga tushirilmoqda..."
    Info "Profillar: production (nginx, clamav, db-backup)"

    docker-compose `
        -f docker-compose.yml `
        -f docker-compose.prod.yml `
        --profile production `
        up -d --build

    if ($LASTEXITCODE -eq 0) {
        Success "Production servislar ishga tushdi!"
        Write-Color ""
        Write-Color "  🌐 Web: http://localhost (nginx orqali)" "Green"
        Write-Color ""
        Warning "SSL sertifikatlari: ./nginx/certs/ papkasida bo'lishi kerak"
    } else {
        Error "Production rejimida xatolik!"
    }
}

function Cmd-Monitoring {
    Header "IntegrityBot — Monitoring (Prometheus + Grafana)"

    if (-not (Check-Docker)) { return }
    Set-Location $ProjectRoot

    Info "Monitoring servislar ishga tushirilmoqda..."
    docker-compose --profile monitoring up -d

    if ($LASTEXITCODE -eq 0) {
        Success "Monitoring ishga tushdi!"
        Write-Color ""
        Write-Color "  📊 Prometheus: http://localhost:9090" "Green"
        Write-Color "  📈 Grafana:    http://localhost:3000" "Green"
        Write-Color "     Login: admin / (GRAFANA_PASSWORD .env da)" "Cyan"
        Write-Color ""
    }
}

function Cmd-Clean {
    Header "IntegrityBot — To'liq tozalash"

    Warning "DIQQAT! Bu barcha ma'lumotlarni o'chiradi:"
    Write-Color "  - Barcha konteynerlar" "Red"
    Write-Color "  - Barcha volumelar (DB, Redis, fayllar)" "Red"
    Write-Color "  - Barcha build imagelar" "Red"
    Write-Color ""

    $confirm = Read-Host "Haqiqatan ham tozalashni xohlaysizmi? (yes/NO)"
    if ($confirm -ne "yes") {
        Info "Bekor qilindi."
        return
    }

    Set-Location $ProjectRoot

    docker-compose down -v --remove-orphans --rmi local

    if ($LASTEXITCODE -eq 0) {
        Success "Tozalash yakunlandi!"
    }
}

function Cmd-Check {
    Header "IntegrityBot — Servislar tekshiruvi"

    if (-not (Check-Docker)) { return }

    Write-Color ""
    Write-Color "  Konteynerlar:" "Yellow"

    $services = @("integrity-bot-backend-1", "integrity-bot-frontend-1", "integrity-bot-db-1", "integrity-bot-redis-1")
    foreach ($svc in $services) {
        $status = docker inspect --format "{{.State.Status}}" $svc 2>$null
        if ($status -eq "running") {
            Write-Color "  ✅ $svc — running" "Green"
        } else {
            Write-Color "  ❌ $svc — $status" "Red"
        }
    }

    Write-Color ""
    Write-Color "  API tekshiruv:" "Yellow"

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Color "  ✅ Backend API — http://localhost:8000 (200 OK)" "Green"
        }
    } catch {
        Write-Color "  ❌ Backend API — javob bermayapti" "Red"
    }

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Color "  ✅ Frontend — http://localhost:5173 (200 OK)" "Green"
        }
    } catch {
        Write-Color "  ⚠️  Frontend — http://localhost:5173 (ulanib bo'lmadi)" "Yellow"
    }

    Write-Color ""
    Write-Color "  🌐 Manzillar:" "Cyan"
    Write-Color "     Frontend:    http://localhost:5173" "White"
    Write-Color "     Backend API: http://localhost:8000" "White"
    Write-Color "     API Docs:    http://localhost:8000/docs" "White"
    Write-Color "     DB:          localhost:5432" "White"
    Write-Color "     Redis:       localhost:6379" "White"
    Write-Color ""
    Write-Color "  🔐 Admin kirish:" "Cyan"
    Write-Color "     URL:      http://localhost:5173/login" "White"
    Write-Color "     Username: admin" "White"

    $envContent = Get-Content "$ProjectRoot\.env" -Raw -ErrorAction SilentlyContinue
    if ($envContent -match "ADMIN_DEFAULT_PASSWORD=(.+)") {
        Write-Color "     Parol:    $($Matches[1].Trim())" "White"
    }
    Write-Color ""
}

function Cmd-Help {
    Write-Color ""
    Write-Color "╔═══════════════════════════════════════════════════════╗" "DarkCyan"
    Write-Color "║         IntegrityBot — Boshqaruv Skripti             ║" "Cyan"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  Ishlatish: .\manage.ps1 <buyruq> [parametrlar]      ║" "White"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  ASOSIY BUYRUQLAR:                                    ║" "Yellow"
    Write-Color "║    up          Servislarni ishga tushirish (dev)      ║" "White"
    Write-Color "║    down        Servislarni to'xtatish                 ║" "White"
    Write-Color "║    down -Clean Volumelar bilan to'xtatish             ║" "White"
    Write-Color "║    restart     Qayta ishga tushirish                  ║" "White"
    Write-Color "║    build       Imagelarni qayta build qilish          ║" "White"
    Write-Color "║    status      Konteynerlar holati va resurslar       ║" "White"
    Write-Color "║    check       API va servislar ishlayotganini tekshir ║" "White"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  LOG VA DEBUG:                                        ║" "Yellow"
    Write-Color "║    logs                 Barcha loglar                 ║" "White"
    Write-Color "║    logs -Service backend  Backend loglari             ║" "White"
    Write-Color "║    shell                Backend shelliga kirish       ║" "White"
    Write-Color "║    shell -Service db    DB shelliga kirish            ║" "White"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  MA'LUMOTLAR BAZASI:                                  ║" "Yellow"
    Write-Color "║    migrate     DB migratsiyalarini qo'llash           ║" "White"
    Write-Color "║    seed        Boshlang'ich ma'lumotlar               ║" "White"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  TEST VA PRODUCTION:                                  ║" "Yellow"
    Write-Color "║    test        Barcha testlarni ishga tushirish       ║" "White"
    Write-Color "║    prod        Production rejimida ishga tushirish    ║" "White"
    Write-Color "║    monitoring  Prometheus + Grafana ishga tushirish   ║" "White"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  TOZALASH:                                            ║" "Red"
    Write-Color "║    clean       Barcha ma'lumotlarni o'chirish ⚠️       ║" "White"
    Write-Color "╠═══════════════════════════════════════════════════════╣" "DarkCyan"
    Write-Color "║  MISOL:                                               ║" "Yellow"
    Write-Color "║    .\manage.ps1 up                                    ║" "White"
    Write-Color "║    .\manage.ps1 logs -Service backend                 ║" "White"
    Write-Color "║    .\manage.ps1 down -Clean                           ║" "White"
    Write-Color "║    .\manage.ps1 prod                                  ║" "White"
    Write-Color "╚═══════════════════════════════════════════════════════╝" "DarkCyan"
    Write-Color ""
}

# ── ASOSIY DISPATCHER ─────────────────────────────────────────────────────────
Set-Location $ProjectRoot

switch ($Command.ToLower()) {
    "up"         { Cmd-Up }
    "down"       { Cmd-Down }
    "restart"    { Cmd-Restart }
    "build"      { Cmd-Build }
    "logs"       { Cmd-Logs }
    "status"     { Cmd-Status }
    "ps"         { Cmd-Status }
    "check"      { Cmd-Check }
    "shell"      { Cmd-Shell }
    "exec"       { Cmd-Shell }
    "migrate"    { Cmd-Migrate }
    "seed"       { Cmd-Seed }
    "test"       { Cmd-Test }
    "prod"       { Cmd-Prod }
    "production" { Cmd-Prod }
    "monitoring" { Cmd-Monitoring }
    "clean"      { Cmd-Clean }
    "help"       { Cmd-Help }
    default {
        Error "Noma'lum buyruq: $Command"
        Cmd-Help
    }
}

