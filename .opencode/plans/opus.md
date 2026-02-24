# OPUS — Plano Mestre do Projeto 2 CEREBRO

**Autor**: Dev Senior (Lead)
**Data**: 2026-02-24
**Versao**: 1.0
**Status**: Em execucao — Fase 0 CONCLUIDA em 2026-02-24

---

## 1. VISAO GERAL

O 2 Cerebro e um sistema de segundo cerebro digital que transforma prints de tela
(Twitter, Instagram, GitHub, sites) em conhecimento estruturado, conectado e acionavel.

**Objetivo final**: Plataforma profissional que ingere imagens automaticamente,
extrai texto via OCR, gera embeddings semanticos, detecta padroes/gargalos,
sugere postagens para redes sociais e gera insights via LLM — funcionando
em producao pessoal agora, com arquitetura preparada para multi-usuario no futuro.

---

## 2. DIAGNOSTICO HONESTO DO ESTADO ATUAL

### 2.1 Hardware Confirmado

| Componente | Especificacao | Status |
|---|---|---|
| CPU | Intel Core i7-3770 @ 3.40GHz (4c/8t) | Funcional |
| RAM | 16GB DDR3 (9.5GB disponiveis) | Justo |
| Disco | SSD 219GB (119GB livres) | OK |
| GPU | Nenhuma | Limitante para LLM |
| SO | Linux Ubuntu | Ideal |

### 2.2 Software Confirmado

| Software | Versao | Status |
|---|---|---|
| Python | 3.12.3 | OK |
| Tesseract | 5.3.4 (AVX, SSE4.1, OpenMP) | OK |
| Ollama | Instalado | OK |
| qwen2.5:7b | 4.7GB | Disponivel |
| llava:7b | 4.7GB | Disponivel |
| all-MiniLM-L6-v2 | models/ local | Baixado |
| Flask | 3.1.3 | Instalado |
| numpy | 2.4.2 | Instalado |
| pillow | 10.2.0 | Instalado |
| pytesseract | 0.3.13 | Instalado |

### 2.3 PROBLEMAS CRITICOS (Divida Tecnica)

**P01 — sentence-transformers e chromadb NAO INSTALADOS**
O `pip list` nao mostra nenhum dos dois. O codigo faz `try/except` e
silenciosamente desabilita tudo. Todo o pipeline semantico esta INATIVO.
Embeddings funcionam apenas por TF-IDF/SVD (fallback basico).

**P02 — langwatch como dependencia fantasma**
Importado em `chroma_store.py` e nos testes com decorador `@trace`.
Nao aparece no pip list. Adiciona overhead e pode causar ImportError.

**P03 — app.py monolitico (954 linhas)**
Mistura rotas HTTP, logica de negocio, helpers de texto, chamadas LLM,
funcoes de rebuild de embeddings. Impossivel testar unitariamente.

**P04 — Frontend monolitico e amador**
- `app.js`: 1263 linhas sem modularizacao
- `style.css`: 1144 linhas com duplicacoes
- Codigo morto (funcoes PaddleOCR que nao existe mais)
- Sem componentizacao, sem framework, sem build pipeline
- Funcoes como `alert()` para feedback (nao profissional)
- Grafos D3.js basicos sem interatividade real

**P05 — Sem requirements.txt**
Nenhum arquivo de dependencias. Impossivel reproduzir o ambiente.

**P06 — Database sem connection pooling**
Cada chamada abre/fecha conexao SQLite. Em requests concorrentes,
gera `database is locked`.

**P07 — Zero autenticacao**
Qualquer dispositivo na rede acessa todos os endpoints.
Dados pessoais (prints, textos) expostos.

**P08 — Debug mode em producao**
`app.run(debug=True)` no `app.py:954`. Auto-reload ativo, stack traces
expostos, hot-reload consome CPU desnecessariamente.

**P09 — .gitignore incompleto**
Falta: `chroma_data/`, `models/`, `.venv/`, `*.db`, `server.log`,
`flask.log`, `diagnostico_chroma_out.json`.

**P10 — Zero logging estruturado**
Tudo via `print()`. Sem rotacao, sem niveis, sem arquivo de log organizado.

**P11 — Regex de data quebrado em file_manager.py**
`_extrair_data()` usa `\\\\d` (escaped duplo em string normal).
Nenhum regex funciona. Todas as fotos caem no fallback de data.

**P12 — Sem testes de integracao**
Apenas 4 testes basicos. Nenhum teste de API, nenhum teste end-to-end.

**P13 — Busca textual com SQL LIKE**
`WHERE ocr_limpo LIKE ?` e O(n) full table scan. Com 10k+ fotos, vai travar.

**P14 — Sync de fotos a cada 20s sem watchdog**
Loop infinito com `time.sleep(20)` que escaneia toda a pasta.
Ineficiente para pastas grandes.

### 2.4 O QUE FUNCIONA BEM (Preservar)

- Pipeline OCR basico (Tesseract com pre-processamento adaptativo)
- Extracao de @usuarios e repos GitHub
- Deduplicacao por hash MD5
- Renomeacao automatica com data
- Estrutura de banco SQLite com tabelas coerentes
- WAL mode e indices no SQLite
- Dossiee por termo com coocorrencias, timeline e ancoras
- Integracao basica com LLM (Ollama, Gemini, Groq, Mistral)
- Tema claro/escuro funcional

