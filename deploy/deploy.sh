#!/usr/bin/env bash
# Deploy amc-agno to VPS side-by-side with old lucas-amc.
# Usage: VPS_PASS='...' ./deploy/deploy.sh
set -euo pipefail

VPS_HOST="${VPS_HOST:-root@72.60.137.105}"
REMOTE_BASE="/opt/amc-agno"
LOG_DIR="/var/log/amc-agno"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"

if [[ -z "${VPS_PASS:-}" ]]; then
  echo "VPS_PASS env var required" >&2
  exit 1
fi

run() { sshpass -p "$VPS_PASS" ssh $SSH_OPTS "$VPS_HOST" "$@"; }
copy() { sshpass -p "$VPS_PASS" scp $SSH_OPTS "$@"; }

echo "==> Garantindo estrutura remota"
run "id amcagent >/dev/null 2>&1 || useradd -r -m -s /usr/sbin/nologin amcagent
mkdir -p $REMOTE_BASE/current $REMOTE_BASE/shared/data $LOG_DIR
chown -R amcagent:amcagent $REMOTE_BASE $LOG_DIR"

echo "==> Enviando código (sem venv/data/backups/logs)"
sshpass -p "$VPS_PASS" rsync -az --delete \
  --exclude '.venv' --exclude 'venv' --exclude '__pycache__' \
  --exclude '.git' --exclude 'backups' --exclude 'data' \
  --exclude 'logs' --exclude '*.log' --exclude 'tmp' \
  --exclude 'sandbox' --exclude 'scratch' \
  -e "ssh $SSH_OPTS" \
  ./ "$VPS_HOST:$REMOTE_BASE/current/"

echo "==> Enviando .env"
copy .env "$VPS_HOST:$REMOTE_BASE/shared/.env"

echo "==> Symlink data persistente"
run "ln -sfn $REMOTE_BASE/shared/data $REMOTE_BASE/current/data
chown -R amcagent:amcagent $REMOTE_BASE"

echo "==> Criando/atualizando venv + deps"
run "test -d $REMOTE_BASE/shared/.venv || python3 -m venv $REMOTE_BASE/shared/.venv
$REMOTE_BASE/shared/.venv/bin/pip install --upgrade pip
$REMOTE_BASE/shared/.venv/bin/pip install -r $REMOTE_BASE/current/requirements.txt
chown -R amcagent:amcagent $REMOTE_BASE/shared/.venv"

echo "==> Instalando systemd unit"
copy deploy/amc-agno.service "$VPS_HOST:/etc/systemd/system/amc-agno.service"
run "systemctl daemon-reload && systemctl enable amc-agno.service && systemctl restart amc-agno.service"

echo "==> Status"
run "sleep 2 && systemctl --no-pager status amc-agno.service | head -20"
run "curl -sS http://127.0.0.1:8322/health || true"

echo "Done. Próximo: trocar nginx 8321 -> 8322 e parar lucas-amc."
