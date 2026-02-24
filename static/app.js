let todasFotos = [];
let fotosNaFila = [];
let filtroStatus = "todos";
let ultimoDossieTermo = "";

document.addEventListener("DOMContentLoaded", () => {
  const temaSalvo = localStorage.getItem("gigu-tema") || "light";
  document.documentElement.setAttribute("data-theme", temaSalvo);
  document.getElementById("theme-icon").textContent = temaSalvo === "dark" ? "🌙" : "☀️";
  
  carregarFotos();
  carregarPalavras();
  carregarGrupos();
  carregarUsuarios();
  carregarRepos();
  setupUpload();
  setupGaleriaAutoScroll();
  initDossieUI();
});

function toggleTheme() {
  const atual = document.documentElement.getAttribute("data-theme");
  const novo = atual === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", novo);
  localStorage.setItem("gigu-tema", novo);
  document.getElementById("theme-icon").textContent = novo === "dark" ? "🌙" : "☀️";
}

function atualizarStats(fotos, palavras) {
  document.getElementById("stat-fotos").textContent = `${fotos} fotos`;
  document.getElementById("stat-palavras").textContent = `${palavras} palavras`;
}

function trocarAba(aba, el) {
  document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
  if (el) el.classList.add("active");
  document.getElementById(`tab-${aba}`).style.display = "block";
  if (aba === "brain") carregarPalavras();
  if (aba === "timeline") carregarTimeline();
  if (aba === "clusters") carregarClusters();
  if (aba === "grafo") carregarGrafo();
}

function filtrarStatus(status, el) {
  filtroStatus = status;
  document.querySelectorAll(".filter").forEach(b => b.classList.remove("active"));
  if (el) el.classList.add("active");
  renderGaleria();
}

async function carregarFotos() {
  try {
    const res = await fetch("/api/fotos");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    todasFotos = await res.json();
    renderGaleria();
    const palavras = await fetch("/api/palavras?limit=1").then(r => r.json());
    atualizarStats(todasFotos.length, palavras.length > 0 ? '80+' : 0);
  } catch (e) {
    console.error("Erro ao carregar fotos:", e);
  }
}

async function rebuildEmbeddings() {
  const btn = document.querySelector("#tab-clusters .btn-embeddings");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Atualizando...";
  }
  try {
    const res = await fetch("/api/embeddings/rebuild", { method: "POST" });
    const data = await res.json();
    if (!data.sucesso) {
      alert(data.erro || "Erro ao gerar vetores");
    }
  } catch (e) {
    alert("Erro ao gerar vetores");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Atualizar Vetores";
    }
  }
  carregarClusters();
  carregarGrafo();
}

async function carregarSimilares(numero) {
  const container = document.getElementById("similares-list");
  if (!container) return;
  container.innerHTML = "";
  if (!numero) return;
  try {
    const res = await fetch(`/api/fotos/${numero}/similares?limit=8`);
    const data = await res.json();
    if (!data.length) {
      container.innerHTML = `<div class="empty-state">Sem similares</div>`;
      return;
    }
    container.innerHTML = data.map(item => `
      <div class="similares-item" onclick="loadPhotoFromGallery('${item.numero}')">
        <img src="/api/foto/imagem/${item.numero}" alt="Foto ${item.numero}" onerror="this.style.display='none'">
        <div class="similares-score">${item.score.toFixed(2)}</div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<div class="empty-state">Erro ao carregar</div>`;
  }
}

async function carregarClusters() {
  const grid = document.getElementById("clusters-grid");
  if (!grid) return;
  grid.innerHTML = "";
  try {
    const res = await fetch("/api/clusters/semana");
    const data = await res.json();
    const clusters = data.clusters || [];
    if (!clusters.length) {
      grid.innerHTML = `<div class="empty-state">Sem clusters nesta semana</div>`;
      return;
    }
    grid.innerHTML = clusters.map(c => `
      <div class="cluster-card">
        <div class="clusters-title">Cluster ${c.id + 1}</div>
        <div class="cluster-size">${c.total} fotos</div>
        <div class="cluster-terms">
          ${c.termos.map(t => `<span class="cluster-tag">${t}</span>`).join("")}
        </div>
      </div>
    `).join("");
  } catch (e) {
    grid.innerHTML = `<div class="empty-state">Erro ao carregar clusters</div>`;
  }
}

async function carregarGrafo() {
  const container = document.getElementById("grafo-area");
  if (!container) return;
  container.innerHTML = "";
  try {
    const res = await fetch("/api/grafo");
    const data = await res.json();
    if (!data.nodes || !data.nodes.length) {
      container.innerHTML = `<div class="empty-state">Sem conexões suficientes</div>`;
      return;
    }
    renderGrafo(data);
  } catch (e) {
    container.innerHTML = `<div class="empty-state">Erro ao carregar grafo</div>`;
  }
}

function renderGrafo(data) {
  const container = document.getElementById("grafo-area");
  if (!container || !window.d3) return;
  container.innerHTML = "";
  const width = container.clientWidth || 800;
  const height = Math.max(container.clientHeight, 520);
  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const color = d3.scaleOrdinal(d3.schemeTableau10);
  const links = data.links.map(d => ({ ...d }));
  const nodes = data.nodes.map(d => ({ ...d }));

  const link = svg.append("g")
    .attr("stroke", "rgba(148,163,184,0.5)")
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("stroke-width", d => Math.max(1, d.value * 2));

  const node = svg.append("g")
    .selectAll("circle")
    .data(nodes)
    .enter()
    .append("circle")
    .attr("r", 7)
    .attr("fill", d => color(d.cluster || 0))
    .call(d3.drag()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      })
    );

  node.append("title").text(d => `#${d.id}`);

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(90))
    .force("charge", d3.forceManyBody().strength(-160))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide(20));

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);
    node
      .attr("cx", d => d.x)
      .attr("cy", d => d.y);
  });
}