---

## 3. DECISOES DE ARQUITETURA

| Decisao | Escolha | Justificativa |
|---|---|---|
| Backend | FastAPI | Async nativo, melhor para OCR/LLM pesado, Pydantic nativo, OpenAPI auto |
| Frontend | React (Vite) | Componentizado, build otimizado, ecosystem maduro, TypeScript |
| LLM Local | Ollama (qwen2.5:7b) | Ja instalado, qualidade boa para sinteses |
| LLM API Gratis | Groq + Gemini + Ollama | Fallback automatico entre os tres |
| Embeddings | all-MiniLM-L6-v2 local | Ja baixado, 384 dim, rapido na CPU |
| Vector Store | ChromaDB | Persistente, HNSW cosine, sem servidor extra |
| Banco Relacional | SQLite (WAL) -> futuro PostgreSQL | Funciona agora, migra quando escalar |
| Sync Celular | Syncthing | Sem servidor, P2P, criptografado, gratis |
| Grafos Frontend | D3.js + Force Graph | Ja tem base, interativo, sem dependencia extra |

---

## 4. ARQUITETURA ALVO

### 4.1 Estrutura de Pastas

```
leitorcontextofoto/
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, startup, shutdown
│   ├── config.py                  # Settings com Pydantic BaseSettings
│   ├── dependencies.py            # Injecao de dependencia (DB, services)
│   │
│   ├── api/                       # Rotas organizadas por dominio
│   │   ├── __init__.py
│   │   ├── router.py              # Monta todos os routers
│   │   ├── fotos.py               # CRUD fotos, upload, imagem
│   │   ├── ocr.py                 # Extrair, salvar, comparar
│   │   ├── busca.py               # Textual e semantica
│   │   ├── embeddings.py          # Rebuild, similares
│   │   ├── insights.py            # Dossie, clusters, grafo, timeline
│   │   ├── llm.py                 # Analisar com LLM, gerar post
│   │   ├── cerebro.py             # Cerebro 1 (enriquecimento) e 2 (geracao)
│   │   └── health.py              # /health, /status, /metrics
│   │
│   ├── services/                  # Logica de negocio (sem HTTP)
│   │   ├── __init__.py
│   │   ├── ocr_service.py         # Tesseract + pre-processamento
│   │   ├── embedding_service.py   # all-MiniLM-L6-v2 + ChromaDB
│   │   ├── llm_service.py         # Ollama / Groq / Gemini com fallback
│   │   ├── cerebro1_service.py    # Classificacao automatica pos-OCR
│   │   ├── cerebro2_service.py    # Insights, gargalos, sugestoes de post
│   │   ├── file_service.py        # Sync, rename, upload, dedup
│   │   ├── search_service.py      # Busca textual + semantica unificada
│   │   └── graph_service.py       # Grafo de conhecimento, clusters
│   │
│   ├── db/                        # Camada de dados
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite com connection pool (aiosqlite)
│   │   ├── models.py              # Schemas Pydantic (request/response)
│   │   ├── repositories.py        # CRUD puro (fotos, palavras, usuarios, etc.)
│   │   └── migrations.py          # Versionamento de schema
│   │
│   ├── stores/                    # Armazenamentos especializados
│   │   ├── __init__.py
│   │   └── chroma_store.py        # ChromaDB wrapper
│   │
│   └── utils/                     # Utilitarios
│       ├── __init__.py
│       ├── logger.py              # Logging estruturado (JSON, rotacao)
│       ├── security.py            # Auth basica, CORS, rate limiting
│       └── performance.py         # Cache, batch processing, profiling
│
├── frontend/                      # React (Vite + TypeScript)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                   # Chamadas HTTP tipadas
│   │   │   └── client.ts
│   │   ├── components/            # Componentes reutilizaveis
│   │   │   ├── Header.tsx
│   │   │   ├── PhotoDrop.tsx
│   │   │   ├── OcrWorkspace.tsx
│   │   │   ├── Gallery.tsx
│   │   │   ├── BrainMap.tsx       # Word cloud
│   │   │   ├── Timeline.tsx
│   │   │   ├── ClusterView.tsx
│   │   │   ├── GraphView.tsx      # D3 force graph
│   │   │   ├── DossiePanel.tsx
│   │   │   ├── LlmPanel.tsx
│   │   │   ├── CerebroPanel.tsx   # Insights, gargalos, posts
│   │   │   └── Sidebar.tsx
│   │   ├── hooks/                 # Custom hooks
│   │   │   ├── usePhotos.ts
│   │   │   ├── useOcr.ts
│   │   │   ├── useSearch.ts
│   │   │   └── useTheme.ts
│   │   ├── stores/                # Estado global (zustand)
│   │   │   └── appStore.ts
│   │   ├── types/                 # Tipos TypeScript
│   │   │   └── index.ts
│   │   └── styles/                # CSS Modules ou Tailwind
│   │       └── globals.css
│   └── public/
│
├── tests/                         # Testes organizados
│   ├── unit/
│   │   ├── test_ocr_service.py
│   │   ├── test_embedding_service.py
│   │   ├── test_llm_service.py
│   │   ├── test_file_service.py
│   │   └── test_search_service.py
│   ├── integration/
│   │   ├── test_api_fotos.py
│   │   ├── test_api_ocr.py
│   │   ├── test_api_busca.py
│   │   └── test_pipeline_completo.py
│   ├── conftest.py                # Fixtures compartilhadas
│   └── fixtures/                  # Imagens e dados de teste
│
├── scripts/                       # Utilitarios de operacao
│   ├── setup.sh                   # Instala tudo automaticamente
│   ├── migrate_from_flask.py      # Migra dados antigos
│   ├── backup_db.py               # Backup SQLite + ChromaDB
│   ├── health_check.py            # Verificacao de saude
│   └── benchmark.py               # Performance do pipeline
│
├── fotos/                         # Imagens (gitignore)
├── ocr_bruto/                     # OCR bruto (gitignore)
├── logs/                          # Logs rotacionados (gitignore)
├── chroma_data/                   # ChromaDB persistente (gitignore)
├── models/                        # Modelos ML locais (gitignore)
│   └── all-MiniLM-L6-v2/         # Ja baixado
├── APAGAVEL/                      # Lixeira do dev (gitignore)
│
├── .env.example                   # Template de variaveis
├── .env                           # Variaveis reais (gitignore)
├── .gitignore                     # Completo
├── requirements.txt               # Dependencias backend
├── requirements-dev.txt           # Dependencias de desenvolvimento
├── pyproject.toml                 # Configuracao do projeto
├── README.md                      # Documentacao publica
└── opus.md                        # Este arquivo (planejamento)
```

