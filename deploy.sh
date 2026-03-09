#!/usr/bin/env bash
# =============================================================
#  IntegrityBot — Shared Hosting (VPS) deployment skripti
#
#  Ishlatish:
#    chmod +x deploy.sh
#    ./deploy.sh yourdomain.com admin@yourdomain.com
#
#  Talablar:
#    - Ubuntu 22.04 / Debian 12 VPS
#    - Root yoki sudo huquqi
#    - Domain DNS A-yozuvi serverga ko'rsatilgan bo'lishi kerak
# =============================================================

set -euo pipefail

# ── Argumentlarni tekshirish ──────────────────────────────────
DOMAIN="${1:-}"
EMAIL="${2:-}"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
    echo "Ishlatish: $0 yourdomain.com admin@yourdomain.com"
    exit 1
fi

WEBHOOK_URL="https://${DOMAIN}/api/telegram/webhook"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${PROJECT_DIR}/nginx/certs"

echo ""
echo "=================================================="
echo "  IntegrityBot deployment"
echo "  Domain:  ${DOMAIN}"
echo "  Email:   ${EMAIL}"
echo "  Webhook: ${WEBHOOK_URL}"
echo "=================================================="
echo ""

# ── 1. Docker o'rnatish ───────────────────────────────────────
install_docker() {
    echo "[1/7] Docker tekshirilmoqda..."
    if command -v docker &>/dev/null; then
        echo "      Docker allaqachon o'rnatilgan: $(docker --version)"
        return
    fi
    echo "      Docker o'rnatilmoqda..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    # Joriy foydalanuvchini docker guruhiga qo'shish
    usermod -aG docker "$USER" 2>/dev/null || true
    echo "      Docker o'rnatildi ✅"
}

# ── 2. Docker Compose v2 tekshirish ──────────────────────────
install_compose() {
    echo "[2/7] Docker Compose tekshirilmoqda..."
    if docker compose version &>/dev/null; then
        echo "      Docker Compose allaqachon mavjud ✅"
        return
    fi
    echo "      Docker Compose plugin o'rnatilmoqda..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    COMPOSE_VER="v2.27.1"
    ARCH=$(uname -m | sed 's/x86_64/x86_64/' | sed 's/aarch64/aarch64/')
    curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-linux-${ARCH}" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    echo "      Docker Compose o'rnatildi ✅"
}

# ── 3. .env fayl tekshirish / yaratish ────────────────────────
setup_env() {
    echo "[3/7] .env fayl tekshirilmoqda..."
    if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
        if [[ ! -f "${PROJECT_DIR}/.env.example" ]]; then
            echo "      XATO: .env.example topilmadi!"
            exit 1
        fi
        cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
        echo ""
        echo "  ⚠️  .env fayl .env.example dan nusxalandi."
        echo "  Iltimos, .env faylini to'ldiring va skriptni qayta ishga tushiring:"
        echo ""
        echo "    nano ${PROJECT_DIR}/.env"
        echo ""
        echo "  Minimal talab qilinadigan sozlamalar:"
        echo "    TELEGRAM_BOT_TOKEN=  ← BotFather dan oling"
        echo "    POSTGRES_PASSWORD=   ← kuchli parol"
        echo "    REDIS_PASSWORD=      ← kuchli parol"
        echo "    SECRET_KEY=          ← 64+ belgili random string"
        echo "    ENCRYPTION_KEY=      ← base64 encoded 32 byte"
        echo "    ADMIN_DEFAULT_PASSWORD= ← kuchli parol"
        echo "    ADMIN_CHAT_ID=       ← Telegram guruh ID (-100...)"
        echo "    SMTP_*               ← email sozlamalari (ixtiyoriy)"
        echo ""
        exit 0
    fi

    # .env fayldagi WEBHOOK_URL va BOT_MODE ni yangilash
    echo "      .env ga WEBHOOK_URL va BOT_MODE yozilmoqda..."

    # sed bilan mavjud qiymatni almashtirish (yoki qo'shish)
    if grep -q "^WEBHOOK_URL=" "${PROJECT_DIR}/.env"; then
        sed -i "s|^WEBHOOK_URL=.*|WEBHOOK_URL=${WEBHOOK_URL}|" "${PROJECT_DIR}/.env"
    else
        echo "WEBHOOK_URL=${WEBHOOK_URL}" >> "${PROJECT_DIR}/.env"
    fi

    if grep -q "^BOT_MODE=" "${PROJECT_DIR}/.env"; then
        sed -i "s|^BOT_MODE=.*|BOT_MODE=webhook|" "${PROJECT_DIR}/.env"
    else
        echo "BOT_MODE=webhook" >> "${PROJECT_DIR}/.env"
    fi

    if grep -q "^FRONTEND_URL=" "${PROJECT_DIR}/.env"; then
        sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=https://${DOMAIN}|" "${PROJECT_DIR}/.env"
    else
        echo "FRONTEND_URL=https://${DOMAIN}" >> "${PROJECT_DIR}/.env"
    fi

    if grep -q "^ALLOWED_ORIGINS=" "${PROJECT_DIR}/.env"; then
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://${DOMAIN}|" "${PROJECT_DIR}/.env"
    else
        echo "ALLOWED_ORIGINS=https://${DOMAIN}" >> "${PROJECT_DIR}/.env"
    fi

    if grep -q "^VITE_API_URL=" "${PROJECT_DIR}/.env"; then
        sed -i "s|^VITE_API_URL=.*|VITE_API_URL=https://${DOMAIN}/api|" "${PROJECT_DIR}/.env"
    else
        echo "VITE_API_URL=https://${DOMAIN}/api" >> "${PROJECT_DIR}/.env"
    fi

    echo "      .env yangilandi ✅"
}

