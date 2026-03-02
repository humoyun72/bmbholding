#!/bin/bash
# =============================================================================
#  IntegrityBot — Loyihani boshqarish skripti (Linux/macOS)
#  Ishlatish: ./manage.sh <buyruq> [--service <servis>]
# =============================================================================

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Ranglar
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; WHITE='\033[1;37m'; NC='\033[0m'

info()    { echo -e "${CYAN}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()     { echo -e "${RED}❌ $1${NC}"; }
header()  { echo -e "\n${CYAN}═══════════════════════════════════════════\n  $1\n═══════════════════════════════════════════${NC}"; }

COMMAND="${1:-help}"
SERVICE=""
CLEAN=false

# Parametrlarni parse qilish
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --service|-s) SERVICE="$2"; shift 2 ;;
        --clean|-c)   CLEAN=true; shift ;;
        *) shift ;;
    esac
done

# ── YORDAMCHI FUNKSIYALAR ─────────────────────────────────────────────────────

check_docker() {
    if ! docker info &>/dev/null; then
        err "Docker ishlamayapti! Docker ni ishga tushiring."
        exit 1
    fi
}

check_env() {
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        warning ".env fayli topilmadi. .env.example dan nusxa olinmoqda..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        warning ".env faylini to'ldirishni unutmang!"
        return 1
    fi

    local issues=()
    grep -q "POSTGRES_PASSWORD=CHANGE_ME" .env && issues+=("POSTGRES_PASSWORD")
    grep -q "SECRET_KEY=CHANGE_ME" .env && issues+=("SECRET_KEY")
    grep -qP "TELEGRAM_BOT_TOKEN=\d+:" .env || issues+=("TELEGRAM_BOT_TOKEN")

    if [[ ${#issues[@]} -gt 0 ]]; then
        warning "Quyidagi .env o'zgaruvchilari to'ldirilmagan:"
        for issue in "${issues[@]}"; do
            echo -e "   ${YELLOW}⚠️  $issue${NC}"
        done
        return 1
    fi
    return 0
}

# ── BUYRUQLAR ─────────────────────────────────────────────────────────────────

cmd_up() {
    header "IntegrityBot — Ishga tushirish (Development)"
    check_docker

    if ! check_env; then
        read -p "Muammolar bor. Davom etish? (y/N): " confirm
        [[ "$confirm" != "y" && "$confirm" != "Y" ]] && return
    fi

    info "Servislar ishga tushirilmoqda (backend, frontend, db, redis)..."
    docker-compose up -d --build

    success "Servislar muvaffaqiyatli ishga tushdi!"
    echo ""
    echo -e "  ${GREEN}🌐 Frontend:    http://localhost:5173${NC}"
    echo -e "  ${GREEN}🔧 Backend API: http://localhost:8000${NC}"
    echo -e "  ${GREEN}📚 API Docs:    http://localhost:8000/docs${NC}"
    echo -e "  ${GREEN}🗄️  DB Port:     localhost:5432${NC}"
    echo ""
    info "Loglarni ko'rish: ./manage.sh logs"
    info "To'xtatish:       ./manage.sh down"
}

cmd_down() {
    header "IntegrityBot — Servislarni to'xtatish"
    check_docker

    if [[ "$CLEAN" == "true" ]]; then
        warning "Volumelar ham o'chiriladi!"
        read -p "Davom etish? (y/N): " confirm
        [[ "$confirm" != "y" && "$confirm" != "Y" ]] && return
        docker-compose down -v --remove-orphans
    else
        docker-compose down --remove-orphans
    fi

    success "Servislar to'xtatildi!"
}

cmd_restart() {
    header "IntegrityBot — Qayta ishga tushirish"
    check_docker

    if [[ -n "$SERVICE" ]]; then
        info "Servis qayta ishga tushirilmoqda: $SERVICE"
        docker-compose restart "$SERVICE"
    else
        docker-compose restart
    fi
    success "Qayta ishga tushirildi!"
}

cmd_build() {
    header "IntegrityBot — Image build"
    check_docker
    info "Imagelar qayta build qilinmoqda (cache o'chirilgan)..."
    docker-compose build --no-cache
    success "Build muvaffaqiyatli!"
}

cmd_logs() {
    header "IntegrityBot — Loglar"
    check_docker

    if [[ -n "$SERVICE" ]]; then
        info "Servis loglari: $SERVICE"
        docker-compose logs --tail=100 -f "$SERVICE"
    else
        info "Barcha servislar loglari"
        docker-compose logs --tail=50 -f
    fi
}

cmd_status() {
    header "IntegrityBot — Konteynerlar holati"
    check_docker
    docker-compose ps
    echo ""
    info "CPU va Xotira:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
}

cmd_shell() {
    header "IntegrityBot — Shell"
    check_docker
    local svc="${SERVICE:-backend}"
    info "Konteynerga ulanilmoqda: $svc"
    docker-compose exec "$svc" /bin/bash
}

cmd_migrate() {
    header "IntegrityBot — DB Migratsiya"
    check_docker
    info "Migratsiyalar qo'llanilmoqda..."
    docker-compose exec backend alembic upgrade head
    success "Migratsiyalar muvaffaqiyatli qo'llandi!"
}

cmd_test() {
    header "IntegrityBot — Testlar"
    check_docker
    info "Testlar ishga tushirilmoqda..."
    docker-compose exec backend python -m pytest tests/ -v --tb=short
}

cmd_prod() {
    header "IntegrityBot — Production rejimi"
    check_docker

    if ! check_env; then
        err "Production uchun .env to'liq to'ldirilishi shart!"
        exit 1
    fi

    info "Production servislar ishga tushirilmoqda..."
    docker-compose \
        -f docker-compose.yml \
        -f docker-compose.prod.yml \
        --profile production \
        up -d --build

    success "Production servislar ishga tushdi!"
    echo ""
    echo -e "  ${GREEN}🌐 Web: http://localhost (nginx orqali)${NC}"
    warning "SSL sertifikatlari: ./nginx/certs/ papkasida bo'lishi kerak"
}

cmd_monitoring() {
    header "IntegrityBot — Monitoring"
    check_docker
    docker-compose --profile monitoring up -d
    success "Monitoring ishga tushdi!"
    echo ""
    echo -e "  ${GREEN}📊 Prometheus: http://localhost:9090${NC}"
    echo -e "  ${GREEN}📈 Grafana:    http://localhost:3000${NC}"
}

cmd_clean() {
    header "IntegrityBot — To'liq tozalash"
    warning "DIQQAT! Barcha ma'lumotlar o'chiriladi!"

    read -p "Haqiqatan ham tozalashni xohlaysizmi? (yes/NO): " confirm
    [[ "$confirm" != "yes" ]] && { info "Bekor qilindi."; return; }

    docker-compose down -v --remove-orphans --rmi local
    success "Tozalash yakunlandi!"
}

cmd_help() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║         IntegrityBot — Boshqaruv Skripti             ║${NC}"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  ASOSIY BUYRUQLAR:                                    ║${NC}"
    echo -e "║    up                  Dev rejimda ishga tushirish    ║"
    echo -e "║    down                Servislarni to'xtatish         ║"
    echo -e "║    down --clean        Volume bilan to'xtatish        ║"
    echo -e "║    restart             Qayta ishga tushirish          ║"
    echo -e "║    build               Imagelarni rebuild             ║"
    echo -e "║    status              Holat va resurslar             ║"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  LOG VA DEBUG:                                        ║${NC}"
    echo -e "║    logs                   Barcha loglar               ║"
    echo -e "║    logs --service backend Backend loglari             ║"
    echo -e "║    shell                  Backend shelliga kirish     ║"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  MA'LUMOTLAR:                                         ║${NC}"
    echo -e "║    migrate             DB migratsiyalarni qo'llash   ║"
    echo -e "║    test                Barcha testlarni ishga tushir ║"
    echo -e "${CYAN}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  PRODUCTION:                                          ║${NC}"
    echo -e "║    prod                Production rejimi              ║"
    echo -e "║    monitoring          Prometheus + Grafana           ║"
    echo -e "${RED}╠═══════════════════════════════════════════════════════╣${NC}"
    echo -e "${RED}║    clean               Barcha ma'lumotlarni o'chir ⚠️  ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ── DISPATCHER ────────────────────────────────────────────────────────────────
case "$COMMAND" in
    up)          cmd_up ;;
    down)        cmd_down ;;
    restart)     cmd_restart ;;
    build)       cmd_build ;;
    logs)        cmd_logs ;;
    status|ps)   cmd_status ;;
    shell|exec)  cmd_shell ;;
    migrate)     cmd_migrate ;;
    test)        cmd_test ;;
    prod|production) cmd_prod ;;
    monitoring)  cmd_monitoring ;;
    clean)       cmd_clean ;;
    help|*)      cmd_help ;;
esac

