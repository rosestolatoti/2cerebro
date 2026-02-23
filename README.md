# 2 CÉREBRO — OCR, Contexto e Tendências de Prints

Projeto privado para transformar prints em conhecimento estruturado: OCR robusto, ranking de usuários, repos GitHub, clusters, grafo semântico e dossiê por termo.

## Objetivo Final

- Automatizar ingestão de prints com renomeação e indexação contínua
- Extrair texto com alta qualidade, reduzindo ruído de interface
- Gerar contexto: palavras, @users, repos, clusters, grafo e dossiês por termo
- Permitir uso futuro como app móvel ou produto para terceiros
- Ter pipeline confiável com testes, lint e validações antes de mudanças

## Status Atual (Resumo)

- OCR com Tesseract e limpeza de texto
- Extração de palavras, @users e repos GitHub
- Banco SQLite com fotos, palavras, usuários, repos e embeddings
- Similaridade por TF‑IDF + SVD
- Clusters e grafo semântico no frontend
- Dossiê de termo com coocorrências, timeline e âncoras
- Painel LLM opcional com múltiplos provedores
- Sincronização automática da pasta fotos/ a cada 20s
- Interface responsiva com tema claro/escuro

## Automações Ativas

- Sincronização contínua da pasta fotos/ com renomeação e registro automático
- Detecção de duplicatas por hash MD5
- Registro inicial de fotos existentes no startup
- Reconstrução de embeddings via endpoint dedicado

## Como Funciona (Fluxo Completo)

1. **Adicionar fotos** na pasta fotos/ ou via upload.
2. **Sincronizar**: o backend renomeia e registra novas imagens.
3. **Extrair OCR** na foto selecionada.
4. **Limpar e salvar** o texto no banco.
5. **Atualizar painéis**: palavras, usuários, repos, clusters e grafo.
6. **Consultar dossiê** para ver coocorrências e linha do tempo.
7. **Gerar insights LLM** (opcional) a partir do dossiê.

## Arquitetura

- Backend: Flask + SQLite
- OCR: Tesseract + pré‑processamento
- NLP: TF‑IDF + SVD para similaridade
- Frontend: HTML/CSS/JS + D3 para grafo
- LLM: integração opcional com múltiplos provedores

## Estrutura do Projeto

```
leitorcontextofoto/
├── app.py              # API Flask e rotas
├── config.py           # Configurações globais
├── database.py         # Banco SQLite e queries
├── embeddings.py       # Vetores e similaridade
├── file_manager.py     # Renomeação e sync de fotos
├── ocr_engine.py       # Motor de OCR
├── templates/
│   └── index.html      # UI principal
├── static/
│   ├── style.css       # Estilos
│   └── app.js          # Lógica do frontend
├── fotos/              # Imagens (não versionado)
├── ocr_bruto/          # OCR bruto (não versionado)
├── logs/               # Logs (não versionado)
├── tests/              # Testes
└── gigu_brain.db       # DB (não versionado)
```

## Principais Endpoints

- GET /api/fotos
- POST /api/ocr/<numero>
- POST /api/ocr/<numero>/salvar
- POST /api/ocr/<numero>/salvar-motor
- POST /api/embeddings/rebuild
- GET /api/similares/<numero>
- GET /api/clusters
- GET /api/grafo
- GET /api/insights/dossie?termo=...
- POST /api/llm/analisar

## Testes e Qualidade

Testes existentes:

- tests/test_ocr_limpeza.py
- tests/test_regressao_embeddings.py
- tests/ocr_amostra.py
- tests/renomear_fotos.py

Comandos padrão:

```bash
python -m flake8 app.py database.py ocr_engine.py file_manager.py config.py --max-line-length=120
python -m py_compile app.py database.py ocr_engine.py file_manager.py
pytest -q
```

## Erros e Problemas Reais Encontrados

- PSReadLine no PowerShell gerando erro visual durante execução de comandos
- flake8 ausente inicialmente, exigiu instalação via pip
- OCR captura ruído de UI em prints de aplicativos
- Tipografias pequenas e fundos escuros reduzem precisão
- Repos GitHub podem aparecer truncados

## Pendências e Próximos Passos

- OCR por áreas de texto para reduzir UI residual
- PaddleOCR como fallback e comparação real no endpoint /api/ocr/<numero>/comparar
- Heurística para completar repos truncados
- Modo batch para OCR em lote com relatório
- Ranking temporal por semana/mês no frontend
- Testes de regressão para grafo e clusters com dados reais
- Pipeline automatizado antes de cada mudança no projeto
- Planejamento de migração para PostgreSQL quando escalar

## Instalação (Resumo)

1. Instalar Tesseract no sistema.
2. Criar venv e instalar dependências:

```bash
python -m venv venv
venv\Scripts\activate
pip install flask pillow pytesseract
```

3. Rodar:

```bash
python app.py
```

## Observações Importantes

- Fotos, DB, OCR bruto e logs são locais e não versionados.
- O foco atual é produção interna com automação total.
