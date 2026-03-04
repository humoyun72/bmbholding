# ╔══════════════════════════════════════════════════════════════╗
# ║          IntegrityBot — Tezkor Boshqaruv Skripti            ║
# ║                  Windows PowerShell uchun                    ║
# ╚══════════════════════════════════════════════════════════════╝
#
# ISHLATISH:
#   .\dev.ps1               → Menyuni ko'rsatadi
#   .\dev.ps1 up            → Barcha servislarni ishga tushirish
#   .\dev.ps1 down          → Barcha servislarni to'xtatish
#   .\dev.ps1 restart       → Barcha servislarni qayta ishga tushirish
#   .\dev.ps1 rb            → Faqat backend ni rebuild + restart
#   .\dev.ps1 rf            → Faqat frontend ni rebuild + restart
#   .\dev.ps1 ra            → Ikkalasini rebuild + restart
#   .\dev.ps1 logs          → Barcha loglar (real-time)
#   .\dev.ps1 logs b        → Faqat backend loglari
#   .\dev.ps1 logs f        → Faqat frontend loglari
#   .\dev.ps1 ps            → Servislar holati
#   .\dev.ps1 clean         → Keraksiz Docker narsalarni tozalash
#   .\dev.ps1 db            → DB ga kirish (psql)
#   .\dev.ps1 migrate       → Alembic migratsiyalarni bajarish
#   .\dev.ps1 shell         → Backend container ichiga kirish

param(
    [Parameter(Position=0)]
    [string]$Command = "menu",

    [Parameter(Position=1)]
    [string]$SubCommand = ""
)

# ─── Ranglar ───────────────────────────────────────────────────
function Write-Info    { param($msg) Write-Host "ℹ  $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "⚠  $msg" -ForegroundColor Yellow }
function Write-Step    { param($msg) Write-Host "`n▶ $msg" -ForegroundColor Blue }
function Write-Err     { param($msg) Write-Host "❌ $msg" -ForegroundColor Red; exit 1 }

# ─── Skript qayerda turganini aniqlash ──────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ─── .env tekshiruvi ────────────────────────────────────────────
function Check-Env {
    if (-not (Test-Path ".env")) {
        Write-Warning ".env fayli topilmadi!"
        if (Test-Path ".env.example") {
            $ans = Read-Host "  .env.example dan nusxa ko'chirilsinmi? [y/N]"
            if ($ans -match "^[Yy]$") {
                Copy-Item ".env.example" ".env"
                Write-Success ".env yaratildi. Iltimos qiymatlarni to'ldiring."
                exit 0
            }
        }
        Write-Err ".env fayli kerak!"
    }
}

# ─── Vaqt o'lchash ──────────────────────────────────────────────
$global:StartTime = $null
function Start-Timer { $global:StartTime = Get-Date }
function Stop-Timer  {
    $elapsed = [int](((Get-Date) - $global:StartTime).TotalSeconds)
    Write-Host "  ⏱  Vaqt: ${elapsed}s" -ForegroundColor Cyan
}

# ─── Health check ────────────────────────────────────────────────
function Wait-Backend {
    Write-Info "Backend health tekshirish..."
    Start-Sleep -Seconds 3
    for ($i = 1; $i -le 10; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            Write-Success "Backend ishlayapti! (http://localhost:8000)"
            return
        } catch { }
        if ($i -eq 10) {
            Write-Warning "Health check kelmadi. Loglarni tekshiring: .\dev.ps1 logs b"
        }
        Start-Sleep -Seconds 2
    }
}

# ─── Holat (qisqa) ───────────────────────────────────────────────
function Show-StatusShort {
    Write-Host "`n  Servislar:" -ForegroundColor White
    docker compose ps --format "table {{.Name}}`t{{.Status}}`t{{.Ports}}" 2>$null |
        Select-Object -Skip 1 |
        ForEach-Object {
            if ($_ -match "Up|running") {
                Write-Host "  ● $_" -ForegroundColor Green
            } else {
                Write-Host "  ● $_" -ForegroundColor Red
            }
        }
}

# ═══════════════════════════════════════════════════════════════
#  BUYRUQLAR
# ═══════════════════════════════════════════════════════════════