### 4.2 Fluxo de Dados Completo

```
CELULAR (Print de tela)
    |
    v
SYNCTHING (P2P automatico)
    |
    v
PASTA fotos/ (watchdog detecta novo arquivo)
    |
    v
FILE SERVICE
    ├── Calcula hash SHA-256
    ├── Detecta duplicata
    ├── Renomeia: 001_2026-02-24.jpg
    └── Registra no SQLite
    |
    v
OCR SERVICE (Tesseract)
    ├── Pre-processamento adaptativo
    ├── Extracao por confianca
    ├── Limpeza de ruido de UI
    ├── Extracao de @users, repos, hashtags
    └── Salva texto bruto + limpo
    |
    v
CEREBRO 1 — ENRIQUECIMENTO (LLM classifica)
    ├── fonte: twitter | github | site | reddit
    ├── tema: llm | agentes | automacao | dados
    ├── tipo: tutorial | opiniao | lancamento | ferramenta
    ├── sentimento: positivo | neutro | negativo
    ├── entidades: ["Claude", "n8n", "RAG"]
    ├── resumo: "2 frases"
    └── Salva metadados ricos no SQLite
    |
    v
EMBEDDING SERVICE
    ├── all-MiniLM-L6-v2 (384 dim)
    ├── Normaliza embeddings
    ├── Upsert no ChromaDB (cosine)
    └── Salva backup no SQLite (JSON)
    |
    v
CEREBRO 2 — GERACAO DE VALOR
    ├── Tendencias temporais (esta semana vs anterior)
    ├── Detector de gargalos (sentimento negativo recorrente)
    ├── Sugestor de posts com evidencias (cita prints reais)
    ├── Briefing semanal automatico
    └── Identificacao de lacunas ("falta isso no seu conhecimento")
    |
    v
FRONTEND REACT
    ├── Dashboard com metricas
    ├── Galeria interativa
    ├── Grafo de conhecimento (D3 force graph)
    ├── Timeline visual
    ├── Clusters por tema
    ├── Painel de Insights do Cerebro
    ├── Gerador de posts
    └── Busca semantica unificada
```

### 4.3 Schema do Banco (Evolucao)

```sql
-- Tabela fotos (colunas novas)
ALTER TABLE fotos ADD COLUMN fonte TEXT;        -- twitter, github, site, etc
ALTER TABLE fotos ADD COLUMN tema TEXT;          -- llm, agentes, automacao
ALTER TABLE fotos ADD COLUMN tipo TEXT;          -- tutorial, opiniao, lancamento
ALTER TABLE fotos ADD COLUMN sentimento TEXT;    -- positivo, neutro, negativo
ALTER TABLE fotos ADD COLUMN entidades TEXT;     -- JSON array
ALTER TABLE fotos ADD COLUMN resumo TEXT;        -- 2 frases geradas por LLM
ALTER TABLE fotos ADD COLUMN classificado INTEGER DEFAULT 0;
ALTER TABLE fotos ADD COLUMN hash_sha256 TEXT;   -- substituir MD5

-- Indices novos
CREATE INDEX IF NOT EXISTS idx_fotos_fonte ON fotos(fonte);
CREATE INDEX IF NOT EXISTS idx_fotos_tema ON fotos(tema);
CREATE INDEX IF NOT EXISTS idx_fotos_sentimento ON fotos(sentimento);
CREATE INDEX IF NOT EXISTS idx_fotos_classificado ON fotos(classificado);
```

