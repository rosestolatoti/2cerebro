# 📋 RELATÓRIO 02 — Análise do Roadmap v1.1

**Data:** 22/02/2026  
**Projeto:** GigU Brain  
**Roadmap:** gigu_brain_v1.1_roadmap.md  
**Análise:** Sisyphus AI

---

## SUMÁRIO EXECUTIVO

| Métrica | Valor |
|---------|-------|
| **Tarefas no Roadmap** | 10 |
| **Bugs identificados** | 3 |
| **Features propostas** | 5 |
| **Melhorias de qualidade** | 2 |
| **Bugs já existentes (fora roadmap)** | ~6 |

---

## ANÁLISE DETALHADA POR TAREFA

---

### #01 — Bug: Fotos duplicadas no banco

**Status Atual (verificado no código):** ❌ **NÃO CORRIGIDO**

**Local:** `file_manager.py:20-33` + `app.py:16`

**Problema confirmado:**
```python
# app.py:16
registrar_fotos_existentes()  # Roda a cada init do Flask
```
```python
# file_manager.py:20-33
def registrar_fotos_existentes():
    arquivos = sorted([...])
    for arquivo in arquivos:
        numero = proximo_numero()
        registrar_foto(numero, arquivo.name, str(arquivo))  # SEM verificação!
```

**Análise:** O bug está 100% confirmado. A função `registrar_foto` usa `INSERT OR IGNORE` no banco (via `numero UNIQUE`), mas não verifica se o `filepath` já existe. Se o usuário adicionar fotos na pasta `fotos/` manualmente, elas serão re-registradas a cada restart.

**Solução proposta no roadmap:** ✅ Correta e mínima.

**Minha opinião:** A correção é necessária e urgente. Uma melhoria adicional seria adicionar uma coluna `hash_md5` para detecção de duplicatas por conteúdo, não só por caminho.

---

### #02 — Bug: Detecção de foto duplicada no upload

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Local:** `database.py:24-34` (tabela fotos) + `file_manager.py:36-56`

**Problema:** Não existe:
- Coluna `hash_md5` na tabela `fotos`
- Função de gerar hash do arquivo
- Verificação de duplicata por conteúdo

**Tabela atual fotos:**
```sql
CREATE TABLE fotos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    numero      TEXT UNIQUE NOT NULL,
    filename    TEXT NOT NULL,
    filepath    TEXT NOT NULL,
    status      TEXT DEFAULT 'pendente',
    ocr_texto   TEXT,
    ocr_limpo   TEXT,
    criado_em   TEXT,
    processado_em TEXT
    -- FALTA: hash_md5 TEXT
);
```

**Solução proposta no roadmap:** ✅ Completa, mas requer migração de banco.

**Minha opinião:** Essencial para um sistema robusto. Recomendo incluir também `hash_sha256` para segurança adicional. A migração deve ser feita com `ALTER TABLE` condicional.

---

### #03 — Bug: Galeria some ao abrir OCR

**Status Atual:** ❌ **NÃO CORRIGIDO** (problema existe)

**Local:** `static/app.js:78-97` + `templates/index.html:55`

**Código atual problemático:**
```javascript
// app.js:82-83
document.getElementById("section-ocr").style.display = "block";
document.getElementById("section-ocr").scrollIntoView({ behavior: "smooth" });
```

```html
<!-- index.html:55 -->
<section class="card" id="section-ocr" style="display:none">
```

**Problema confirmado:** O OCR usa `display: block` que empurra a galeria para baixo. O usuário perde a visão da galeria.

**Solução proposta:** Modal overlay - ✅ Excelente ideia.

**Minha opinião:** A abordagem modal é muito melhor UX. Pode até usar o padrão existente de `section-ocr` mas com `position: fixed` e `z-index`.

---

### #04 — Feature: Botão deletar foto

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Verificações:**
- `grep "DELETE" app.py` → 0 resultados
- `grep "deletar" app.py` → 0 resultados
- `grep "remover" app.py` → 0 resultados

**Solução proposta no roadmap:** ✅ Correta.

**Minha opinião:** Funcionalidade urgente. O sistema não pode crescer sem capacidade de remoção. Recomendo também adicionar:
- Confirmação antes de deletar (modal de confirmação)
- Deletar palavras associadas da tabela `palavras`
- Backup antes de deletar arquivo físico

---

### #05 — Feature: Tema claro/escuro com toggle

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Verificações:**
- `grep "toggleTheme"` → 0 resultados no código (só no roadmap)
- `grep "data-theme"` → só no roadmap, não implementado
- CSS atual: apenas `var(--bg): #0f1117` (dark mode hardcoded)

**Solução proposta:** ✅ Completa, com CSS variables e localStorage.

