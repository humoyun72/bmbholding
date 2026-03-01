#!/bin/sh
# IntegrityBot uchun Vault'ni sozlash skripti
# Foydalanish: docker compose --profile vault up -d vault && sh scripts/vault_setup.sh

set -e

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"

echo "🔐 Vault sozlanmoqda: $VAULT_ADDR"

# KV v2 engine yoqish
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV engine allaqachon yoqilgan"

# IntegrityBot secretlarini yozish
# .env fayldan o'qib Vault ga yuklab qo'yish
vault kv put secret/integritybot \
  SECRET_KEY="${SECRET_KEY}" \
  ENCRYPTION_KEY="${ENCRYPTION_KEY}" \
  TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}" \
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  REDIS_PASSWORD="${REDIS_PASSWORD}" \
  SMTP_PASSWORD="${SMTP_PASSWORD}" \
  AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"

echo "✅ Secretlar Vault ga saqlandi: secret/integritybot"

# AppRole auth method yoqish (production uchun)
vault auth enable approle 2>/dev/null || echo "AppRole allaqachon yoqilgan"

# IntegrityBot uchun policy yaratish
vault policy write integritybot - <<EOF
path "secret/data/integritybot" {
  capabilities = ["read"]
}
path "secret/metadata/integritybot" {
  capabilities = ["read"]
}
EOF

# AppRole yaratish
vault write auth/approle/role/integritybot \
  secret_id_ttl=0 \
  token_ttl=1h \
  token_max_ttl=4h \
  policies=integritybot

# Role ID va Secret ID olish
echo ""
echo "📋 Backend uchun qo'yish kerak bo'lgan qiymatlar:"
echo "SECRETS_BACKEND=vault"
echo "VAULT_ADDR=$VAULT_ADDR"
echo "VAULT_ROLE_ID=$(vault read -field=role_id auth/approle/role/integritybot/role-id)"
echo "VAULT_SECRET_ID=$(vault write -f -field=secret_id auth/approle/role/integritybot/secret-id)"