---

## 5. OTIMIZACAO PARA O HARDWARE (i7-3770 + 16GB DDR3)

### 5.1 Configuracoes de Performance

```python
# Backend - FastAPI com uvicorn otimizado
# Usar 4 workers (1 por core fisico)
# Limitar threads do modelo de embeddings

# Embeddings: processar em lotes de 32 (nao 1000 de uma vez)
EMBEDDING_BATCH_SIZE = 32

# Ollama: limitar threads
OLLAMA_NUM_THREAD = 6  # Deixar 2 para o sistema

# ChromaDB: limitar uso de memoria
CHROMA_ANONYMIZED_TELEMETRY = False

# SQLite: WAL mode ja ativo, manter
# PRAGMA journal_mode=WAL;
# PRAGMA synchronous=NORMAL;
# PRAGMA cache_size=-64000;  -- 64MB de cache
# PRAGMA temp_store=MEMORY;

# Sentence-transformers: forcar CPU otimizado
# TOKENIZERS_PARALLELISM=false  -- Evita warning e deadlock
# OMP_NUM_THREADS=4
```

### 5.2 Gerenciamento de Memoria

```
Orcamento de RAM (16GB total):
├── Sistema operacional: ~2GB
├── Ollama (qwen2.5:7b carregado): ~6GB
├── Sentence-transformers (all-MiniLM-L6-v2): ~200MB
├── ChromaDB: ~300MB
├── FastAPI + workers: ~500MB
├── SQLite cache: ~64MB
├── Frontend dev server: ~200MB
└── Margem de seguranca: ~6.7GB

REGRA: Nao carregar Ollama e Sentence-transformers simultaneamente
em operacoes pesadas. Usar lazy loading.
```

### 5.3 Swap Otimizado (Linux)

```bash
# Confirmar:
sudo sysctl vm.swappiness=10
sudo sysctl vm.vfs_cache_pressure=50
```

---

## 6. CONFIGURACAO LLM (Gratuito)

### 6.1 Estrategia de Fallback

```
Prioridade de uso:
1. Ollama local (qwen2.5:7b) — gratis, privado, 5-10 tok/s
2. Groq API (gratis) — rapido, limite generoso
3. Google Gemini API (gratis) — boa qualidade, limite ok
4. Fallback manual — usuario cola texto no frontend
```

### 6.2 Configuracao por Tarefa

| Tarefa | Provider Ideal | Motivo |
|---|---|---|
| Classificacao de foto (curta) | Ollama local | <100 tokens, rapido |
| Resumo de dossie | Groq (gratis) | Rapido, bom para textos medios |
| Geracao de post | Ollama ou Groq | Criatividade, tamanho medio |
| Briefing semanal | Gemini ou Groq | Contexto longo, qualidade |
| Detector de gargalos | Ollama local | Privacidade, analise interna |

### 6.3 Configuracao Ollama

```bash
# Confirmar que Ollama esta servindo
curl http://localhost:11434/api/tags

# Modelo para classificacao rapida (futuro, mais leve):
ollama pull qwen2.5:3b  # 2GB, mais rapido para tarefas curtas

# Modelo atual para sinteses:
# qwen2.5:7b (ja instalado)
```

### 6.4 APIs Gratuitas - Setup

```env
# .env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Groq - criar conta em console.groq.com (gratis)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Gemini - criar conta em ai.google.dev (gratis)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash
```

---

## 7. CHROMADB — PLANO DE TESTE E USO

### 7.1 Instalacao e Validacao

```bash
pip install chromadb sentence-transformers
```

### 7.2 Teste de Integracao

```python
# scripts/test_chroma.py
import chromadb
from sentence_transformers import SentenceTransformer

# 1. Criar cliente persistente
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(
    name="cerebro_v2",
    metadata={"hnsw:space": "cosine"}
)

# 2. Carregar modelo
model = SentenceTransformer("models/all-MiniLM-L6-v2")

# 3. Testar encode + upsert
textos = [
    "Claude Code agora suporta MCP tools",
    "RAG com LangChain e ChromaDB",
    "Como fazer fine-tuning de LLM local",
]
embeddings = model.encode(textos, normalize_embeddings=True)

collection.upsert(
    ids=["t1", "t2", "t3"],
    embeddings=embeddings.tolist(),
    documents=textos,
    metadatas=[{"fonte": "twitter"}, {"fonte": "github"}, {"fonte": "site"}]
)

# 4. Testar busca semantica
query = "otimizar modelo de linguagem"
query_emb = model.encode([query], normalize_embeddings=True)
results = collection.query(query_embeddings=query_emb.tolist(), n_results=3)
print(results)
# Deve retornar "fine-tuning de LLM" como mais similar
```

### 7.3 Migracao de Dados Existentes

```python
# scripts/migrate_from_flask.py
# Le embeddings do SQLite antigo e insere no ChromaDB novo
# Le fotos com ocr_limpo e gera embeddings semanticos
# Executa em batch de 32 para nao estourar RAM
```

---

## 8. AUTOMACAO — SYNCTHING

### 8.1 Setup