# ── 4. SSL sertifikat olish (Let's Encrypt) ──────────────────
setup_ssl() {
    echo "[4/7] SSL sertifikat tekshirilmoqda..."
    mkdir -p "${CERTS_DIR}"
    mkdir -p "${PROJECT_DIR}/nginx/certbot-webroot"

    if [[ -f "${CERTS_DIR}/fullchain.pem" ]] && [[ -f "${CERTS_DIR}/privkey.pem" ]]; then
        echo "      Sertifikat allaqachon mavjud ✅"
        return
    fi

    # Certbot o'rnatish
    if ! command -v certbot &>/dev/null; then
        echo "      Certbot o'rnatilmoqda..."
        apt-get update -qq
        apt-get install -y -qq certbot
    fi

    # 80-port band emasligini tekshirish
    if ss -tlnp | grep -q ':80 '; then
        echo "      80-port band — nginx/apache to'xtatilmoqda..."
        systemctl stop nginx apache2 2>/dev/null || true
        # Docker nginx ham to'xtatamiz
        cd "${PROJECT_DIR}"
        docker compose stop nginx 2>/dev/null || true
    fi

    echo "      Let's Encrypt sertifikat so'ralmoqda..."
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "${EMAIL}" \
        -d "${DOMAIN}" \
        --http-01-port 80

    # Sertifikatlarni nginx/certs/ ga nusxalash
    echo "      Sertifikatlar nginx/certs/ ga ko'chirilmoqda..."
    cp "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${CERTS_DIR}/fullchain.pem"
    cp "/etc/letsencrypt/live/${DOMAIN}/privkey.pem"   "${CERTS_DIR}/privkey.pem"
    chmod 644 "${CERTS_DIR}/fullchain.pem"
    chmod 600 "${CERTS_DIR}/privkey.pem"

    echo "      SSL sertifikat olindi ✅"

    # Avtomatik yangilash uchun cron qo'shish
    setup_ssl_renewal
}

# ── SSL sertifikatni avtomatik yangilash ──────────────────────
setup_ssl_renewal() {
    echo "      SSL avtomatik yangilash cron qo'shilmoqda..."
    RENEW_SCRIPT="${PROJECT_DIR}/renew-ssl.sh"
    cat > "${RENEW_SCRIPT}" << RENEW_EOF
#!/usr/bin/env bash
# SSL sertifikatni yangilash va nginx konteynerini qayta yuklash
set -e
DOMAIN="${DOMAIN}"
CERTS_DIR="${CERTS_DIR}"
PROJECT_DIR="${PROJECT_DIR}"

# Nginx to'xtatish → certbot → qayta boshlash
cd "\${PROJECT_DIR}"
docker compose stop nginx
certbot renew --standalone --http-01-port 80 --quiet
cp "/etc/letsencrypt/live/\${DOMAIN}/fullchain.pem" "\${CERTS_DIR}/fullchain.pem"
cp "/etc/letsencrypt/live/\${DOMAIN}/privkey.pem"   "\${CERTS_DIR}/privkey.pem"
chmod 644 "\${CERTS_DIR}/fullchain.pem"
chmod 600 "\${CERTS_DIR}/privkey.pem"
docker compose --profile production start nginx
echo "\$(date): SSL yangilandi ✅"
RENEW_EOF
    chmod +x "${RENEW_SCRIPT}"

    # Har 2 oyda bir yangilash (Let's Encrypt 90 kunda eskiradi)
    CRON_LINE="0 3 1 */2 * ${RENEW_SCRIPT} >> /var/log/ssl-renewal.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "renew-ssl.sh"; echo "${CRON_LINE}") | crontab -
    echo "      Cron qo'shildi (har 2 oyda bir, 03:00 da) ✅"
}

