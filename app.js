/* ============================================================
   CONFIGURAÇÃO — altere aqui para apontar para uma API REST
   Ex.: const API_BASE = "https://api.exemplo.ao/v1/eleicoes/1992";
   ============================================================ */
const API_BASE = "data"; // pasta estática local

const ENDPOINTS = {
  eleicao:      `${API_BASE}/eleicao.json`,
  partidos:     `${API_BASE}/partidos.json`,
  candidatos:   `${API_BASE}/candidatos_presidenciais.json`,
  parlamentar:  `${API_BASE}/resultados_parlamentares.json`,
  timeline:     `${API_BASE}/timeline.json`
};

/* ============================================================
   HELPERS
   ============================================================ */
const fmtInt = n => n == null ? "—" : n.toLocaleString("pt-PT");
const fmtPct = n => n == null ? "—" : n.toFixed(2) + "%";

/**
 * fetchJSON — wrapper de fetch com verificação de erro HTTP
 * (substituível por XMLHttpRequest se necessário; ver função XHR abaixo)
 */
async function fetchJSON(url) {
  const resp = await fetch(url, { cache: "no-cache" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ao obter ${url}`);
  return resp.json();
}

/**
 * Variante XHR (comentada) — para ambientes sem fetch.
 * Basta trocar fetchJSON por fetchJSON_XHR nas chamadas abaixo.
 *
 * function fetchJSON_XHR(url) {
 *   return new Promise((resolve, reject) => {
 *     const xhr = new XMLHttpRequest();
 *     xhr.open("GET", url);
 *     xhr.responseType = "json";
 *     xhr.onload = () => (xhr.status >= 200 && xhr.status < 300)
 *       ? resolve(xhr.response)
 *       : reject(new Error(`HTTP ${xhr.status}`));
 *     xhr.onerror = () => reject(new Error("Erro de rede"));
 *     xhr.send();
 *   });
 * }
 */

/* ============================================================
   ESTADO GLOBAL
   ============================================================ */
let state = {
  eleicao: null,
  partidos: [],
  candidatos: [],
  parlamentar: [],
  timeline: []
};

const partidoById = id =>
  state.partidos.find(p => p.id_partido === id) ||
  { sigla: "Ind.", nome_completo: "Independente" };

/* ============================================================
   CARREGAMENTO DE DADOS
   ============================================================ */
async function carregarDados() {
  try {
    const [eleicao, partidos, candidatos, parlamentar, timeline] =
      await Promise.all([
        fetchJSON(ENDPOINTS.eleicao),
        fetchJSON(ENDPOINTS.partidos),
        fetchJSON(ENDPOINTS.candidatos),
        fetchJSON(ENDPOINTS.parlamentar),
        fetchJSON(ENDPOINTS.timeline)
      ]);

    state = { eleicao, partidos, candidatos, parlamentar, timeline };

    document.getElementById("loader").hidden = true;
    document.getElementById("conteudo").hidden = false;

    renderKPIs();
    renderTimeline();
    renderTabelaPresidenciais();
    renderTabelaParlamentares();
    initDataTables();
    initFiltrosPresidenciais();
    renderGraficos();
  } catch (err) {
    console.error(err);
    const erroEl = document.getElementById("erro");
    erroEl.hidden = false;
    erroEl.textContent = `Falha ao carregar dados: ${err.message}. ` +
      `Verifique se os ficheiros JSON existem em "${API_BASE}/" ou se o servidor está a correr.`;
    document.getElementById("loader").hidden = true;
  }
}

/* ============================================================
   KPIs
   ============================================================ */
function renderKPIs() {
  const e = state.eleicao;
  document.getElementById("kpi-inscritos").textContent   = fmtInt(e.eleitores_inscritos);
  document.getElementById("kpi-votantes").textContent    = fmtInt(e.votantes);
  document.getElementById("kpi-participacao").textContent = e.taxa_participacao + "%";
}

/* ============================================================
   TIMELINE
   ============================================================ */
function renderTimeline() {
  const cont = document.getElementById("timeline-container");
  cont.innerHTML = "";
  state.timeline.forEach(ev => {
    const [ano, mes, dia] = ev.data.split("-");
    const div = document.createElement("div");
    div.className = "timeline-item";
    div.innerHTML = `
      <div class="data">${dia}/${mes}/${ano}</div>
      <div class="titulo">${ev.titulo}</div>
      <div class="descricao">${ev.descricao}</div>`;
    cont.appendChild(div);
  });
}

/* ============================================================
   TABELA PRESIDENCIAIS
   ============================================================ */
function renderTabelaPresidenciais() {
  const tbody = document.querySelector("#tabela-presidenciais tbody");
  tbody.innerHTML = "";
  state.candidatos.forEach(c => {
    const p = c.id_partido ? partidoById(c.id_partido)
                           : { sigla: "Ind.", nome_completo: "Independente (apoiado pelo PNDA)" };
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${c.posicao}</td>
      <td>${c.nome_candidato}</td>
      <td>${p.sigla}</td>
      <td>${p.nome_completo}</td>
      <td>${fmtInt(c.votos)}</td>
      <td>${fmtPct(c.percentagem)}</td>`;
    tbody.appendChild(tr);
  });
}