```bash
# Instalar Syncthing no Linux
sudo apt install syncthing

# Iniciar como servico
systemctl --user enable syncthing
systemctl --user start syncthing

# Acessar UI: http://localhost:8384

# No celular: instalar Syncthing do F-Droid ou Play Store
# Configurar pasta de screenshots para sincronizar com:
# /home/fabiorjvr/Area de trabalho/leitorcontextofoto/fotos/
```

### 8.2 Integracao com o Projeto

```
Celular tira print
    -> Syncthing detecta novo arquivo
    -> Sincroniza para pasta fotos/ no PC
    -> Watchdog (backend) detecta novo arquivo
    -> Pipeline automatico: OCR -> Classificacao -> Embeddings -> ChromaDB
    -> Disponivel no frontend em segundos
```

### 8.3 Watchdog em vez de Polling

```python
# Substituir loop de 20s por watchdog (inotify no Linux)
from watchdog.observers import Observer
from watchdog.events import FileCreatedHandler

class FotoHandler(FileCreatedHandler):
    def on_created(self, event):
        if event.src_path.endswith(('.jpg', '.png', '.webp')):
            processar_nova_foto(event.src_path)

observer = Observer()
observer.schedule(FotoHandler(), path="fotos/", recursive=False)
observer.start()
```

---

## 9. CEREBRO 1 — ENRIQUECIMENTO AUTOMATICO

### 9.1 Classificacao Pos-OCR

Apos cada OCR, o texto extraido e enviado ao LLM (local ou API) para
classificacao estruturada:

```python
PROMPT_CLASSIFICACAO = """
Analise o texto extraido de um print de tela e classifique:

TEXTO:
{texto}

Responda APENAS em JSON valido:
{{
    "fonte": "twitter|instagram|github|site|reddit|youtube|outro",
    "tema": "llm|agentes|automacao|dados|web|devops|outro",
    "tipo": "tutorial|opiniao|lancamento|caso_de_uso|ferramenta|debate|outro",
    "sentimento": "positivo|neutro|negativo",
    "entidades": ["lista", "de", "nomes", "proprios"],
    "resumo": "Duas frases resumindo o conteudo principal."
}}
"""
```

### 9.2 Pipeline Automatico

```
Foto nova detectada
    -> OCR (Tesseract)
    -> Texto limpo salvo
    -> LLM classifica (Ollama local, <5s)
    -> Metadados salvos no SQLite
    -> Embedding gerado (all-MiniLM-L6-v2, <0.5s)
    -> Upsert no ChromaDB com metadados ricos
    -> Pronto para consulta
```

---

## 10. CEREBRO 2 — GERACAO DE VALOR

### 10.1 Tendencias Temporais

```python
# Comparar clusters entre semanas
# "Esta semana: 12 prints sobre 'Claude Code', semana passada: 3"
# "Tema emergente: 'MCP Protocol' apareceu 8x em 3 dias"
```

### 10.2 Detector de Gargalos

```python
# Quando um tema aparece com sentimento negativo repetido:
# "Alerta: 5 prints sobre 'token expensive' com sentimento negativo"
# "Gargalo detectado: 'database locked' mencionado 4x esta semana"
```

### 10.3 Gerador de Posts com Evidencias

```python
# Nao gera do nada — cita prints reais como fonte:
# "Baseado em 7 prints desta semana sobre Claude Code:
#  - Print #045: '@AnthropicAI lancou MCP tools'
#  - Print #048: 'Tutorial de integracao com VS Code'
#  - Print #052: '@simonw comparou com Cursor'
#  Post sugerido: 'Thread: 3 formas de usar Claude Code com MCP...'"
```

### 10.4 Briefing Semanal

```python
# Todo domingo (ou sob demanda):
# 1. Quantos prints processados na semana
# 2. Top 5 temas por volume
# 3. Tendencias crescentes vs decrescentes
# 4. Gargalos detectados
# 5. 3 sugestoes de post com evidencias
# 6. Lacunas: "Voce leu muito sobre RAG mas nada sobre custos"
```

### 10.5 Identificacao de Lacunas

```python
# Analisa distribuicao de temas e detecta gaps:
# "Voce tem 15 prints sobre 'agentes IA' mas nenhum sobre 'avaliacao de agentes'"
# "Sugestao: pesquisar benchmarks e metricas de agentes"
```

---

## 11. FRONTEND REACT — DESIGN

### 11.1 Stack

| Tecnologia | Motivo |
|---|---|
| React 18 | Componentizado, ecosystem maduro |
| Vite | Build rapido, HMR instantaneo |
| TypeScript | Tipos, menos bugs, autocomplete |
| Zustand | Estado global simples (sem Redux overhead) |
| Tailwind CSS | Utility-first, responsivo, tema claro/escuro |
| D3.js | Grafos interativos (ja tem base) |
| React Query (TanStack) | Cache de API, revalidacao automatica |

### 11.2 Paginas/Abas

