# 2 CÉREBRO — Conhecimento Estruturado e Automação

O **2 Cérebro** é um sistema de "segundo cérebro digital" que transforma capturas de tela (Twitter, Instagram, GitHub, sites) em conhecimento estruturado, conectado e acionável.

---

## 🎯 Objetivo Final
Criar uma plataforma profissional que **ingere imagens automaticamente**, extrai texto via OCR (reduzindo ruído de UI), gera embeddings semânticos para buscas complexas, detecta padrões/gargalos de informações, sugere postagens para redes sociais e gera insights usando Modelos de Linguagem (LLMs).
O projeto foi pensado para rodar em hardware pessoal comum (CPU) com máxima otimização, e já possui arquitetura preparada para escalar para nuvem e múltiplos usuários.

---

## 🚀 Progresso Atual

O projeto passou recentemente por um intenso *Refactoring* estrutural para substituir a versão protótipo antiga (baseada em scripts monolíticos com Flask) por uma base profissional assíncrona.

### Fase 0 — Fundação (CONCLUÍDA)
O foco foi limpar a dívida técnica e garantir que a infraestrutura local estivesse 100% pronta.
* **Ambiente e Dependências**: Criação de ambiente virtual Linux (`.venv_linux/`), adição do `requirements.txt` com todas as dependências isoladas (FastAPI, ChromaDB, Sentence-Transformers, Pytest).
* **Limpeza de Código**: Remoção de bibliotecas não utilizadas e fantasmas (como `langwatch`), correção de Expressões Regulares quebradas (regex de extração de data dos arquivos).
* **Configurações e Segurança**: Arquivo `.gitignore` robusto criado, e criação do `.env.example` protegendo integrações com Ollama, Groq e Gemini.
* **Testes Base**: Criação do script de validação de modelos que confirmou o funcionamento do `all-MiniLM-L6-v2`, `ChromaDB` e a API do `Ollama`.

### Fase 1 — Backend FastAPI (CONCLUÍDA)
A arquitetura foi inteiramente reescrita para focar em performance, escalabilidade e design de software moderno.
* **Estrutura de Pastas Profissional**: Divisão do código em `backend/api`, `backend/db`, `backend/services`, `backend/stores` e `backend/utils`.
* **Banco de Dados Assíncrono**: Transição do SQLite síncrono para o `aiosqlite` (assíncrono) utilizando Connection Pools, Modo WAL e migrations automáticas no `database.py`. Separação do CRUD bruto (`repositories.py`) da lógica de negócios.
* **Pydantic**: Adoção estrita de validação de dados com *Pydantic* tanto para Settings (`config.py`) quanto para In/Out da API (`models.py`).
* **FastAPI**: Migração de todas as rotas de Flask para FastAPI. O App agora documenta tudo automaticamente no Swagger (`/docs`) e usa processamento assíncrono para liberar o event loop.
* **Serviços em Background**: O Watchdog de sincronização de pastas (antigo sleep em loop) agora roda nativamente gerido pelo ciclo de vida do FastAPI sem travar requisições.
* **Vetor e Semantic DB**: Criação de um Singleton Wrapper robusto para o `ChromaDB` (em `stores/chroma_store.py`).
* **Testes de Integração**: Testes assíncronos via `pytest`, `pytest-asyncio` e cliente `httpx` validando a API contra bancos de dados em memória ou temporários. Tudo fluindo com lint (`Ruff`) e tipagem (`Mypy`) zerados.
* **Migração de Dados**: Escrito e executado com sucesso script (`migrate_from_flask.py`) migrando imagens e banco antigo para o novo esquema relacional + vetorial de uma vez só.

---

## 🏗️ Arquitetura e Tecnologias

* **Backend API**: Python 3.12, FastAPI, Uvicorn, Pydantic, HTTPX.
* **Banco Relacional**: SQLite (via aiosqlite, WAL Mode).
* **Banco Vetorial**: ChromaDB (Cosine Similarity).
* **Machine Learning / OCR**: PyTesseract, SentenceTransformers (`all-MiniLM-L6-v2`), NumPy, Pillow.
* **Qualidade**: Ruff, Mypy, Pytest.
* **LLM Integrations**: Ollama (Local), Groq, Gemini.

---

## 💻 Como Rodar (Ambiente Linux)

1. Instale o Tesseract no sistema:
   ```bash
   sudo apt install tesseract-ocr tesseract-ocr-por
   ```
2. Inicie o ambiente virtual limpo e instale:
   ```bash
   python3 -m venv .venv_linux
   source .venv_linux/bin/activate
   pip install -r requirements.txt
   ```
3. Copie o arquivo de variáveis de ambiente e preencha:
   ```bash
   cp .env.example .env
   ```
4. Suba o servidor:
   ```bash
   PYTHONPATH=. python backend/main.py
   # A API estará disponível em http://0.0.0.0:8000
   # A documentação automática (Swagger) em http://0.0.0.0:8000/docs
   ```

---

## 🔮 Próximos Passos (Fases Mapeadas)

* **FASE 2 (Cérebro 1 — Enriquecimento)**: 
  * Classificação automática pós-OCR via LLMs (Ollama/Groq) determinando fonte, tema, sentimento e gerando resumo do print.
* **FASE 3 (Cérebro 2 — Geração de Valor)**:
  * Agente que avalia o banco para gerar "Briefing Semanal", descobrir tendências, sugerir tópicos de posts e apontar lacunas no conhecimento rastreado.
* **FASE 4 (Frontend React)**:
  * Reescrita completa da interface de usuário que abandonará HTML puro/monolítico para dar lugar a um app modular em React (Vite, Tailwind, Zustand) exibindo o Grafo de forma interativa.