function Cmd-Up {
    Check-Env
    Write-Step "Barcha servislarni ishga tushirish..."
    Start-Timer
    docker compose up -d --remove-orphans
    Stop-Timer
    Write-Host ""
    Write-Success "Barcha servislar ishga tushdi!"
    Show-StatusShort
    Write-Host ""
    Write-Host "  Frontend:" -NoNewline; Write-Host "  http://localhost:5173" -ForegroundColor Cyan
    Write-Host "  Backend: " -NoNewline; Write-Host "  http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  API Docs:" -NoNewline; Write-Host "  http://localhost:8000/docs" -ForegroundColor Cyan
}

function Cmd-Down {
    Write-Step "Barcha servislarni to'xtatish..."
    docker compose down
    Write-Success "To'xtatildi."
}

function Cmd-Restart {
    Write-Step "Barcha servislarni qayta ishga tushirish..."
    Start-Timer
    docker compose restart
    Stop-Timer
    Write-Success "Qayta ishga tushirildi."
    Show-StatusShort
}

# ─── Backend rebuild ─────────────────────────────────────────────
function Cmd-Rb {
    Check-Env
    Write-Step "Backend rebuild va restart..."
    Start-Timer
    docker compose build --no-cache backend
    docker compose up -d --no-deps backend
    Stop-Timer
    Write-Host ""
    Wait-Backend
}

# ─── Frontend rebuild ────────────────────────────────────────────
function Cmd-Rf {
    Check-Env
    Write-Step "Frontend rebuild va restart..."
    Start-Timer
    docker compose build --no-cache frontend
    docker compose up -d --no-deps frontend
    Stop-Timer
    Write-Success "Frontend yangilandi! (http://localhost:5173)"
}

# ─── Ikkalasini rebuild ──────────────────────────────────────────
function Cmd-Ra {
    Check-Env
    Write-Step "Backend + Frontend rebuild va restart..."
    Start-Timer
    docker compose build --no-cache backend frontend
    docker compose up -d --no-deps backend frontend
    Stop-Timer
    Write-Host ""
    Write-Success "Ikkalasi yangilandi!"
    Write-Host ""
    Write-Host "  Frontend:" -NoNewline; Write-Host "  http://localhost:5173" -ForegroundColor Cyan
    Write-Host "  Backend: " -NoNewline; Write-Host "  http://localhost:8000" -ForegroundColor Cyan
}

# ─── Loglar ─────────────────────────────────────────────────────
function Cmd-Logs {
    param($sub)
    switch ($sub) {
        { $_ -in "b","back","backend" }   { docker compose logs -f --tail=100 backend }
        { $_ -in "f","front","frontend" } { docker compose logs -f --tail=100 frontend }
        { $_ -in "d","db","database" }    { docker compose logs -f --tail=100 db }
        { $_ -in "r","redis" }            { docker compose logs -f --tail=100 redis }
        default                           { docker compose logs -f --tail=50 }
    }
}

# ─── Holat ──────────────────────────────────────────────────────
function Cmd-Ps {
    Write-Host ""
    docker compose ps
    Write-Host ""
}

# ─── Tozalash ────────────────────────────────────────────────────
function Cmd-Clean {
    Write-Warning "Bu keraksiz Docker image, container va cache ni o'chiradi."
    $ans = Read-Host "  Davom etilsinmi? [y/N]"
    if ($ans -match "^[Yy]$") {
        Write-Step "Tozalash..."
        docker system prune -f
        docker image prune -f
        Write-Success "Tozalandi!"
        docker system df
    }
}

# ─── DB kirish ───────────────────────────────────────────────────
function Cmd-Db {
    $dbName = "integritybot"
    $dbUser = "postgres"
    if (Test-Path ".env") {
        $env_content = Get-Content ".env"
        $dbLine = $env_content | Where-Object { $_ -match "^POSTGRES_DB=" }
        if ($dbLine) { $dbName = $dbLine.Split("=")[1].Trim('"') }
        $userLine = $env_content | Where-Object { $_ -match "^POSTGRES_USER=" }
        if ($userLine) { $dbUser = $userLine.Split("=")[1].Trim('"') }
    }
    Write-Info "DB ga ulanish: $dbName @ $dbUser"
    docker compose exec db psql -U $dbUser -d $dbName
}

# ─── Migratsiya ──────────────────────────────────────────────────
function Cmd-Migrate {
    Write-Step "Alembic migratsiyalarni bajarish..."
    docker compose exec backend alembic upgrade head
    Write-Success "Migratsiyalar bajarildi."
}