1. **Dashboard** — Metricas gerais, briefing semanal, alertas
2. **Galeria** — Grid de fotos com filtros (fonte, tema, semana)
3. **OCR Workspace** — Upload, extracao, edicao de texto
4. **Brain Map** — Word cloud, top palavras/users/repos
5. **Grafo** — Grafo de conhecimento interativo (D3 force)
6. **Clusters** — Agrupamentos por tema com drill-down
7. **Timeline** — Visualizacao temporal (barras por semana/mes)
8. **Dossie** — Busca por termo, coocorrencias, ancoras
9. **Cerebro** — Insights, gargalos, sugestoes de post, tendencias
10. **Config** — LLM providers, Syncthing status, saude do sistema

### 11.3 Principios de UI

- Mobile-first (responsivo para quando usar no celular)
- Tema claro/escuro (persistido no localStorage)
- Loading states e skeletons (nao telas brancas)
- Toast notifications (nao alert())
- Keyboard shortcuts para power users
- Acessibilidade basica (ARIA labels, contraste)

---

## 12. SEGURANCA (Base para Multi-Usuario Futuro)

### 12.1 Fase Atual (Uso Pessoal)

```python
# Autenticacao basica com token fixo
# Header: Authorization: Bearer <token-do-.env>
API_TOKEN = os.getenv("API_TOKEN", "")  # Se vazio, sem auth (dev)

# CORS restrito
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:8000"]

# Rate limiting basico
# 60 req/min para API geral
# 10 req/min para OCR (CPU pesado)
# 5 req/min para LLM (muito pesado)
```

### 12.2 Fase Futura (Multi-Usuario)

```python
# JWT com refresh tokens
# OAuth2 (Google, GitHub)
# Row-level security no banco
# Isolamento de dados por usuario
# HTTPS obrigatorio
# Audit log de acoes
```

### 12.3 Boas Praticas Imediatas

- Nunca expor stack traces (debug=False)
- Validar MIME type + magic bytes no upload
- Sanitizar paths (werkzeug.secure_filename)
- SQL parametrizado (ja faz, manter)
- Escapar output HTML (React faz por padrao)
- .env no .gitignore (ja faz)
- Secrets nunca hardcoded

---

## 13. TESTES

### 13.1 Estrutura

```
tests/
├── unit/
│   ├── test_ocr_service.py          # Limpeza, extracao, pre-processamento
│   ├── test_embedding_service.py    # Encode, similaridade, batch
│   ├── test_llm_service.py          # Fallback, parsing de resposta
│   ├── test_file_service.py         # Rename, dedup, watchdog
│   ├── test_search_service.py       # Textual, semantica
│   └── test_cerebro_service.py      # Classificacao, insights
├── integration/
│   ├── test_api_fotos.py            # Upload, listagem, delete
│   ├── test_api_ocr.py              # Extracao end-to-end
│   ├── test_api_busca.py            # Busca textual + semantica
│   ├── test_api_cerebro.py          # Pipeline completo
│   └── test_chroma_integration.py   # ChromaDB upsert + query
├── conftest.py                      # Fixtures: DB em memoria, fotos de teste
└── fixtures/
    ├── sample_twitter.png           # Print de teste
    ├── sample_github.png
    └── sample_text.txt              # Texto OCR de referencia
```

### 13.2 Comandos

```bash
# Testes unitarios (rapido, sem IO)
pytest tests/unit/ -v --tb=short

# Testes de integracao (com DB e filesystem)
pytest tests/integration/ -v --tb=short

# Cobertura
pytest --cov=backend --cov-report=term-missing

# Lint
ruff check backend/ tests/
ruff format backend/ tests/ --check

# Type check
mypy backend/ --ignore-missing-imports
```

---

## 14. FASES DE EXECUCAO

### FASE 0 — Fundacao (3-5 dias) — CONCLUIDA 2026-02-24
**Objetivo**: Infraestrutura basica, tudo rodando.

- [x] Instalar dependencias faltantes (sentence-transformers, chromadb, fastapi, uvicorn, aiosqlite, pydantic-settings, python-multipart, python-json-logger — venv Linux em .venv_linux/)
- [x] Criar requirements.txt e requirements-dev.txt
- [x] Corrigir .gitignore (adicionado chroma_data/, models/, .venv/, .venv_linux/, *.db, logs/, server.log, flask.log, diagnostico_chroma_out.json)
- [x] Remover langwatch de todo o codigo (chroma_store.py, tests/test_ocr_limpeza.py, tests/test_regressao_embeddings.py)
- [x] Corrigir regex de data em file_manager.py (escapamento duplo \\d -> \d — CRITICO, estava quebrando todas as datas)
- [x] Criar .env.example com todas as variaveis (Ollama, Groq, Gemini, seguranca, diretorios, CORS)
- [x] Testar all-MiniLM-L6-v2 com sentence-transformers — PASS (Shape: 3x384, 0.09s)
- [x] Testar ChromaDB (criar, upsert, query) — PASS (busca semantica retornou resultado correto)
- [x] Testar Ollama API — PASS (qwen2.5:7b respondeu em 2.4s, llava:7b disponivel)
- [x] Mover arquivos desnecessarios para APAGAVEL/ (diagnostico_chroma.py, plano.md, relatoriokimi.md, test_modelo.py, all-MiniLM-L6-v2.txt)
- Script de validacao criado: scripts/validar_fase0.py (todos PASS)

### FASE 1 — Backend FastAPI (5-7 dias) — CONCLUIDA 2026-02-24
**Objetivo**: Backend novo funcional, API completa.

