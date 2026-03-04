#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════╗
# ║          IntegrityBot — Tezkor Boshqaruv Skripti            ║
# ║                  Linux / macOS uchun                         ║
# ╚══════════════════════════════════════════════════════════════╝
#
# ISHLATISH:
#   ./dev.sh               → Menyuni ko'rsatadi
#   ./dev.sh up            → Barcha servislarni ishga tushirish
#   ./dev.sh down          → Barcha servislarni to'xtatish
#   ./dev.sh restart       → Barcha servislarni qayta ishga tushirish
#   ./dev.sh rb            → Faqat backend ni rebuild + restart
#   ./dev.sh rf            → Faqat frontend ni rebuild + restart
#   ./dev.sh ra            → Ikkalasini rebuild + restart
#   ./dev.sh logs          → Barcha loglar (real-time)
#   ./dev.sh logs b        → Faqat backend loglari
#   ./dev.sh logs f        → Faqat frontend loglari
#   ./dev.sh ps            → Servislar holati
#   ./dev.sh clean         → Keraksiz Docker narsalarni tozalash
#   ./dev.sh db            → DB ga kirish (psql)
#   ./dev.sh migrate       → Alembic migratsiyalarni bajarish
#   ./dev.sh shell         → Backend container ichiga kirish

set -e

# ─── Ranglar ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Yordamchi funksiyalar ──────────────────────────────────────
info()    { echo -e "${CYAN}ℹ ${NC}$1"; }
success() { echo -e "${GREEN}✅ ${NC}$1"; }
warning() { echo -e "${YELLOW}⚠ ${NC}$1"; }
error()   { echo -e "${RED}❌ ${NC}$1"; exit 1; }
step()    { echo -e "\n${BOLD}${BLUE}▶ $1${NC}"; }

# ─── Skript qayerda turganini aniqlash ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── .env tekshiruvi ────────────────────────────────────────────
check_env() {
  if [ ! -f ".env" ]; then
    warning ".env fayli topilmadi!"
    if [ -f ".env.example" ]; then
      read -r -p "  .env.example dan nusxa ko'chirilsinmi? [y/N] " ans
      if [[ "$ans" =~ ^[Yy]$ ]]; then
        cp .env.example .env
        success ".env yaratildi. Iltimos qiymatlarni to'ldiring."
        exit 0
      fi
    fi
    error ".env fayli kerak!"
  fi
}

# ─── Docker compose buyrug'i ─────────────────────────────────────
DC="docker compose"

# ─── Vaqt o'lchash ──────────────────────────────────────────────
timer_start() { START_TIME=$(date +%s); }
timer_end()   {
  END_TIME=$(date +%s)
  ELAPSED=$((END_TIME - START_TIME))
  echo -e "  ${CYAN}⏱  Vaqt: ${ELAPSED}s${NC}"
}

# ═══════════════════════════════════════════════════════════════
#  BUYRUQLAR
# ═══════════════════════════════════════════════════════════════

cmd_up() {
  check_env
  step "Barcha servislarni ishga tushirish..."
  timer_start
  $DC up -d --remove-orphans
  timer_end
  echo ""
  success "Barcha servislar ishga tushdi!"
  echo ""
  cmd_status_short
  echo ""
  echo -e "  ${CYAN}Frontend:${NC}  http://localhost:5173"
  echo -e "  ${CYAN}Backend:${NC}   http://localhost:8000"
  echo -e "  ${CYAN}API Docs:${NC}  http://localhost:8000/docs"
}

cmd_down() {
  step "Barcha servislarni to'xtatish..."
  $DC down
  success "To'xtatildi."
}

cmd_restart() {
  step "Barcha servislarni qayta ishga tushirish..."
  timer_start
  $DC restart
  timer_end
  success "Qayta ishga tushirildi."
  cmd_status_short
}

# ─── Backend rebuild ─────────────────────────────────────────────
cmd_rb() {
  check_env
  step "Backend rebuild va restart..."
  timer_start
  $DC build --no-cache backend
  $DC up -d --no-deps backend
  timer_end
  echo ""

  # Health check
  info "Backend health tekshirish..."
  sleep 3
  for i in {1..10}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
      success "Backend ishlayapti! (http://localhost:8000)"
      break
    fi
    if [ $i -eq 10 ]; then
      warning "Health check kelmadi. Loglarni tekshiring: ./dev.sh logs b"
    fi
    sleep 2
  done
}

# ─── Frontend rebuild ────────────────────────────────────────────
cmd_rf() {
  check_env
  step "Frontend rebuild va restart..."
  timer_start
  $DC build --no-cache frontend
  $DC up -d --no-deps frontend
  timer_end
  success "Frontend yangilandi! (http://localhost:5173)"
}

# ─── Ikkalasini rebuild ──────────────────────────────────────────
cmd_ra() {
  check_env
  step "Backend + Frontend rebuild va restart..."
  timer_start
  $DC build --no-cache backend frontend
  $DC up -d --no-deps backend frontend
  timer_end
  echo ""
  success "Ikkalasi yangilandi!"
  echo ""
  echo -e "  ${CYAN}Frontend:${NC}  http://localhost:5173"
  echo -e "  ${CYAN}Backend:${NC}   http://localhost:8000"
}