**Minha opinião:** Excelente proposta. O código JS exampleado está correto. O único ponto de atenção é o CSS do tema claro precisar ser testado cuidadosamente (contrastes, cores de borda, etc).

---

### #06 — UX: Reorganizar layout da página (Sidebar)

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Layout atual verificado (index.html):**
```html
<header>...</header>
<main>
  <section id="section-upload">...</section>
  <section id="section-galeria">...</section>
  <section id="section-ocr" style="display:none">...</section>
  <section id="section-brain">...</section>
</main>
```

**Estrutura:** Vertical, sequencial, sem sidebar.

**Solução proposta:** Grid com sidebar fixa - ✅ Muito bom.

**Minha opinião:** A reorganização proposta melhora drasticamente a UX, especialmente para quem tem muitas fotos. O Brain Map fica mais acessível.

**Consideração:** Esta mudança afeta TODO o CSS e HTML. Deve ser a última a ser implementada (ou uma das primeiras, dependendo da estratégia).

---

### #07 — UX: Navegação por abas

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Verificações:**
- `grep "abas"` → 0 resultados
- `grep "tab"` → 0 resultados relevantes

**Solução proposta:** ✅ Simples e eficaz.

**Minha opinião:** As abas complementam a sidebar (#06). Podem ser implementadas juntas ou separadas. Recomendo usar a estrutura:
```
[Sidebar] | [Abas: Galeria | Brain | Upload]
```

---

### #08 — Feature: Busca full-text nas fotos

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Verificações:**
- `grep "/api/buscar"` → 0 resultados
- `grep "LIKE"` em app.py → 0 resultados (apenas em database.py para palavras)

**Solução proposta no roadmap:** ✅ Correta (endpoint LIKE simples).

**Minha opinião:** A solução básica funciona, mas no futuro considerar:
- SQLite FTS (Full-Text Search) para buscas mais rápidas
- Destaque do termo encontrado nos resultados
- Busca em tempo real (debounce)

---

### #09 — Qualidade: Try/catch no frontend

**Status Atual:** ⚠️ **PARCIAL** (2 de 11 functions)

**Verificação detalhada:**
```javascript
// Funções com try/catch:
- enviarFotos()         → ✅ Linhas 232-246
- extrairOCR()          → ✅ Linhas 112-128

// Funções SEM try/catch (potencialmente problemáticas):
- carregarFotos()       → ❌ Linhas 26-36
- abrirFoto()           → ❌ Linhas 78-97  
- carregarPalavras()    → ❌ Linhas 256-285
- carregarGrupos()      → ❌ Linhas 287-297
- salvarTexto()         → ⚠️ Linhas 147-155 (sem erro)
```

**Problema:** 9 de 11 chamadas fetch não têm tratamento de erro adequado.

**Solução proposta:** ✅ Essencial.

**Minha opinião:** Crítico para estabilidade. Implementar padrão global de erro:
```javascript
// Pattern recomendado
async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    mostrarErro(e.message);
    throw e;
  }
}
```

---

### #10 — Qualidade: Conexão SQLite com context manager

**Status Atual:** ❌ **NÃO IMPLEMENTADO**

**Verificação:**
```python
# database.py - 9x conn.close() manual encontrado
# Todas as funções: abrir → executar → fechar manualmente
```

**Problema confirmado:** Código verboso e propenso a vazamentos se exceção ocorrer antes do close().

**Solução proposta:** ✅ Perfeita, usando contextlib.

**Minha opinião:** MELHORIA TÉCNICA OBRIGATÓRIA. O padrão atual é propenso a bugs em produção. Exemplo do problema:
```python
# PROBLEMA: se algo falhar entre execute e close, conexão vaza
def listar_fotos():
    conn = get_conn()
    rows = conn.execute("SELECT...").fetchall()  # Se exception aqui...
    conn.close()  # ...nunca executa
    return [dict(r) for r in rows]
```

---

## PROBLEMAS ADICIONAIS ENCONTRADOS (fora roadmap)

### P11 — Debug=True em produção
**Local:** `app.py:113`
```python
app.run(host="0.0.0.0", port=5000, debug=True)
```
**Severidade:** 🔴 Crítica

---

### P12 — Sem autenticação
**Severidade:** 🔴 Crítica

---

### P13 — CSS LANCZOS deprecated
**Local:** `ocr_engine.py:49`
```python
img = img.resize((w * 2, h * 2), Image.LANCZOS)  # Deprecation warning
```
**Severidade:** 🟡 Baixa (funciona, mas warning)

---

### P14 — Stopwords duplicadas
**Local:** `config.py:38-40`
```python
"pelo", "pela", "pelo",  # duplicado
"uma",  # duplicado em diferentes linhas
```
**Severidade:** 🟡 Baixa

---

### P15 — Inconsistência no return type
**Local:** `database.py:86`
```python
return id_  # pode ser None se INSERT falhar
```
**Severidade:** 🟠 Média

---

### P16 — Filename pode ser None
**Local:** `app.py:63`
```python
resultado = salvar_upload(file.read(), file.filename)  # filename pode ser None
```
**Severidade:** 🟠 Média

---

## ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

| # | Tarefa | Tipo | Severidade | Dependências |
|---|--------|------|------------|---------------|
| 01 | #01 Fotos duplicadas | Bug | 🔴 Alta | Nenhuma |
| 02 | #09 Try/catch frontend | Qualidade | 🔴 Alta | Nenhuma |
| 03 | #04 Deletar foto | Feature | 🔴 Alta | #01 (se resolver duplicates) |
| 04 | #02 Hash MD5 upload | Bug | 🟠 Média | #01 |
| 05 | #10 Context manager DB | Qualidade | 🟠 Média | Nenhuma |
| 06 | #03 Modal OCR | Bug | 🟠 Média | Nenhuma |
| 07 | #05 Tema claro/escuro | Feature | 🟡 Baixa | Nenhuma |
| 08 | #08 Busca full-text | Feature | 🟡 Baixa | Nenhuma |
| 09 | #07 Abas | UX | 🟡 Baixa | #06 |
| 10 | #06 Sidebar | UX | 🟡 Baixa | #07, #09 |

---

## OPINIÃO PROFISSIONAL

### Pontos Fortes do Roadmap
1. **Priorização correta** - Bugs críticos primeiro
2. **Soluções detalhadas** - Cada item tem código de exemplo
3. **Visão UX** - Não apenas bugs, mas experiência do usuário
4. **Qualidade de código** - Items 09 e 10 melhoram manutenibilidade

### Pontos de Atenção
1. **Faltaitem de segurança** - Auth não está no roadmap (deveria ser #0)
2. **Sem testes** - Nenhum item sobre testes unitários
3. **Escalabilidade** - SQLite pode ser limitante no futuro
4. **Versionamento** - Não há plano de migração de banco

### O que eu faria diferente
1. Adicionar autenticação como #00 (antes de tudo)
2. Adicionar testes como item obrigatório
3. Adicionar Docker/docker-compose
4. Planejar migração para PostgreSQL a longo prazo

---

## IDEAS DE EVOLUÇÃO (além do roadmap)

### Curto prazo (v1.2)
- [ ] Autenticação (Flask-Login)
- [ ] Rate limiting
- [ ] Testes pytest (coverage > 70%)
- [ ] Docker local

### Médio prazo (v1.3)
- [ ] PostgreSQL (substituir SQLite)
- [ ] Celery para OCR assíncrono
- [ ] WebSocket para progresso de OCR
- [ ] Export para Obsidian

### Longo prazo (v2.0)
- [ ] Multi-usuário
- [ ] API RESTful completa
- [ ] Deploy em cloud (Vercel/Render/Heroku)
- [ ] ML para categorização automática

---

## MEMÓRIA DO PROJETO (para referência futura)

### Stack
- **Backend:** Flask (Python)
- **Database:** SQLite
- **OCR:** Tesseract (pytesseract)
- **Frontend:** Vanilla JS + CSS custom
- **Templates:** Jinja2

### Estrutura de arquivos
```
gigubrain/
├── app.py              # 113 linhas - API Flask
├── config.py           # 46 linhas - Configurações
├── database.py         # 178 linhas - SQLite
├── file_manager.py     # 69 linhas - Gestão arquivos
├── ocr_engine.py      # 124 linhas - OCR + limpeza
├── gigu_brain.db      # SQLite (não commitado)
├── gigu_brain_v1.1_roadmap.md  # Roadmap atual
├── RELATORIOS/
│   ├── relatorio01.md # Análise geral
│   └── relatorio02.md # Este relatório
├── static/
│   ├── app.js         # 311 linhas - Frontend
│   └── style.css     # 376 linhas - UI
├── templates/
│   └── index.html    # 93 linhas
└── fotos/           # Diretório de fotos (não commitado)
```

### Bugs críticos conhecidos
1. `registrar_fotos_existentes()` duplica fotos
2. Sem hash para duplicatas
3. Sem autenticação
4. Debug=True em produção

### Padrões de código
- Funções pequenas e focadas
- Nomes em português (pt-BR)
- Feedback visual no frontend (status messages)
- CSS variables para theming

---

## RESUMO FINAL

O roadmap v1.1 é **sólido e bem_prioritado**. As 10 tarefas cobrem:
- 3 bugs críticos
- 5 features importantes
- 2 melhorias de qualidade

**Minha recomendação:** Implementar na ordem sugerida, mas adicionar autenticação como prioridade zero. O projeto tem potencial para crescer significativamente.

---

*Relatório gerado por Sisyphus AI - Projeto GigU Brain*