- [x] Criar estrutura backend/ com pastas
- [x] Implementar config.py com Pydantic BaseSettings
- [x] Implementar db/database.py com aiosqlite + pool
- [x] Implementar db/repositories.py (CRUD puro)
- [x] Implementar db/models.py (Pydantic schemas)
- [x] Migrar services: ocr_service.py (do ocr_engine.py atual)
- [x] Migrar services: file_service.py (do file_manager.py atual)
- [x] Implementar services: embedding_service.py (MiniLM + ChromaDB)
- [x] Implementar services: llm_service.py (Ollama + Groq + Gemini com fallback)
- [x] Implementar services: search_service.py (textual + semantica)
- [x] Implementar services: graph_service.py (grafo + clusters)
- [x] Implementar stores: chroma_store.py (wrapper limpo)
- [x] Implementar utils: logger.py (logging estruturado)
- [x] Implementar utils: security.py (auth token, CORS, rate limit)
- [x] Implementar api/ routers (fotos, ocr, busca, embeddings, insights, llm, health)
- [x] Implementar main.py com startup/shutdown events
- [x] Implementar watchdog para pasta fotos/ (substituir polling)
- [x] Migrar dados do SQLite antigo (script migrate_from_flask.py)
- [x] Testes unitarios para todos os services
- [x] Testes de integracao para API (conftest.py + test_api_basic.py)

### FASE 2 — Cerebro 1: Enriquecimento (3-4 dias)
**Objetivo**: Classificacao automatica de cada foto pos-OCR.

- [ ] Implementar cerebro1_service.py
- [ ] Criar prompt de classificacao (fonte, tema, tipo, sentimento, entidades, resumo)
- [ ] Integrar com Ollama local (qwen2.5:7b)
- [ ] Fallback para Groq/Gemini quando Ollama indisponivel
- [ ] Adicionar colunas no SQLite (fonte, tema, tipo, sentimento, entidades, resumo)
- [ ] Pipeline automatico: OCR -> Classificacao -> Embeddings
- [ ] Processar fotos existentes em batch (retroativo)
- [ ] Testes de classificacao com prints reais
- [ ] API endpoint: POST /api/cerebro/classificar/{numero}
- [ ] API endpoint: POST /api/cerebro/classificar-batch

### FASE 3 — Cerebro 2: Geracao de Valor (4-5 dias)
**Objetivo**: Insights, gargalos, sugestoes de post.

- [ ] Implementar cerebro2_service.py
- [ ] Tendencias temporais (comparar semanas)
- [ ] Detector de gargalos (sentimento negativo recorrente)
- [ ] Gerador de posts com evidencias (cita prints reais)
- [ ] Briefing semanal automatico
- [ ] Identificacao de lacunas ("falta isso")
- [ ] API endpoint: GET /api/cerebro/tendencias?semana=...
- [ ] API endpoint: GET /api/cerebro/gargalos
- [ ] API endpoint: POST /api/cerebro/gerar-post
- [ ] API endpoint: GET /api/cerebro/briefing?periodo=semana
- [ ] API endpoint: GET /api/cerebro/lacunas
- [ ] Testes com dados reais

### FASE 4 — Frontend React (7-10 dias)
**Objetivo**: Interface profissional completa.

- [ ] Setup Vite + React + TypeScript + Tailwind
- [ ] Configurar proxy para FastAPI (vite.config.ts)
- [ ] Implementar api/client.ts (chamadas HTTP tipadas)
- [ ] Implementar store global (Zustand)
- [ ] Componente: Header + Theme Toggle
- [ ] Componente: PhotoDrop (upload drag-and-drop)
- [ ] Componente: OcrWorkspace (extracao + edicao)
- [ ] Componente: Gallery (grid com filtros)
- [ ] Componente: BrainMap (word cloud)
- [ ] Componente: Timeline (barras por semana/mes)
- [ ] Componente: ClusterView (agrupamentos)
- [ ] Componente: GraphView (D3 force graph interativo)
- [ ] Componente: DossiePanel (busca + coocorrencias)
- [ ] Componente: LlmPanel (config de providers)
- [ ] Componente: CerebroPanel (insights, gargalos, posts)
- [ ] Componente: Sidebar (stats, top palavras/users/repos)
- [ ] Componente: Dashboard (metricas, alertas, briefing)
- [ ] Responsivo (mobile-first)
- [ ] Tema claro/escuro
- [ ] Loading states e error handling
- [ ] Toast notifications

### FASE 5 — Automacao Syncthing (1-2 dias)
**Objetivo**: Fotos do celular chegam automaticamente.

- [ ] Instalar e configurar Syncthing no Linux
- [ ] Instalar Syncthing no celular
- [ ] Configurar pasta de screenshots -> fotos/
- [ ] Testar sync automatico
- [ ] Documentar setup no README

### FASE 6 — Polimento e Producao (3-4 dias)
**Objetivo**: Projeto pronto para uso real diario.

