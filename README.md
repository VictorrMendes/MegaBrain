# KHONSHU — Assistente de IA Pessoal

Sistema operacional cognitivo local. Ver documentação completa em `HomeLab/projeto_IA/`.

## Início rápido

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com seus valores (SECRET_KEY, INFLUXDB_TOKEN)
```

### 2. Subir infraestrutura (desenvolvimento local)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Sobe: PostgreSQL + Redis + Ollama. API e Web rodam localmente.

### 3. Instalar dependências

```bash
# API
cd apps/api && uv sync

# Web
pnpm install
```

### 4. Rodar

```bash
# API (terminal 1)
cd apps/api && uv run fastapi dev main.py --port 8100

# Web (terminal 2)
pnpm --filter web dev
```

- Web: http://localhost:3100
- API: http://localhost:8100
- Docs: http://localhost:8100/docs

### 5. Baixar modelos Ollama

```bash
docker exec -it khonshu-ollama-1 ollama pull qwen3:8b
docker exec -it khonshu-ollama-1 ollama pull nomic-embed-text
```

## Deploy no servidor

```bash
# No servidor (após git pull)
cp .env.example .env  # editar com valores de produção
docker compose up --build -d
```

## Estrutura

```
kernel/     # Core: eventos, providers, permissões, cache
engines/    # Lógica de domínio: memória, RAG, agentes
apps/api/   # FastAPI — porta 8100
apps/web/   # Next.js — porta 3100
plugins/    # Integrações externas
```