function renderGaleria() {
  const grid = document.getElementById("galeria-grid");
  let fotos = filtroStatus === "todos" ? todasFotos : todasFotos.filter(f => f.status === filtroStatus);

  if (!fotos.length) {
    grid.innerHTML = `<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg><p>Nenhuma foto encontrada</p></div>`;
    return;
  }

  grid.innerHTML = fotos.map(f => `
    <div class="foto-card" draggable="true" ondragstart="handleDragStart(event, '${f.numero}')" onclick="loadPhotoFromGallery('${f.numero}')">
      <img src="/api/foto/imagem/${f.numero}" alt="Foto ${f.numero}" loading="lazy" onerror="this.style.display='none'">
      <div class="foto-card-info">
        <span class="foto-numero">#${f.numero}</span>
        <span class="foto-status-badge ${f.status === 'ocr_feito' ? 'done' : 'pending'}"></span>
      </div>
    </div>
  `).join("");
}

let dragNumero = null;
let autoScrollInterval = null;

// Auto-scroll when dragging near edges of gallery
function setupGaleriaAutoScroll() {
  const galleryContainer = document.querySelector('.content');
  const galleryGrid = document.getElementById('galeria-grid');
  
  const doAutoScroll = (e, container) => {
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const edgeThreshold = 100;
    const fromTop = e.clientY - rect.top;
    const fromBottom = rect.bottom - e.clientY;
    if (autoScrollInterval) {
      clearInterval(autoScrollInterval);
      autoScrollInterval = null;
    }
    
    // Scroll up (content goes up) when dragging near bottom of screen
    if (fromBottom < edgeThreshold && container.scrollTop > 0) {
      autoScrollInterval = setInterval(() => {
        if (container.scrollTop > 0) {
          container.scrollBy({ top: -10, behavior: 'instant' });
        }
      }, 16);
    }
    // Scroll down when dragging near top of screen
    else if (fromTop < edgeThreshold) {
      autoScrollInterval = setInterval(() => {
        container.scrollBy({ top: 10, behavior: 'instant' });
      }, 16);
    }
  };
  
  const stopAutoScroll = () => {
    if (autoScrollInterval) {
      clearInterval(autoScrollInterval);
      autoScrollInterval = null;
    }
  };
  
  // Listen on content area
  if (galleryContainer) {
    galleryContainer.addEventListener('dragover', (e) => doAutoScroll(e, galleryContainer));
    galleryContainer.addEventListener('dragleave', stopAutoScroll);
    galleryContainer.addEventListener('drop', stopAutoScroll);
  }
  
  // Also listen on the gallery grid for better detection
  if (galleryGrid) {
    galleryGrid.addEventListener('dragover', (e) => doAutoScroll(e, galleryContainer));
    galleryGrid.addEventListener('dragleave', stopAutoScroll);
  }
}

function handleDragStart(e, numero) {
  dragNumero = numero;
  e.dataTransfer.setData("text/plain", numero);
}

function handleGaleriaDrop(e) {
  e.preventDefault();
  const numero = e.dataTransfer.getData("text/plain") || dragNumero;
  if (numero) adicionarFilaOCR(numero);
  dragNumero = null;
}

function adicionarFilaOCR(numero) {
  if (fotosNaFila.find(f => f.numero === numero)) return;
  
  const foto = todasFotos.find(f => f.numero === numero);
  if (!foto) return;
  
  fotosNaFila.push({ numero: numero, status: "pendente", texto: "" });
  renderFilaOCR();
}

function renderFilaOCR() {
  const queue = document.getElementById("ocr-queue");
  
  if (!fotosNaFila.length) {
    queue.innerHTML = `<div class="ocr-empty"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg><p>Arraste fotos da galeria para esta área</p><span>ou clique para selecionar</span></div>`;
    return;
  }
  
  queue.innerHTML = fotosNaFila.map((f, idx) => `
    <div class="ocr-item" data-numero="${f.numero}">
      <div class="ocr-item-col1">
        <img class="ocr-item-img" src="/api/foto/imagem/${f.numero}" alt="Foto ${f.numero}">
        <div class="ocr-item-btns">
          <button class="btn-ocr" onclick="processarOCR('${f.numero}')" ${f.status === 'processando' ? 'disabled' : ''}>
            ${f.status === 'processando' ? '⏳ Processando...' : '⚡ Extrair Texto'}
          </button>
          <button class="btn-limpar" onclick="limparTexto('${f.numero}')" ${!f.texto ? 'disabled' : ''}>🧹 Limpar</button>
          <button class="btn-salvar" onclick="salvarOCR('${f.numero}')" ${!f.texto ? 'disabled' : ''}>💾 Salvar</button>
        </div>
      </div>
      <div class="ocr-item-col2">
        <textarea id="ocr-textarea-${f.numero}" placeholder="O texto extraído aparecerá aqui...">${f.texto}</textarea>
        <div class="ocr-status" id="ocr-status-${f.numero}"></div>
      </div>
    </div>
  `).join("");
}