# ─── Backend shell ───────────────────────────────────────────────
function Cmd-Shell {
    Write-Info "Backend container ichiga kirish..."
    docker compose exec backend bash 2>$null
    if ($LASTEXITCODE -ne 0) {
        docker compose exec backend sh
    }
}

# ─── Menyu ──────────────────────────────────────────────────────
function Show-Menu {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║       IntegrityBot — Boshqaruv Skripti      ║" -ForegroundColor Blue
    Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
    Write-Host "  ASOSIY:" -ForegroundColor White
    Write-Host "  " -NoNewline; Write-Host "up          " -ForegroundColor Green -NoNewline; Write-Host " Barcha servislarni ishga tushirish"
    Write-Host "  " -NoNewline; Write-Host "down        " -ForegroundColor Green -NoNewline; Write-Host " Barcha servislarni to'xtatish"
    Write-Host "  " -NoNewline; Write-Host "restart     " -ForegroundColor Green -NoNewline; Write-Host " Barcha servislarni qayta ishga tushirish"
    Write-Host ""
    Write-Host "  REBUILD (tezkor):" -ForegroundColor White
    Write-Host "  " -NoNewline; Write-Host "rb          " -ForegroundColor Yellow -NoNewline; Write-Host " Faqat backend  → rebuild + restart"
    Write-Host "  " -NoNewline; Write-Host "rf          " -ForegroundColor Yellow -NoNewline; Write-Host " Faqat frontend → rebuild + restart"
    Write-Host "  " -NoNewline; Write-Host "ra          " -ForegroundColor Yellow -NoNewline; Write-Host " Ikkalasi       → rebuild + restart"
    Write-Host ""
    Write-Host "  MONITORING:" -ForegroundColor White
    Write-Host "  " -NoNewline; Write-Host "logs        " -ForegroundColor Cyan -NoNewline; Write-Host " Barcha loglar (real-time)"
    Write-Host "  " -NoNewline; Write-Host "logs b      " -ForegroundColor Cyan -NoNewline; Write-Host " Faqat backend loglari"
    Write-Host "  " -NoNewline; Write-Host "logs f      " -ForegroundColor Cyan -NoNewline; Write-Host " Faqat frontend loglari"
    Write-Host "  " -NoNewline; Write-Host "logs d      " -ForegroundColor Cyan -NoNewline; Write-Host " Faqat DB loglari"
    Write-Host "  " -NoNewline; Write-Host "ps          " -ForegroundColor Cyan -NoNewline; Write-Host " Servislar holati"
    Write-Host ""
    Write-Host "  BOSHQA:" -ForegroundColor White
    Write-Host "  " -NoNewline; Write-Host "db          " -ForegroundColor Magenta -NoNewline; Write-Host " PostgreSQL ga kirish"
    Write-Host "  " -NoNewline; Write-Host "migrate     " -ForegroundColor Magenta -NoNewline; Write-Host " Alembic migratsiyalar"
    Write-Host "  " -NoNewline; Write-Host "shell       " -ForegroundColor Magenta -NoNewline; Write-Host " Backend container ichiga kirish"
    Write-Host "  " -NoNewline; Write-Host "clean       " -ForegroundColor Magenta -NoNewline; Write-Host " Docker cache ni tozalash"
    Write-Host ""
    Write-Host "  MISOL:" -ForegroundColor White
    Write-Host "  .\dev.ps1 rb    # Backend kodi o'zgarganda"
    Write-Host "  .\dev.ps1 ra    # Ikkalasini yangilash"
    Write-Host ""
}

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
switch ($Command.ToLower()) {
    "up"                            { Cmd-Up }
    "down"                          { Cmd-Down }
    "restart"                       { Cmd-Restart }
    { $_ -in "rb","rebuild-back" }  { Cmd-Rb }
    { $_ -in "rf","rebuild-front" } { Cmd-Rf }
    { $_ -in "ra","rebuild-all" }   { Cmd-Ra }
    "logs"                          { Cmd-Logs $SubCommand }
    { $_ -in "ps","status" }        { Cmd-Ps }
    "clean"                         { Cmd-Clean }
    "db"                            { Cmd-Db }
    "migrate"                       { Cmd-Migrate }
    "shell"                         { Cmd-Shell }
    { $_ -in "menu","help","" }     { Show-Menu }
    default {
        Write-Err "Noma'lum buyruq: '$Command'. Yordam uchun: .\dev.ps1"
    }
}
