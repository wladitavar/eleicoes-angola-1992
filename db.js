/**
 * db.js — Abstração de fonte de dados.
 * Usa SQLite se disponível; caso contrário, lê JSON de public/data/.
 */
const path = require("path");
const fs = require("fs");

const DATA_DIR = path.join(__dirname, "public", "data");
const SQLITE_PATH = path.join(__dirname, "eleicoes.db");

let sqlite = null;
let usandoSQLite = false;

try {
  if (fs.existsSync(SQLITE_PATH)) {
    const Database = require("better-sqlite3");
    sqlite = new Database(SQLITE_PATH, { readonly: true });
    usandoSQLite = true;
    console.log(`[db] SQLite ligado: ${SQLITE_PATH}`);
  } else {
    console.log("[db] eleicoes.db não encontrado — a usar JSON.");
  }
} catch (e) {
  console.log(`[db] better-sqlite3 indisponível (${e.message}) — a usar JSON.`);
}

function lerJSON(nome) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, nome), "utf-8"));
}

function getEleicao(id = "1992_GERAL") {
  if (usandoSQLite) {
    return sqlite.prepare("SELECT * FROM eleicoes WHERE id_eleicao = ?").get(id) || null;
  }
  const e = lerJSON("eleicao.json");
  return e.id_eleicao === id ? e : null;
}

function getPartidos() {
  if (usandoSQLite) {
    return sqlite.prepare("SELECT * FROM partidos ORDER BY id_partido").all();
  }
  return lerJSON("partidos.json");
}

function getCandidatos(idEleicao = "1992_GERAL") {
  if (usandoSQLite) {
    return sqlite.prepare("SELECT * FROM candidatos_presidenciais WHERE id_eleicao = ? ORDER BY posicao").all(idEleicao);
  }
  return lerJSON("candidatos_presidenciais.json");
}

function getResultadosParlamentares(idEleicao = "1992_GERAL") {
  if (usandoSQLite) {
    return sqlite.prepare("SELECT * FROM resultados_parlamentares WHERE id_eleicao = ? ORDER BY assentos DESC").all(idEleicao);
  }
  return lerJSON("resultados_parlamentares.json");
}

function getTimeline() {
  if (usandoSQLite) {
    return sqlite.prepare("SELECT * FROM timeline ORDER BY data").all();
  }
  return lerJSON("timeline.json");
}

function getTudo(id = "1992_GERAL") {
  return {
    eleicao: getEleicao(id),
    partidos: getPartidos(),
    candidatos: getCandidatos(id),
    parlamentar: getResultadosParlamentares(id),
    timeline: getTimeline(),
  };
}

module.exports = {
  getEleicao, getPartidos, getCandidatos,
  getResultadosParlamentares, getTimeline, getTudo,
  usandoSQLite,
};