async function processarOCR(numero) {
  const item = fotosNaFila.find(f => f.numero === numero);
  if (!item) return;
  
  item.status = "processando";
  renderFilaOCR();
  
  const statusEl = document.getElementById(`ocr-status-${numero}`);
  statusEl.textContent = "Processando OCR...";
  statusEl.className = "ocr-status";
  
  try {
    const res = await fetch(`/api/ocr/${numero}`, { method: "POST" });
    const data = await res.json();
    
    if (data.sucesso) {
      item.texto = data.texto_limpo;
      item.status = "pronto";
      document.getElementById(`ocr-textarea-${numero}`).value = data.texto_limpo;
      statusEl.textContent = `✓ ${data.caracteres} caracteres extraídos`;
      statusEl.className = "ocr-status sucesso";
      
      carregarFotos();
      carregarPalavras();
    } else {
      statusEl.textContent = `Erro: ${data.erro}`;
      statusEl.className = "ocr-status erro";
      item.status = "erro";
    }
  } catch (e) {
    statusEl.textContent = "Erro de conexão";
    statusEl.className = "ocr-status erro";
    item.status = "erro";
  }
  
  renderFilaOCR();
}

function limparTexto(numero) {
  const item = fotosNaFila.find(f => f.numero === numero);
  if (!item) return;
  
  const textarea = document.getElementById(`ocr-textarea-${numero}`);
  const linhas = textarea.value.split("\n");
  const limpas = linhas
    .map(l => l.trim())
    .filter(l => l.length > 2)
    .filter(l => !/^\d{1,2}:\d{2}/.test(l))
    .filter(l => !/^[<>|]{2,}$/.test(l))
    .filter(l => !/(Publicar|Seguir|Curtir|Salvo|YouTube|Instagram)/i.test(l));
  
  item.texto = limpas.join("\n");
  textarea.value = item.texto;
  
  const statusEl = document.getElementById(`ocr-status-${numero}`);
  statusEl.textContent = "✓ Texto limpo";
  statusEl.className = "ocr-status sucesso";
}