/* ============================================================
   TABELA PARLAMENTARES
   ============================================================ */
function renderTabelaParlamentares() {
  const tbody = document.querySelector("#tabela-parlamentares tbody");
  tbody.innerHTML = "";
  state.parlamentar
    .slice()
    .sort((a, b) => b.assentos - a.assentos || (b.percentagem || 0) - (a.percentagem || 0))
    .forEach(r => {
      const p = partidoById(r.id_partido);
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${p.sigla}</td>
        <td>${p.nome_completo}</td>
        <td>${fmtInt(r.votos)}</td>
        <td>${fmtPct(r.percentagem)}</td>
        <td>${r.assentos}</td>`;
      tbody.appendChild(tr);
    });
}

/* ============================================================
   DATATABLES
   ============================================================ */
function initDataTables() {
  $("#tabela-presidenciais").DataTable({
    language: { url: "https://cdn.datatables.net/plug-ins/1.13.6/i18n/pt-PT.json" },
    order: [[5, "desc"]],
    pageLength: 15
  });
  $("#tabela-parlamentares").DataTable({
    language: { url: "https://cdn.datatables.net/plug-ins/1.13.6/i18n/pt-PT.json" },
    order: [[4, "desc"]],
    pageLength: 15
  });
}

/* ============================================================
   FILTROS POR PARTIDO (PRESIDENCIAIS)
   ============================================================ */
function initFiltrosPresidenciais() {
  const filtrosDiv = document.getElementById("filtros-presidenciais");
  filtrosDiv.innerHTML = "";

  const siglas = [...new Set(state.candidatos.map(c =>
    c.id_partido ? partidoById(c.id_partido).sigla : "Ind."))];

  const btnTodos = document.createElement("button");
  btnTodos.className = "btn-filtro ativo";
  btnTodos.textContent = "Todos";
  btnTodos.dataset.sigla = "TODOS";
  filtrosDiv.appendChild(btnTodos);

  siglas.forEach(sig => {
    const b = document.createElement("button");
    b.className = "btn-filtro";
    b.textContent = sig;
    b.dataset.sigla = sig;
    filtrosDiv.appendChild(b);
  });

  filtrosDiv.addEventListener("click", e => {
    if (!e.target.classList.contains("btn-filtro")) return;
    filtrosDiv.querySelectorAll(".btn-filtro").forEach(b => b.classList.remove("ativo"));
    e.target.classList.add("ativo");
    const sig = e.target.dataset.sigla;
    const table = $("#tabela-presidenciais").DataTable();
    if (sig === "TODOS") table.column(2).search("").draw();
    else table.column(2).search("^" + sig + "$", true, false).draw();
  });
}

/* ============================================================
   GRÁFICOS (Chart.js)
   ============================================================ */
function renderGraficos() {
  /* --- Barras: Assentos --- */
  const dadosAssentos = state.parlamentar.slice().sort((a, b) => b.assentos - a.assentos);
  new Chart(document.getElementById("grafico-assentos"), {
    type: "bar",
    data: {
      labels: dadosAssentos.map(r => partidoById(r.id_partido).sigla),
      datasets: [{
        label: "Assentos na Assembleia Nacional",
        data: dadosAssentos.map(r => r.assentos),
        backgroundColor: dadosAssentos.map(r =>
          r.id_partido === 1 ? "#1a3d6d" :
          r.id_partido === 2 ? "#b22222" : "#7a8ca8"),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Distribuição de Assentos — 1992", font: { size: 14 } },
        legend: { display: false }
      },
      scales: { y: { beginAtZero: true, title: { display: true, text: "Assentos" } } }
    }
  });

  /* --- Doughnut: Presidenciais --- */
  const principais = state.candidatos.filter(c => c.percentagem >= 2);
  const outrosPct = state.candidatos
    .filter(c => c.percentagem < 2)
    .reduce((s, c) => s + c.percentagem, 0);

  const labels = principais.map(c => c.nome_candidato.split(" ").slice(-2).join(" "));
  labels.push("Outros");
  const data = principais.map(c => c.percentagem);
  data.push(parseFloat(outrosPct.toFixed(2)));

  new Chart(document.getElementById("grafico-presidenciais"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: ["#1a3d6d","#b22222","#e6a817","#3c8d5a","#7a4fa3","#c26b2b","#4a7fa3"],
        borderWidth: 2, borderColor: "#fff"
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Votação Presidencial (%) — 1992", font: { size: 14 } },
        legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => `${ctx.label}: ${ctx.parsed.toFixed(2)}%` } }
      }
    }
  });
}

/* ============================================================
   ARRANQUE
   ============================================================ */
document.addEventListener("DOMContentLoaded", carregarDados);