# ── 5. Docker image larni build qilish ────────────────────────
build_images() {
    echo "[5/7] Docker imagelar build qilinmoqda..."
    cd "${PROJECT_DIR}"
    docker compose --profile production build --no-cache
    echo "      Build tugadi ✅"
}

# ── 6. Konteynerlarni ishga tushirish ─────────────────────────
start_services() {
    echo "[6/7] Servislar ishga tushirilmoqda..."
    cd "${PROJECT_DIR}"

    # Mavjud konteynerlarni to'xtatish
    docker compose --profile production down 2>/dev/null || true

    # Yangi versiyani boshlash
    docker compose --profile production up -d

    # Backend tayyor bo'lishini kutish
    echo "      Backend ishga tushishini kutilmoqda..."
    for i in $(seq 1 30); do
        if docker compose exec -T backend \
            curl -sf http://localhost:8000/api/health &>/dev/null; then
            echo "      Backend tayyor ✅"
            break
        fi
        if [[ $i -eq 30 ]]; then
            echo "      ⚠️  Backend 30 soniyada ishga tushmadi."
            echo "      Loglarni tekshiring: docker compose logs backend"
        fi
        sleep 1
    done
}

# ── 7. Telegram Webhook ro'yxatdan o'tkazish ──────────────────
register_webhook() {
    echo "[7/7] Telegram Webhook ro'yxatdan o'tirilmoqda..."

    # .env dan BOT_TOKEN ni o'qish
    BOT_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" "${PROJECT_DIR}/.env" | cut -d= -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
    WEBHOOK_SECRET=$(grep "^WEBHOOK_SECRET=" "${PROJECT_DIR}/.env" | cut -d= -f2 | tr -d '"' | tr -d "'" | tr -d ' ')

    if [[ -z "$BOT_TOKEN" || "$BOT_TOKEN" == "YOUR_BOT_TOKEN_FROM_BOTFATHER" ]]; then
        echo ""
        echo "  ⚠️  TELEGRAM_BOT_TOKEN .env faylida to'ldirilmagan!"
        echo "  Webhookni qo'lda ro'yxatdan o'tkazing:"
        echo ""
        echo "    curl -X POST \"https://api.telegram.org/bot<TOKEN>/setWebhook\" \\"
        echo "         -d \"url=${WEBHOOK_URL}\" \\"
        echo "         -d \"secret_token=<WEBHOOK_SECRET>\""
        echo ""
        return
    fi

    # Webhook o'rnatish
    RESPONSE=$(curl -sf \
        -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
        -d "url=${WEBHOOK_URL}" \
        -d "secret_token=${WEBHOOK_SECRET}" \
        -d "allowed_updates=[\"message\",\"callback_query\",\"edited_message\",\"poll_answer\",\"poll\"]" \
        2>&1 || echo "CURL_ERROR")

    if echo "${RESPONSE}" | grep -q '"ok":true'; then
        echo "      Webhook ro'yxatdan o'tdi ✅"
        echo "      URL: ${WEBHOOK_URL}"
    else
        echo "      ⚠️  Webhook o'rnatishda xato:"
        echo "      ${RESPONSE}"
        echo ""
        echo "  Qo'lda o'rnatish:"
        echo "    curl -X POST \"https://api.telegram.org/bot${BOT_TOKEN}/setWebhook\" \\"
        echo "         -d \"url=${WEBHOOK_URL}\" \\"
        echo "         -d \"secret_token=${WEBHOOK_SECRET}\""
    fi
}

# ── Asosiy bajarilish tartibi ─────────────────────────────────
main() {
    install_docker
    install_compose
    setup_env
    setup_ssl
    build_images
    start_services
    register_webhook

    echo ""
    echo "=================================================="
    echo "  Deployment muvaffaqiyatli yakunlandi! 🎉"
    echo ""
    echo "  Admin panel:  https://${DOMAIN}"
    echo "  API docs:     https://${DOMAIN}/api/docs"
    echo "  Bot webhook:  ${WEBHOOK_URL}"
    echo ""
    echo "  Loglarni ko'rish:"
    echo "    docker compose logs -f backend"
    echo "    docker compose logs -f nginx"
    echo ""
    echo "  Servislar holati:"
    echo "    docker compose ps"
    echo "=================================================="
}

main