async function salvarOCR(numero) {
  const item = fotosNaFila.find(f => f.numero === numero);
  if (!item) return;
  
  const texto = document.getElementById(`ocr-textarea-${numero}`).value;
  
  try {
    await fetch(`/api/ocr/${numero}/salvar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto })
    });
    
    const statusEl = document.getElementById(`ocr-status-${numero}`);
    statusEl.textContent = "💾 Salvo!";
    statusEl.className = "ocr-status sucesso";
    
    carregarFotos();
    carregarPalavras();
  } catch (e) {
    const statusEl = document.getElementById(`ocr-status-${numero}`);
    statusEl.textContent = "Erro ao salvar";
    statusEl.className = "ocr-status erro";
  }
}

function setupUpload() {
  const input = document.getElementById("input-fotos");
  input.addEventListener("change", () => adicionarArquivos([...input.files]));
}

function adicionarArquivos(files) {
  const validos = files.filter(f => f.type.startsWith("image/"));
  if (!validos.length) return;
  
  const form = new FormData();
  validos.forEach(f => form.append("fotos", f));
  
  fetch("/api/upload", { method: "POST", body: form })
    .then(r => r.json())
    .then(data => {
      carregarFotos();
    })
    .catch(e => console.error("Erro no upload:", e));
}

const CORES = ["#007aff", "#34c759", "#ff9500", "#ff3b30", "#af52de", "#00c7be", "#ff2d55", "#5856d6", "#ffcc00"];

async function carregarPalavras() {
  try {
    const palavras = await fetch("/api/palavras?limit=80").then(r => r.json());
    if (!palavras.length) {
      const palavras = await fetch("/api/palavras?limit=1").then(r => r.json());
    atualizarStats(todasFotos.length, palavras.length > 0 ? '80+' : 0);
      return;
    }
    
    const max = palavras[0].contagem;
    const cloud = document.getElementById("word-cloud");
    
    cloud.innerHTML = palavras.map((p, i) => {
      const tamanho = 12 + Math.round((p.contagem / max) * 18);
      const cor = CORES[i % CORES.length];
      return `<span class="word-tag" style="font-size:${tamanho}px; background:${cor}15; color:${cor}; border:1px solid ${cor}30">${p.palavra}</span>`;
    }).join("");
    
    const top = document.getElementById("top-palavras");
    top.innerHTML = palavras.slice(0, 20).map(p => `<div class="palavra-item"><span>${p.palavra}</span><span class="count">${p.contagem}</span></div>`).join("");
    
    const sidebarTop = document.getElementById("top-palavras-sidebar");
    if (sidebarTop) {
      sidebarTop.innerHTML = palavras.slice(0, 10).map(p => `<div class="palavra-item"><span>${p.palavra}</span><span class="count">${p.contagem}</span></div>`).join("");
    }
    
    atualizarStats(todasFotos.length, palavras.length);
  } catch (e) {
    console.error("Erro ao carregar palavras:", e);
  }
}

async function carregarGrupos() {
  try {
    const grupos = await fetch("/api/grupos").then(r => r.json());
    const container = document.getElementById("grupos-filtro");
    container.innerHTML = `<div class="grupo-item active">Todos</div>` +
      grupos.map(g => `<div class="grupo-item" style="border-left:3px solid ${g.cor}">${g.nome}</div>`).join("");
  } catch (e) {
    console.error("Erro ao carregar grupos:", e);
  }
}

async function carregarUsuarios() {
  try {
    const usuarios = await fetch("/api/usuarios?limit=15").then(r => r.json());
    const container = document.getElementById("top-usuarios-sidebar");
    if (!usuarios.length) {
      container.innerHTML = `<div class="palavra-item"><span style="color:var(--text-secondary)">Nenhum @user encontrado</span></div>`;
      return;
    }
    container.innerHTML = usuarios.map(u => 
      `<div class="palavra-item user-item"><span>@${u.username}</span><span class="count">${u.contagem}</span></div>`
    ).join("");
  } catch (e) {
    console.error("Erro ao carregar usuarios:", e);
  }
}

async function carregarRepos() {
  try {
    const repos = await fetch("/api/repos?limit=15").then(r => r.json());
    const container = document.getElementById("top-repos-sidebar");
    if (!repos.length) {
      container.innerHTML = `<div class="palavra-item"><span style="color:var(--text-secondary)">Nenhum repo encontrado</span></div>`;
      return;
    }
    container.innerHTML = repos.map(r => 
      `<div class="palavra-item repo-item"><span>${r.repo}</span><span class="count">${r.contagem}</span></div>`
    ).join("");
  } catch (e) {
    console.error("Erro ao carregar repos:", e);
  }
}

let currentPhotoNumero = null;

function handlePhotoSelect(input) {
  const file = input.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = document.getElementById("preview-img");
    const dropText = document.getElementById("drop-text");
    
    img.src = e.target.result;
    img.style.display = "block";
    dropText.style.display = "none";
    
    document.getElementById("btn-extrair").disabled = false;
  };
  reader.readAsDataURL(file);
}

function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("photo-drop").classList.add("drag-over");
}

function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("photo-drop").classList.remove("drag-over");
}

function handleDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  document.getElementById("photo-drop").classList.remove("drag-over");
  
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    const file = files[0];
    if (file.type.startsWith("image/")) {
      const input = document.getElementById("photo-input");
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      handlePhotoSelect(input);
    }
  } else {
    const numero = e.dataTransfer.getData("text/plain");
    if (numero) {
      loadPhotoFromGallery(numero);
    }
  }
}

async function runOCRForPhoto(numero) {
  const statusEl = document.getElementById("ocr-status");
  const btnExtrair = document.getElementById("btn-extrair");
  const btnLimpar = document.getElementById("btn-limpar");
  const btnSalvar = document.getElementById("btn-salvar");
  const textarea = document.getElementById("ocr-text");
  
  btnExtrair.disabled = true;
  btnExtrair.textContent = "⏳ Processando...";
  statusEl.textContent = "Executando OCR...";
  statusEl.className = "ocr-status";
  
  try {
    const ocrRes = await fetch(`/api/ocr/${numero}`, { method: "POST" });
    const ocrData = await ocrRes.json();
    
    if (ocrData.sucesso) {
      textarea.value = ocrData.texto_limpo;
      statusEl.textContent = `✓ ${ocrData.caracteres} caracteres extraídos`;
      statusEl.className = "ocr-status sucesso";
      btnLimpar.disabled = false;
      btnSalvar.disabled = false;
      carregarFotos();
      carregarPalavras();
      carregarSimilares(numero);
      carregarUsuarios();
      carregarRepos();
    } else {
      statusEl.textContent = `Erro: ${ocrData.erro}`;
      statusEl.className = "ocr-status erro";
    }
  } catch (e) {
    statusEl.textContent = "Erro de conexão";
    statusEl.className = "ocr-status erro";
  }
  
  btnExtrair.disabled = false;
  btnExtrair.textContent = "⚡ Extrair Texto";
}

async function executarOCR() {
  const input = document.getElementById("photo-input");
  const file = input.files[0];
  
  if (!file && !currentPhotoNumero) return;
  
  if (currentPhotoNumero && !file) {
    await runOCRForPhoto(currentPhotoNumero);
    return;
  }
  
  const statusEl = document.getElementById("ocr-status");
  const btnExtrair = document.getElementById("btn-extrair");
  const btnLimpar = document.getElementById("btn-limpar");
  const btnSalvar = document.getElementById("btn-salvar");
  const textarea = document.getElementById("ocr-text");
  
  btnExtrair.disabled = true;
  btnExtrair.textContent = "⏳ Processando...";
  statusEl.textContent = "Enviando foto...";
  statusEl.className = "ocr-status";
  
  try {
    const formData = new FormData();
    formData.append("fotos", file);
    
    const uploadRes = await fetch("/api/upload", { method: "POST", body: formData });
    const uploadData = await uploadRes.json();
    
    if (!uploadData.resultados || !uploadData.resultados[0].sucesso) {
      const erro = uploadData.resultados?.[0]?.erro || "Erro no upload";
      statusEl.textContent = erro;
      statusEl.className = "ocr-status erro";
      btnExtrair.disabled = false;
      btnExtrair.textContent = "⚡ Extrair Texto";
      return;
    }
    
    currentPhotoNumero = uploadData.resultados[0].numero;
    statusEl.textContent = "Executando OCR...";
    
    const ocrRes = await fetch(`/api/ocr/${currentPhotoNumero}`, { method: "POST" });
    const ocrData = await ocrRes.json();
    
    if (ocrData.sucesso) {
      textarea.value = ocrData.texto_limpo;
      statusEl.textContent = `✓ ${ocrData.caracteres} caracteres extraídos`;
      statusEl.className = "ocr-status sucesso";
      btnLimpar.disabled = false;
      btnSalvar.disabled = false;
      carregarFotos();
      carregarPalavras();
      carregarSimilares(currentPhotoNumero);
    } else {
      statusEl.textContent = `Erro: ${ocrData.erro}`;
      statusEl.className = "ocr-status erro";
    }
  } catch (e) {
    statusEl.textContent = "Erro de conexão";
    statusEl.className = "ocr-status erro";
  }
  
  btnExtrair.disabled = false;
  btnExtrair.textContent = "⚡ Extrair Texto";
}

async function executarAmbosOCR() {
  const input = document.getElementById("photo-input");
  const file = input.files[0];
  
  if (!file && !currentPhotoNumero) return;
  
  const statusEl = document.getElementById("ocr-status");
  const btnExtrair = document.getElementById("btn-extrair");
  const tessTextarea = document.getElementById("tess-text");
  const paddleTextarea = document.getElementById("paddle-text");
  const tessStats = document.getElementById("tess-stats");
  const paddleStats = document.getElementById("paddle-stats");
  
  btnExtrair.disabled = true;
  btnExtrair.textContent = "⏳ Processando...";
  
  let photoNumero = currentPhotoNumero;
  
  try {
    // Upload se necessário
    if (!photoNumero && file) {
      statusEl.textContent = "Enviando foto...";
      const formData = new FormData();
      formData.append("fotos", file);
      
      const uploadRes = await fetch("/api/upload", { method: "POST", body: formData });
      const uploadData = await uploadRes.json();
      
      if (!uploadData.resultados || !uploadData.resultados[0].sucesso) {
        statusEl.textContent = "Erro no upload";
        statusEl.className = "ocr-status erro";
        btnExtrair.disabled = false;
        btnExtrair.textContent = "⚡ Extrair Ambos";
        return;
      }
      
      photoNumero = uploadData.resultados[0].numero;
      currentPhotoNumero = photoNumero;
    }
    
    if (!photoNumero) {
      statusEl.textContent = "Nenhuma foto selecionada";
      return;
    }
    
    // Executar comparação (Tesseract + PaddleOCR)
    statusEl.textContent = "Executando OCRs (Tesseract + PaddleOCR)...";
    
    const compRes = await fetch(`/api/ocr/${photoNumero}/comparar`, { method: "POST" });
    const compData = await compRes.json();
    
    if (compData.tesseract) {
      tessTextarea.value = compData.tesseract.texto || "";
      tessStats.textContent = `${compData.tesseract.caracteres || 0} chars`;
    }
    
    if (compData.paddleocr) {
      paddleTextarea.value = compData.paddleocr.texto || "";
      paddleStats.textContent = `${compData.paddleocr.caracteres || 0} chars`;
    }
    
    if (compData.comparacao) {
      statusEl.textContent = `✓ Comparação concluída - Recomendado: ${compData.comparacao.recomendado}`;
      statusEl.className = "ocr-status sucesso";
    } else {
      statusEl.textContent = "OCR executado";
      statusEl.className = "ocr-status sucesso";
    }
    
    carregarFotos();
    carregarPalavras();
    
  } catch (e) {
    console.error(e);
    statusEl.textContent = "Erro de conexão";
    statusEl.className = "ocr-status erro";
  }
  
  btnExtrair.disabled = false;
  btnExtrair.textContent = "⚡ Extrair Ambos";
}


function limparTexto() {
  const textarea = document.getElementById("ocr-text");
  if (!textarea) return;
  const linhas = textarea.value.split("\n");
  const limpas = linhas
    .map(l => l.trim())
    .filter(l => l.length > 2)
    // Remover timestamps
    .filter(l => !/^\d{1,2}:\d{2}/.test(l))
    // Remover símbolos estranhos
    .filter(l => !/^[<>|]{2,}$/.test(l))
    // Remover palavras-chave de apps
    .filter(l => !/(Publicar|Seguir|Curtir|Salvo|YouTube|Instagram|Facebook|Uber|99|Drive|Giga|R[$]|[Rr]\$\/Km|Hora|Every tl|Traduzido do ingl[eê]s|Translated from English|See translation|Ver tradu[cç][aã]o)/i.test(l))
    // Remover números sozinhos
    .filter(l => !/^\d+[.,]\d+$/.test(l))
    // Filtrar blacklist
    .filter(l => !blacklist.some(b => l.toLowerCase().includes(b.toLowerCase())));
  
  textarea.value = limpas.join("\n");
  const statusEl = document.getElementById("ocr-status");
  statusEl.textContent = `✓ Texto limpo (${limpas.length} linhas)`;
  statusEl.className = "ocr-status sucesso";
}

async function salvarTexto() {
  if (!currentPhotoNumero) return;
  
  const textarea = document.getElementById("ocr-text");
  const texto = textarea.value;
  const statusEl = document.getElementById("ocr-status");
  
  try {
    await fetch(`/api/ocr/${currentPhotoNumero}/salvar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto })
    });
    
    statusEl.textContent = "💾 Salvo!";
    statusEl.className = "ocr-status sucesso";
    carregarFotos();
    carregarPalavras();
    carregarUsuarios();
    carregarRepos();
  } catch (e) {
    statusEl.textContent = "Erro ao salvar";
    statusEl.className = "ocr-status erro";
  }
}