- [ ] Script de setup automatizado (setup.sh)
- [ ] Health check endpoint (/health)
- [ ] Metricas de uso (/metrics)
- [ ] Backup automatico de SQLite + ChromaDB
- [ ] Documentacao completa no README.md
- [ ] Cobertura de testes > 70%
- [ ] Performance benchmark
- [ ] Corrigir todos os warnings de lint
- [ ] Logging rotacionado funcionando
- [ ] Testar pipeline completo end-to-end
- [ ] Limpar APAGAVEL/ e codigo morto

---

## 15. DEPENDENCIAS COMPLETAS

### requirements.txt (Producao)

```
# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
python-multipart>=0.0.18

# Database
aiosqlite>=0.20.0

# OCR
pytesseract>=0.3.13
Pillow>=10.2.0

# Embeddings & Vector Store
sentence-transformers>=3.3.0
chromadb>=0.5.0
numpy>=2.0.0

# LLM Integration
httpx>=0.27.0

# File Management
watchdog>=6.0.0

# Config & Security
python-dotenv>=1.0.0
pydantic-settings>=2.7.0

# Logging
python-json-logger>=3.0.0
```

### requirements-dev.txt (Desenvolvimento)

```
-r requirements.txt

# Testes
pytest>=8.0.0
pytest-asyncio>=0.25.0
pytest-cov>=6.0.0

# Lint & Format
ruff>=0.8.0
mypy>=1.14.0

# Debug
ipython>=8.0.0
```

---

## 16. METRICAS DE SUCESSO

### Curto Prazo (30 dias)

- [ ] Pipeline completo funcionando: foto -> OCR -> classificacao -> embeddings -> ChromaDB
- [ ] Busca semantica retornando resultados relevantes
- [ ] Cerebro 1 classificando fotos automaticamente
- [ ] Frontend React funcional com todas as abas
- [ ] Syncthing sincronizando fotos do celular

### Medio Prazo (60 dias)

- [ ] Cerebro 2 gerando insights uteis
- [ ] Gerador de posts produzindo sugestoes com evidencias
- [ ] Briefing semanal automatico funcionando
- [ ] Detector de gargalos identificando padroes reais
- [ ] 100+ fotos processadas e indexadas
- [ ] Cobertura de testes > 70%

### Longo Prazo (6 meses)

- [ ] Preparar para multi-usuario (auth, isolamento)
- [ ] Migrar para PostgreSQL + pgvector se necessario
- [ ] API publica documentada (OpenAPI)
- [ ] Docker compose para deploy facil
- [ ] CI/CD pipeline
- [ ] Monetizacao (SaaS)

---

## 17. RISCOS E MITIGACOES

| Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|
| RAM insuficiente com Ollama + tudo | Alta | Medio | Lazy loading, nao carregar tudo junto |
| ChromaDB corrompido | Baixa | Alto | Backup SQLite como fonte de verdade |
| Ollama lento para classificacao | Alta | Baixo | Fallback Groq/Gemini gratis |
| OCR ruim em prints escuros | Media | Medio | Pre-processamento adaptativo ja existe |
| Syncthing conflito de arquivos | Baixa | Baixo | Dedup por hash, watchdog ignora temp |
| Groq/Gemini mudar limites gratis | Media | Medio | Ollama local como fallback primario |

---

## 18. CONVENCOES DO PROJETO

### Codigo Python
- Formatacao: ruff format
- Lint: ruff check
- Tipos: mypy (gradual)
- Docstrings: Google style
- Nomes: snake_case para funcoes/variaveis, PascalCase para classes
- Imports: stdlib -> third-party -> local (ruff organiza)

### Codigo TypeScript/React
- Formatacao: Prettier
- Lint: ESLint
- Componentes: Functional com hooks
- Estado: Zustand (global), useState (local)
- Estilo: Tailwind CSS utility classes
- Nomes: camelCase para funcoes, PascalCase para componentes

### Git
- Mensagens: imperativo, em portugues
  - "Adicionar endpoint de classificacao"
  - "Corrigir regex de data no file_manager"
  - "Refatorar embedding_service para batch processing"
- Branches: main (estavel), dev (desenvolvimento)
- Commits: frequentes, atomicos

### Logs
- Formato: JSON estruturado
- Niveis: DEBUG, INFO, WARNING, ERROR
- Rotacao: 10MB por arquivo, 5 arquivos
- Nao logar dados sensiveis (API keys, textos completos)

---

## 19. ORDEM DE EXECUCAO IMEDIATA

```
AGORA (primeira sessao):
1. Instalar sentence-transformers e chromadb
2. Validar que all-MiniLM-L6-v2 funciona
3. Validar ChromaDB (criar, upsert, query)
4. Criar requirements.txt
5. Corrigir .gitignore
6. Remover langwatch
7. Corrigir regex de data

PROXIMO:
8. Criar estrutura backend/
9. Migrar config.py para Pydantic BaseSettings
10. Migrar database.py para aiosqlite
11. Implementar services um por um
12. Implementar rotas FastAPI
13. Testes

DEPOIS:
14. Cerebro 1 (classificacao)
15. Cerebro 2 (insights)
16. Frontend React
17. Syncthing
18. Polimento
```

---

**Este documento e vivo. Sera atualizado conforme o projeto evolui.**
**Proxima revisao: apos completar Fase 0.**
