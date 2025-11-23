#!/usr/bin/env bash
set -e

STACK_NAME="api"
REPO_DIR="/opt/projeto_automacao"

echo "==> Atualizando código..."
cd $REPO_DIR
git pull

echo "==> Atualizando imagem..."
docker pull arthur433/leads-api:latest

echo "==> Subindo stack..."
docker stack deploy -c docker-compose.prod.yml $STACK_NAME

echo "✅ Deploy concluído."