function loadPhotoFromGallery(numero) {
  const img = document.getElementById("preview-img");
  const dropText = document.getElementById("drop-text");
  
  img.src = `/api/foto/imagem/${numero}`;
  img.style.display = "block";
  dropText.style.display = "none";
  
  currentPhotoNumero = numero;
  document.getElementById("btn-extrair").disabled = false;
  document.getElementById("ocr-status").textContent = `Foto #${numero} carregada`;
  carregarSimilares(numero);
}

function clearPhoto() {
  const img = document.getElementById("preview-img");
  const dropText = document.getElementById("drop-text");
  const input = document.getElementById("photo-input");
  
  img.src = "";
  img.style.display = "none";
  dropText.style.display = "flex";
  input.value = "";
  
  currentPhotoNumero = null;
  document.getElementById("btn-extrair").disabled = true;
  document.getElementById("ocr-text").value = "";
  document.getElementById("btn-limpar").disabled = true;
  document.getElementById("btn-salvar").disabled = true;
  document.getElementById("ocr-status").textContent = "";
  const similares = document.getElementById("similares-list");
  if (similares) similares.innerHTML = "";
}

let fotoAtualComparar = null;

async function compararOCR() {
  const input = document.getElementById("photo-input");
  const file = input.files[0];
  
  if (!file && !currentPhotoNumero) {
    alert("Selecione uma foto primeiro");
    return;
  }
  
  let numero = currentPhotoNumero;
  
  if (!numero && file) {
    alert("Faça upload da foto primeiro");
    return;
  }
  
  fotoAtualComparar = numero;
  
  const btn = document.getElementById("btn-comparar");
  btn.disabled = true;
  btn.textContent = "⏳ Processando...";

  try {
    const res = await fetch(`/api/ocr/${numero}/comparar`, { method: "POST" });
    const data = await res.json();

    if (data.erro) {
      alert("Erro: " + data.erro);
      return;
    }

    document.getElementById("tess-area").value = data.tesseract.texto;
    document.getElementById("tess-stats").textContent = `${data.tesseract.caracteres} chars`;

    document.getElementById("paddle-area").value = data.paddleocr.texto;
    document.getElementById("paddle-stats").textContent = `${data.paddleocr.caracteres} chars`;
    document.getElementById("paddle-confianca").textContent = `Confiança: ${data.paddleocr.confianca_media}%`;

    const rec = data.comparacao;
    document.getElementById("recomendacao-box").innerHTML = 
      `🤖 Sistema recomenda: <strong>${rec.recomendado.toUpperCase()}</strong> — ${rec.motivo}`;

    document.getElementById("painel-comparacao").style.display = "block";

  } catch (e) {
    alert("Erro ao comparar: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "⚖ Comparar OCR";
  }
}

async function usarTexto(motor) {
  const texto = motor === "tesseract"
    ? document.getElementById("tess-area").value
    : document.getElementById("paddle-area").value;

  try {
    const res = await fetch(`/api/ocr/${fotoAtualComparar}/salvar-motor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ motor, texto })
    });
    const data = await res.json();

    if (data.sucesso) {
      document.getElementById("ocr-text").value = texto;
      document.getElementById("painel-comparacao").style.display = "none";
      document.getElementById("ocr-status").textContent = 
        `✓ Salvo via ${motor} · ${data.palavras} palavras indexadas`;
      document.getElementById("btn-limpar").disabled = false;
      document.getElementById("btn-salvar").disabled = false;
      carregarFotos();
      carregarPalavras();
    }
  } catch (e) {
    alert("Erro ao salvar: " + e.message);
  }
}

async function carregarTimeline() {
  try {
    const [semanas, meses] = await Promise.all([
      fetch("/api/fotos/por-semana").then(r => r.json()),
      fetch("/api/fotos/por-mes").then(r => r.json())
    ]);

    const mesesContainer = document.getElementById("timeline-meses");
    const semanasContainer = document.getElementById("timeline-semanas");

    const maxMes = Math.max(...meses.map(m => m.total), 1);
    mesesContainer.innerHTML = meses.map(m => `
      <div class="timeline-item" onclick="filtrarPorMes('${m.mes}')">
        <div class="timeline-label">${m.mes}</div>
        <div class="timeline-bar-wrap">
          <div class="timeline-bar" style="width:${(m.total / maxMes) * 100}%"></div>
        </div>
        <div class="timeline-count">${m.total} fotos · ${m.processadas} proc.</div>
      </div>
    `).join("");

    const maxSemana = Math.max(...semanas.map(s => s.total), 1);
    semanasContainer.innerHTML = semanas.map(s => `
      <div class="timeline-item" onclick="verPalavrasSemana('${s.semana}')">
        <div class="timeline-label">${s.semana}</div>
        <div class="timeline-bar-wrap">
          <div class="timeline-bar" style="width:${(s.total / maxSemana) * 100}%"></div>
        </div>
        <div class="timeline-count">${s.total} fotos · ${s.processadas} proc.</div>
      </div>
    `).join("");

  } catch (e) {
    console.error("Erro ao carregar timeline:", e);
  }
}

async function verPalavrasSemana(semana) {
  try {
    const res = await fetch(`/api/palavras/por-semana?semana=${semana}`);
    const palavras = await res.json();

    if (!palavras.length) {
      alert(`Semana ${semana}: nenhuma palavra encontrada`);
      return;
    }

    const lista = palavras.slice(0, 20).map(p => 
      `${p.palavra} (${p.contagem_semana}×)`
    ).join("\n");

    alert(`Semana ${semana}:\n${lista}`);
  } catch (e) {
    alert("Erro: " + e.message);
  }
}

function filtrarPorMes(mes) {
  alert("Filtrar por mês: " + mes + " (implementação futura)");
}

function initDossieUI() {
  const providerSelect = document.getElementById("llm-provider");
  if (!providerSelect) return;
  providerSelect.addEventListener("change", () => ajustarDefaultsLLM(true));
  ajustarDefaultsLLM(false);
}

function ajustarDefaultsLLM(resetModel) {
  const provider = document.getElementById("llm-provider")?.value;
  const baseUrlInput = document.getElementById("llm-base-url");
  const modelInput = document.getElementById("llm-model");
  if (!provider || !baseUrlInput || !modelInput) return;
  const defaults = {
    ollama: { base: "http://localhost:11434", model: "" },
    groq: { base: "https://api.groq.com/openai/v1", model: "" },
    mistral: { base: "https://api.mistral.ai/v1", model: "" },
    gemini: { base: "https://generativelanguage.googleapis.com/v1beta", model: "" },
    glm: { base: "https://open.bigmodel.cn/api/paas/v4", model: "" },
    custom: { base: "", model: "" }
  };
  const def = defaults[provider] || defaults.custom;
  if (!baseUrlInput.value) baseUrlInput.value = def.base;
  if (resetModel) modelInput.value = def.model;
}

async function gerarDossie() {
  const termoInput = document.getElementById("dossie-termo");
  const statusEl = document.getElementById("dossie-status");
  if (!termoInput || !statusEl) return;
  const termo = termoInput.value.trim();
  if (termo.length < 2) {
    statusEl.textContent = "Informe um termo com 2+ caracteres";
    statusEl.className = "dossie-status erro";
    return;
  }
  statusEl.textContent = "Gerando dossiê...";
  statusEl.className = "dossie-status";
  try {
    const res = await fetch(`/api/insights/dossie?termo=${encodeURIComponent(termo)}`);
    const data = await res.json();
    if (!res.ok || data.erro) {
      statusEl.textContent = data.erro || "Erro ao gerar dossiê";
      statusEl.className = "dossie-status erro";
      return;
    }
    ultimoDossieTermo = termo;
    renderDossie(data);
    statusEl.textContent = `Dossiê pronto: ${data.total_fotos} fotos`;
    statusEl.className = "dossie-status sucesso";
  } catch (e) {
    statusEl.textContent = "Erro ao gerar dossiê";
    statusEl.className = "dossie-status erro";
  }
}

function renderDossie(data) {
  const resumoEl = document.getElementById("dossie-resumo");
  const coocEl = document.getElementById("dossie-cooc");
  const usuariosReposEl = document.getElementById("dossie-usuarios-repos");
  const timelineEl = document.getElementById("dossie-timeline");
  const anchorsEl = document.getElementById("dossie-anchors");
  const fotosEl = document.getElementById("dossie-fotos");

  if (resumoEl) {
    const resumo = [
      `Termo: ${data.termo}`,
      `Fotos: ${data.total_fotos}`,
      `Coocorrências: ${data.coocorrencias.length}`,
      `Users: ${data.usuarios.length}`,
      `Repos: ${data.repos.length}`
    ];
    resumoEl.innerHTML = resumo.map(r => `<div class="dossie-pill">${r}</div>`).join("");
  }

  if (coocEl) {
    if (!data.coocorrencias.length) {
      coocEl.innerHTML = `<div class="empty-state">Sem coocorrências</div>`;
    } else {
      coocEl.innerHTML = data.coocorrencias.slice(0, 20).map(c => 
        `<div class="dossie-row"><span>${c.palavra}</span><strong>${c.contagem}</strong></div>`
      ).join("");
    }
  }

  if (usuariosReposEl) {
    const usuarios = data.usuarios.slice(0, 8).map(u => `@${u.username} (${u.contagem})`);
    const repos = data.repos.slice(0, 8).map(r => `${r.repo} (${r.contagem})`);
    usuariosReposEl.innerHTML = `
      <div class="dossie-subtitle">Users</div>
      <div class="dossie-tags">${usuarios.map(u => `<span>${u}</span>`).join("") || "—"}</div>
      <div class="dossie-subtitle">Repos</div>
      <div class="dossie-tags">${repos.map(r => `<span>${r}</span>`).join("") || "—"}</div>
    `;
  }

  if (timelineEl) {
    const semanas = data.timeline?.por_semana || [];
    const meses = data.timeline?.por_mes || [];
    const semanasHtml = semanas.slice(0, 6).map(s => `<div>${s.semana}: ${s.total}</div>`).join("");
    const mesesHtml = meses.slice(0, 6).map(m => `<div>${m.mes}: ${m.total}</div>`).join("");
    timelineEl.innerHTML = `
      <div class="dossie-subtitle">Semanas</div>
      <div class="dossie-timeline">${semanasHtml || "—"}</div>
      <div class="dossie-subtitle">Meses</div>
      <div class="dossie-timeline">${mesesHtml || "—"}</div>
    `;
  }

  if (anchorsEl) {
    if (!data.anchors.length) {
      anchorsEl.innerHTML = `<div class="empty-state">Sem âncoras</div>`;
    } else {
      anchorsEl.innerHTML = data.anchors.map(a => `
        <div class="dossie-anchor" onclick="loadPhotoFromGallery('${a.numero}')">
          <img src="/api/foto/imagem/${a.numero}" alt="Foto ${a.numero}" onerror="this.style.display='none'">
          <div>
            <div><strong>#${a.numero}</strong> · ${a.filename || ""}</div>
            <div class="dossie-meta">ocorrências: ${a.ocorrencias} · score: ${a.score}</div>
          </div>
        </div>
      `).join("");
    }
  }

  if (fotosEl) {
    if (!data.fotos.length) {
      fotosEl.innerHTML = `<div class="empty-state">Sem fotos relacionadas</div>`;
    } else {
      fotosEl.innerHTML = data.fotos.slice(0, 20).map(f => `
        <div class="dossie-foto">
          <img src="/api/foto/imagem/${f.numero}" alt="Foto ${f.numero}" onerror="this.style.display='none'">
          <div class="dossie-foto-info">
            <div><strong>#${f.numero}</strong> · ${f.filename || ""}</div>
            <div class="dossie-meta">${f.trecho || "Sem trecho"}</div>
          </div>
        </div>
      `).join("");
    }
  }
}

async function gerarInsightsLLM() {
  const provider = document.getElementById("llm-provider")?.value || "";
  const model = document.getElementById("llm-model")?.value.trim() || "";
  const baseUrl = document.getElementById("llm-base-url")?.value.trim() || "";
  const apiKey = document.getElementById("llm-api-key")?.value.trim() || "";
  const termoInput = document.getElementById("dossie-termo");
  const statusEl = document.getElementById("llm-status");
  const outputEl = document.getElementById("llm-output");
  const termo = termoInput?.value.trim() || ultimoDossieTermo;

  if (!statusEl || !outputEl) return;
  if (!termo || termo.length < 2) {
    statusEl.textContent = "Defina um termo no dossiê primeiro";
    statusEl.className = "llm-status erro";
    return;
  }
  if (!model) {
    statusEl.textContent = "Informe o modelo";
    statusEl.className = "llm-status erro";
    return;
  }
  if (provider !== "ollama" && !apiKey) {
    statusEl.textContent = "API key obrigatória";
    statusEl.className = "llm-status erro";
    return;
  }

  statusEl.textContent = "Gerando insights...";
  statusEl.className = "llm-status";
  outputEl.textContent = "";

  try {
    const res = await fetch("/api/llm/analisar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        termo,
        provider,
        model,
        base_url: baseUrl,
        api_key: apiKey
      })
    });
    const data = await res.json();
    if (!res.ok || !data.sucesso) {
      statusEl.textContent = data.erro || "Erro ao gerar insights";
      statusEl.className = "llm-status erro";
      if (data.raw) {
        outputEl.textContent = data.raw;
      }
      return;
    }
    statusEl.textContent = "Insights prontos";
    statusEl.className = "llm-status sucesso";
    outputEl.textContent = data.texto || "Sem texto retornado";
  } catch (e) {
    statusEl.textContent = "Erro ao gerar insights";
    statusEl.className = "llm-status erro";
  }
}


async function traduzirTexto() {
  const textarea = document.getElementById("ocr-text");
  if (!textarea || !textarea.value.trim()) {
    alert("Nenhum texto para traduzir");
    return;
  }
  const statusEl = document.getElementById("ocr-status");
  statusEl.textContent = "Traduzindo...";
  statusEl.className = "ocr-status";
  const texto = textarea.value;
  
  try {
    const encodedText = encodeURIComponent(texto);
    const response = await fetch(`https://api.mymemory.translated.net/get?q=${encodedText}&langpair=en|pt`);
    
    if (!response.ok) throw new Error("Tradução falhou");
    
    const data = await response.json();
    
    if (data.responseStatus === 200 && data.responseData.translatedText) {
      textarea.value = data.responseData.translatedText;
      statusEl.textContent = "✓ Traduzido para Português";
      statusEl.className = "ocr-status sucesso";
    } else {
      throw new Error(data.responseDetails || "Tradução falhou");
    }
  } catch (e) {
    statusEl.textContent = "Erro na tradução: " + e.message;
    statusEl.className = "ocr-status erro";
  }
}

let blacklist = [];

async function adicionarALixeira() {
  const textarea = document.getElementById("lixeira-text");
  if (!textarea || !textarea.value.trim()) return;
  const lines = textarea.value.split("\n").map(l => l.trim()).filter(l => l.length > 0);
  
  try {
    const res = await fetch("/api/blacklist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ textos: lines })
    });
    const data = await res.json();
    if (data.blacklist) {
      blacklist = data.blacklist.map(b => b.texto);
    }
    alert(`${lines.length} texto(s) adicionado(s) à blacklist!\nTotal: ${blacklist.length} itens`);
    textarea.value = "";
  } catch (e) {
    console.error("Erro ao salvar blacklist:", e);
  }
}

async function carregarBlacklist() {
  try {
    const res = await fetch("/api/blacklist");
    const data = await res.json();
    blacklist = data.map(b => b.texto);
  } catch (e) { blacklist = []; }
}
carregarBlacklist();