# ─── Loglar ─────────────────────────────────────────────────────
cmd_logs() {
  case "$1" in
    b|back|backend)   $DC logs -f --tail=100 backend ;;
    f|front|frontend) $DC logs -f --tail=100 frontend ;;
    d|db|database)    $DC logs -f --tail=100 db ;;
    r|redis)          $DC logs -f --tail=100 redis ;;
    *)                $DC logs -f --tail=50 ;;
  esac
}

# ─── Holat ──────────────────────────────────────────────────────
cmd_status_short() {
  echo -e "  ${BOLD}Servislar:${NC}"
  $DC ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null \
    | tail -n +2 \
    | while IFS= read -r line; do
        if echo "$line" | grep -q "Up\|running"; then
          echo -e "  ${GREEN}●${NC} $line"
        else
          echo -e "  ${RED}●${NC} $line"
        fi
      done
}

cmd_ps() {
  echo ""
  $DC ps
  echo ""
}

# ─── Tozalash ────────────────────────────────────────────────────
cmd_clean() {
  warning "Bu keraksiz Docker image, container va cache ni o'chiradi."
  read -r -p "  Davom etilsinmi? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    step "Tozalash..."
    docker system prune -f
    docker image prune -f
    success "Tozalandi!"
    docker system df
  fi
}

# ─── DB kirish ───────────────────────────────────────────────────
cmd_db() {
  DB_NAME=$(grep POSTGRES_DB .env 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "integritybot")
  DB_USER=$(grep POSTGRES_USER .env 2>/dev/null | cut -d= -f2 | tr -d '"' || echo "postgres")
  info "DB ga ulanish: $DB_NAME @ $DB_USER"
  $DC exec db psql -U "$DB_USER" -d "$DB_NAME"
}

# ─── Migratsiya ──────────────────────────────────────────────────
cmd_migrate() {
  step "Alembic migratsiyalarni bajarish..."
  $DC exec backend alembic upgrade head
  success "Migratsiyalar bajarildi."
}

# ─── Backend shell ───────────────────────────────────────────────
cmd_shell() {
  info "Backend container ichiga kirish..."
  $DC exec backend bash 2>/dev/null || $DC exec backend sh
}

# ─── Menyu ──────────────────────────────────────────────────────
show_menu() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║       IntegrityBot — Boshqaruv Skripti      ║${NC}"
  echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${BOLD}ASOSIY:${NC}"
  echo -e "  ${GREEN}up${NC}           Barcha servislarni ishga tushirish"
  echo -e "  ${GREEN}down${NC}         Barcha servislarni to'xtatish"
  echo -e "  ${GREEN}restart${NC}      Barcha servislarni qayta ishga tushirish"
  echo ""
  echo -e "  ${BOLD}REBUILD (tezkor):${NC}"
  echo -e "  ${YELLOW}rb${NC}           Faqat backend  → rebuild + restart"
  echo -e "  ${YELLOW}rf${NC}           Faqat frontend → rebuild + restart"
  echo -e "  ${YELLOW}ra${NC}           Ikkalasi       → rebuild + restart"
  echo ""
  echo -e "  ${BOLD}MONITORING:${NC}"
  echo -e "  ${CYAN}logs${NC}         Barcha loglar (real-time)"
  echo -e "  ${CYAN}logs b${NC}       Faqat backend loglari"
  echo -e "  ${CYAN}logs f${NC}       Faqat frontend loglari"
  echo -e "  ${CYAN}logs d${NC}       Faqat DB loglari"
  echo -e "  ${CYAN}ps${NC}           Servislar holati"
  echo ""
  echo -e "  ${BOLD}BOSHQA:${NC}"
  echo -e "  ${BLUE}db${NC}           PostgreSQL ga kirish"
  echo -e "  ${BLUE}migrate${NC}      Alembic migratsiyalar"
  echo -e "  ${BLUE}shell${NC}        Backend container ichiga kirish"
  echo -e "  ${BLUE}clean${NC}        Docker cache ni tozalash"
  echo ""
  echo -e "  ${BOLD}MISOL:${NC}"
  echo -e "  ${NC}./dev.sh rb    # Backend kodi o'zgarganda"
  echo -e "  ${NC}./dev.sh ra    # Ikkalasini yangilash"
  echo ""
}

# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════
case "${1:-menu}" in
  up)              cmd_up ;;
  down)            cmd_down ;;
  restart)         cmd_restart ;;
  rb|rebuild-back) cmd_rb ;;
  rf|rebuild-front)cmd_rf ;;
  ra|rebuild-all)  cmd_ra ;;
  logs)            cmd_logs "$2" ;;
  ps|status)       cmd_ps ;;
  clean)           cmd_clean ;;
  db)              cmd_db ;;
  migrate)         cmd_migrate ;;
  shell)           cmd_shell ;;
  menu|help|"")    show_menu ;;
  *)
    error "Noma'lum buyruq: '$1'. Yordam uchun: ./dev.sh"
    ;;
esac
