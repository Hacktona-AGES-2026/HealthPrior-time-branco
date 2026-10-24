# Back-end do HealthPrior para deploy (Render, Fly, Railway...). O contexto de build é a RAIZ do repositório:
#   docker build -f backend/Dockerfile -t healthprior-api .
# O verificador oficial (src/) e o dataset (data/) vão junto: a publicação da fila roda o script oficial.
# score/references leva a tabela de IRR dos fatores do score (D-103); sem ela o score vira só o % do prazo.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 HP_USE_MOCKS=false

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend backend
COPY src src
COPY data data
COPY score/references score/references
RUN mkdir -p backend/output

WORKDIR /app/backend
EXPOSE 8000
# Banco vazio -> carga + primeira fila (idempotente: reiniciar não refaz nada); depois a API.
CMD ["sh", "-c", "python -m app.cli bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
