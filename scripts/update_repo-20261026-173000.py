#!/usr/bin/env python3
"""
update_repo-20261026-173000.py — Gestão completa do repositório Git + versão final.

Correções face à versão anterior:
  • _conteudo_generate_snapshot() REMOVIDA (não reescreve generate_snapshot.py).
  • generate_snapshot.py mantido manualmente (já está válido no repositório).
  • Evita a regressão que quebrava o snapshot no passo 3.
  • FICHEIROS_VERSAO_FINAL embutido (autónomo, sem dependência externa).

Uso:
  python scripts/update_repo-20261026-173000.py --dry-run
  python scripts/update_repo-20261026-173000.py --fix-now "feat: ..."
  python scripts/update_repo-20261026-173000.py --auto "feat: ..."
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ======================================================================
# Caminhos
# ======================================================================
SCRIPTS_DIR   = Path(__file__).resolve().parent
PROJETO_DIR   = SCRIPTS_DIR.parent
SNAPSHOTS_DIR = PROJETO_DIR / "snapshots"
BACKUP_DIR    = PROJETO_DIR / ".backup"
GITIGNORE     = PROJETO_DIR / ".gitignore"
GITATTRIBUTES = PROJETO_DIR / ".gitattributes"
GENERATE_SNAP = SCRIPTS_DIR / "generate_snapshot.py"

EXCLUSAO_PADRAO = {
    ".git", "node_modules", "coverage", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", ".DS_Store", ".pytest_cache", ".mypy_cache",
    "dist", "snapshots", ".backup",
}
EXCLUSAO_EXT = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo"}

TIPOS_VALIDOS = ("feat", "fix", "docs", "test", "db", "style", "chore", "refactor", "perf")

# ======================================================================
# Cores
# ======================================================================
class C:
    OK="\033[92m"; AVISO="\033[93m"; ERRO="\033[91m"
    INFO="\033[96m"; BOLD="\033[1m"; FIM="\033[0m"
    @staticmethod
    def ok(t):    return f"{C.OK}{t}{C.FIM}"
    @staticmethod
    def aviso(t): return f"{C.AVISO}{t}{C.FIM}"
    @staticmethod
    def erro(t):  return f"{C.ERRO}{t}{C.FIM}"
    @staticmethod
    def info(t):  return f"{C.INFO}{t}{C.FIM}"
    @staticmethod
    def bold(t):  return f"{C.BOLD}{t}{C.FIM}"

# ======================================================================
# FICHEIROS DA VERSÃO ATUAL (base)
# ======================================================================
FICHEIROS_VERSAO_ATUAL = {
    ".gitattributes": """* text=auto eol=lf
*.bat text eol=crlf
*.cmd text eol=crlf
*.ps1 text eol=crlf
*.png binary
*.jpg binary
*.zip binary
*.db -diff -merge -text
""",

    ".gitignore": """# Dependências
node_modules/
npm-debug.log*

# Ambiente
.env
.env.*
!.env.example

# Base de dados
eleicoes.db
*.sqlite
*.sqlite3

# Testes / cobertura
coverage/
.pytest_cache/
.mypy_cache/

# Build / snapshots
dist/
snapshots/
.backup/

# Scripts temporários
scripts/fix*.ps1
scripts/fix*.sh

# Sistema
.DS_Store
Thumbs.db
desktop.ini

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
""",

    ".env.example": """# Ambiente
NODE_ENV=production
PORT=8000

# CORS (lista separada por vírgulas)
CORS_ORIGINS=http://localhost:8080,http://localhost:8000
""",

    ".dockerignore": """node_modules
npm-debug.log
.git
.gitignore
*.md
tests
scripts
coverage
.env
.env.*
!.env.example
eleicoes.db
*.log
.DS_Store
.vscode
.idea
""",

    "package.json": """{
  "name": "eleicoes-angola-1992",
  "version": "0.2.0",
  "description": "API REST + frontend estático para as eleições de Angola de 1992",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "node --watch server.js",
    "test": "jest --runInBand",
    "test:coverage": "jest --coverage"
  },
  "dependencies": {
    "compression": "^1.7.4",
    "cors": "^2.8.5",
    "express": "^4.19.2",
    "express-rate-limit": "^7.4.0",
    "helmet": "^7.1.0",
    "morgan": "^1.10.0"
  },
  "optionalDependencies": {
    "better-sqlite3": "^11.0.0"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "supertest": "^7.0.0"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}
""",
}

# ======================================================================
# FICHEIROS DA VERSÃO FINAL (embutido)
# ======================================================================
FICHEIROS_VERSAO_FINAL = {

    "server.js": '''/**
 * server.js — API REST + frontend estático.
 * Segurança: helmet, compression, CORS restrito, rate limiting.
 */
const express = require("express");
const cors = require("cors");
const morgan = require("morgan");
const helmet = require("helmet");
const compression = require("compression");
const rateLimit = require("express-rate-limit");
const path = require("path");
const db = require("./db");

const app = express();
const PORT = process.env.PORT || 8000;
const NODE_ENV = process.env.NODE_ENV || "development";

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "https://code.jquery.com", "https://cdn.datatables.net", "https://cdn.jsdelivr.net"],
      styleSrc: ["'self'", "'unsafe-inline'", "https://cdn.datatables.net"],
      imgSrc: ["'self'", "data:"],
      connectSrc: ["'self'"],
      fontSrc: ["'self'", "https://cdn.datatables.net"],
      objectSrc: ["'none'"],
      frameAncestors: ["'self'"],
    },
  },
  crossOriginEmbedderPolicy: false,
  crossOriginResourcePolicy: { policy: "cross-origin" },
}));

app.use(compression({ level: 6, threshold: 1024 }));

const ORIGENS = (process.env.CORS_ORIGINS || "http://localhost:8000")
  .split(",").map(s => s.trim()).filter(Boolean);

app.use(cors({
  origin: (origin, cb) => {
    if (!origin) return cb(null, true);
    if (NODE_ENV !== "production" || ORIGENS.includes(origin)) return cb(null, true);
    cb(new Error(`Origem não permitida: ${origin}`));
  },
  methods: ["GET", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Accept"],
  maxAge: 86400,
}));

const limiterGlobal = rateLimit({
  windowMs: 60 * 1000, max: 100,
  standardHeaders: "draft-7", legacyHeaders: false,
  message: { erro: "Demasiados pedidos. Tente novamente em 1 minuto." },
});
app.use("/api/", limiterGlobal);

const limiterPesado = rateLimit({
  windowMs: 60 * 1000, max: 30,
  standardHeaders: "draft-7", legacyHeaders: false,
  message: { erro: "Limite de pedidos agregados atingido." },
});

app.use(morgan(NODE_ENV === "production" ? "combined" : "dev"));
app.use(express.json({ limit: "100kb" }));

const ANO_PARA_ID = { "1992": "1992_GERAL" };
const resolverId = ano => ANO_PARA_ID[String(ano)] || null;

function validarEleicao(req, res, next) {
  const id = resolverId(req.params.ano);
  if (!id) {
    return res.status(404).json({
      erro: "Eleição não encontrada",
      ano: req.params.ano,
      disponiveis: Object.keys(ANO_PARA_ID),
    });
  }
  req.idEleicao = id;
  next();
}

app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    fonte: db.usandoSQLite ? "sqlite" : "json",
    ambiente: NODE_ENV,
    timestamp: new Date().toISOString(),
  });
});

app.get("/api/eleicoes/:ano", validarEleicao, (req, res) => {
  const e = db.getEleicao(req.idEleicao);
  if (!e) return res.status(404).json({ erro: "Sem dados para esta eleição" });
  res.json(e);
});

app.get("/api/eleicoes/:ano/partidos", validarEleicao, (req, res) => {
  res.json(db.getPartidos());
});

app.get("/api/eleicoes/:ano/presidenciais", validarEleicao, (req, res) => {
  res.json(db.getCandidatos(req.idEleicao));
});

app.get("/api/eleicoes/:ano/parlamentares", validarEleicao, (req, res) => {
  res.json(db.getResultadosParlamentares(req.idEleicao));
});

app.get("/api/eleicoes/:ano/timeline", validarEleicao, (req, res) => {
  res.json(db.getTimeline());
});

app.get("/api/eleicoes/:ano/tudo", limiterPesado, validarEleicao, (req, res) => {
  res.json(db.getTudo(req.idEleicao));
});

app.use(express.static(path.join(__dirname, "public"), {
  maxAge: NODE_ENV === "production" ? "1h" : 0,
  setHeaders: (res, filePath) => {
    if (filePath.endsWith("sw.js")) {
      res.setHeader("Service-Worker-Allowed", "/");
      res.setHeader("Cache-Control", "no-cache");
    }
  },
}));

app.get("*", (req, res) => {
  if (req.path.startsWith("/api/")) {
    return res.status(404).json({ erro: "Endpoint não encontrado" });
  }
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.use((err, req, res, next) => {
  console.error(`[erro] ${req.method} ${req.path}:`, err.message);
  const status = err.status || 500;
  res.status(status).json({
    erro: NODE_ENV === "production" && status === 500
      ? "Erro interno do servidor"
      : err.message,
  });
});

function iniciar() {
  return app.listen(PORT, () => {
    console.log(`\\n✅ Servidor em http://localhost:${PORT} (${NODE_ENV})`);
    console.log(`   API:    http://localhost:${PORT}/api/eleicoes/1992/tudo`);
    console.log(`   Health: http://localhost:${PORT}/api/health`);
    console.log(`   Fonte:  ${db.usandoSQLite ? "SQLite" : "JSON"}\\n`);
  });
}

if (require.main === module) iniciar();

module.exports = { app, iniciar };
''',

    "db.js": '''/**
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
''',

    "Dockerfile": '''FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev --no-audit --no-fund

FROM node:20-alpine AS runtime
WORKDIR /app

RUN addgroup -S app && adduser -S app -G app

ENV NODE_ENV=production PORT=8000

COPY --from=deps /app/node_modules ./node_modules
COPY package*.json ./
COPY server.js db.js ./
COPY public ./public
COPY database ./database

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
  CMD wget -qO- http://localhost:8000/api/health || exit 1

CMD ["node", "server.js"]
''',

    "docker-compose.yml": '''version: "3.9"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: angola92-api:0.2.0
    container_name: angola92-app
    restart: unless-stopped
    environment:
      NODE_ENV: production
      PORT: 8000
      CORS_ORIGINS: "http://localhost:8080,http://localhost:8000"
    ports:
      - "8000:8000"
    volumes:
      - ./eleicoes.db:/app/eleicoes.db:ro
      - ./public/data:/app/public/data:ro
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - angola92-net

  nginx:
    image: nginx:1.27-alpine
    container_name: angola92-nginx
    restart: unless-stopped
    depends_on:
      app:
        condition: service_healthy
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - angola92-net

networks:
  angola92-net:
    driver: bridge
''',

    "nginx/nginx.conf": '''server {
    listen 80;
    server_name _;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               application/xml text/xml image/svg+xml;
    gzip_min_length 1024;
    gzip_comp_level 6;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location /api/ {
        proxy_pass http://app:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }

    location / {
        proxy_pass http://app:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /sw.js {
        proxy_pass http://app:8000;
        add_header Cache-Control "no-cache";
        add_header Service-Worker-Allowed "/";
    }
}
''',

    "jest.config.js": '''module.exports = {
  testEnvironment: "node",
  testMatch: ["**/tests/**/*.test.js"],
  collectCoverageFrom: ["server.js", "db.js", "!node_modules/**"],
  coverageDirectory: "coverage",
  coverageReporters: ["text", "lcov", "html"],
  verbose: true,
  testTimeout: 10000,
};
''',

    "tests/helpers.js": '''/**
 * tests/helpers.js — utilitários partilhados.
 */
const path = require("path");
const fs = require("fs");

const DATA_DIR = path.join(__dirname, "..", "public", "data");

function lerJSON(nome) {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, nome), "utf-8"));
}

module.exports = { lerJSON, DATA_DIR };
''',

    "tests/api.test.js": '''/**
 * tests/api.test.js — Testes de integração com supertest + jest.
 */
const request = require("supertest");
const { app } = require("../server");

describe("API — Eleições Angola 1992", () => {

  describe("GET /api/health", () => {
    it("deve responder 200 com status ok", async () => {
      const res = await request(app).get("/api/health").expect(200);
      expect(res.body).toHaveProperty("status", "ok");
      expect(["json", "sqlite"]).toContain(res.body.fonte);
    });
  });

  describe("GET /api/eleicoes/1992", () => {
    it("deve devolver os metadados da eleição", async () => {
      const res = await request(app).get("/api/eleicoes/1992").expect(200);
      expect(res.body.id_eleicao).toBe("1992_GERAL");
      expect(res.body.ano).toBe(1992);
      expect(res.body.eleitores_inscritos).toBe(4828468);
    });

    it("deve devolver 404 para ano inexistente", async () => {
      const res = await request(app).get("/api/eleicoes/1999").expect(404);
      expect(res.body).toHaveProperty("erro");
      expect(res.body.disponiveis).toContain("1992");
    });
  });

  describe("GET /api/eleicoes/1992/partidos", () => {
    it("deve devolver 14 partidos", async () => {
      const res = await request(app).get("/api/eleicoes/1992/partidos").expect(200);
      expect(res.body).toHaveLength(14);
      const siglas = res.body.map(p => p.sigla);
      expect(siglas).toEqual(expect.arrayContaining(["MPLA", "UNITA", "FNLA"]));
    });
  });

  describe("GET /api/eleicoes/1992/presidenciais", () => {
    it("deve devolver 11 candidatos", async () => {
      const res = await request(app).get("/api/eleicoes/1992/presidenciais").expect(200);
      expect(res.body).toHaveLength(11);
      expect(res.body[0].nome_candidato).toBe("José Eduardo dos Santos");
    });

    it("soma das percentagens deve ser ≈100%", async () => {
      const res = await request(app).get("/api/eleicoes/1992/presidenciais").expect(200);
      const soma = res.body.reduce((s, c) => s + Number(c.percentagem), 0);
      expect(soma).toBeGreaterThan(99);
      expect(soma).toBeLessThan(101);
    });
  });

  describe("GET /api/eleicoes/1992/parlamentares", () => {
    it("soma dos assentos deve ser 220", async () => {
      const res = await request(app).get("/api/eleicoes/1992/parlamentares").expect(200);
      const soma = res.body.reduce((s, r) => s + r.assentos, 0);
      expect(soma).toBe(220);
    });

    it("MPLA deve ter 129 assentos e UNITA 70", async () => {
      const res = await request(app).get("/api/eleicoes/1992/parlamentares").expect(200);
      const mpla = res.body.find(r => r.id_partido === 1);
      const unita = res.body.find(r => r.id_partido === 2);
      expect(mpla.assentos).toBe(129);
      expect(unita.assentos).toBe(70);
    });
  });

  describe("GET /api/eleicoes/1992/timeline", () => {
    it("deve devolver 6 eventos", async () => {
      const res = await request(app).get("/api/eleicoes/1992/timeline").expect(200);
      expect(res.body).toHaveLength(6);
    });
  });

  describe("GET /api/eleicoes/1992/tudo", () => {
    it("deve devolver payload agregado", async () => {
      const res = await request(app).get("/api/eleicoes/1992/tudo").expect(200);
      expect(res.body).toHaveProperty("eleicao");
      expect(res.body).toHaveProperty("partidos");
      expect(res.body).toHaveProperty("candidatos");
      expect(res.body).toHaveProperty("parlamentar");
      expect(res.body).toHaveProperty("timeline");
    });
  });

  describe("Segurança", () => {
    it("deve devolver cabeçalhos do Helmet", async () => {
      const res = await request(app).get("/api/health");
      expect(res.headers["x-content-type-options"]).toBe("nosniff");
    });

    it("deve devolver 404 em endpoint inexistente da API", async () => {
      const res = await request(app).get("/api/inexistente").expect(404);
    });
  });
});
''',

    "database/schema.sql": '''-- Esquema SQLite/PostgreSQL — Eleições Angola 1992

CREATE TABLE IF NOT EXISTS eleicoes (
  id_eleicao          VARCHAR(20)   PRIMARY KEY,
  ano                 INTEGER       NOT NULL,
  data_inicio         DATE          NOT NULL,
  data_fim            DATE          NOT NULL,
  tipo                VARCHAR(100)  NOT NULL,
  eleitores_inscritos INTEGER,
  votantes            INTEGER,
  taxa_participacao   NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS partidos (
  id_partido    INTEGER      PRIMARY KEY,
  sigla         VARCHAR(20)  NOT NULL UNIQUE,
  nome_completo VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS candidatos_presidenciais (
  id_candidato   INTEGER      PRIMARY KEY,
  id_eleicao     VARCHAR(20)  NOT NULL REFERENCES eleicoes(id_eleicao),
  nome_candidato VARCHAR(150) NOT NULL,
  id_partido     INTEGER      REFERENCES partidos(id_partido),
  votos          INTEGER,
  percentagem    NUMERIC(5,2),
  posicao        INTEGER
);

CREATE TABLE IF NOT EXISTS resultados_parlamentares (
  id_resultado INTEGER     PRIMARY KEY,
  id_eleicao   VARCHAR(20) NOT NULL REFERENCES eleicoes(id_eleicao),
  id_partido   INTEGER     NOT NULL REFERENCES partidos(id_partido),
  votos        INTEGER,
  percentagem  NUMERIC(5,2),
  assentos     INTEGER     NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS timeline (
  id        INTEGER      PRIMARY KEY AUTOINCREMENT,
  data      DATE         NOT NULL,
  titulo    VARCHAR(150) NOT NULL,
  descricao TEXT
);

CREATE INDEX IF NOT EXISTS idx_cand_eleicao   ON candidatos_presidenciais(id_eleicao);
CREATE INDEX IF NOT EXISTS idx_cand_partido   ON candidatos_presidenciais(id_partido);
CREATE INDEX IF NOT EXISTS idx_parl_eleicao   ON resultados_parlamentares(id_eleicao);
CREATE INDEX IF NOT EXISTS idx_parl_partido   ON resultados_parlamentares(id_partido);
CREATE INDEX IF NOT EXISTS idx_timeline_data  ON timeline(data);
''',

    "database/seed.sql": '''-- Seed — Dados das Eleições Gerais de Angola (1992)

BEGIN;

INSERT OR REPLACE INTO eleicoes
  (id_eleicao, ano, data_inicio, data_fim, tipo,
   eleitores_inscritos, votantes, taxa_participacao)
VALUES
  ('1992_GERAL', 1992, '1992-09-29', '1992-09-30',
   'Geral (Presidencial + Legislativa)',
   4828468, 4410575, 91.34);

INSERT OR REPLACE INTO partidos (id_partido, sigla, nome_completo) VALUES
  (1,  'MPLA',    'Movimento Popular de Libertação de Angola'),
  (2,  'UNITA',   'União Nacional para a Independência Total de Angola'),
  (3,  'PDA',     'Partido Democrático de Angola'),
  (4,  'FNLA',    'Frente Nacional de Libertação de Angola'),
  (5,  'PLD',     'Partido Liberal Democrático'),
  (6,  'PRD',     'Partido Renovador Democrático'),
  (7,  'PSD',     'Partido Social Democrata'),
  (8,  'FD',      'Frente Democrática'),
  (9,  'PNDA',    'Partido Nacional Democrático Angolano'),
  (10, 'PRA',     'Partido Reformador Angolano'),
  (11, 'PRS',     'Partido Renovador Socialista'),
  (12, 'AAD-COA', 'Coligação – Aliança Democrática'),
  (13, 'PAJOCA',  'Partido da Aliança dos Jovens, Operários e Camponeses de Angola'),
  (14, 'PDP-ANA', 'Partido Democrático Pelo Progresso / Aliança Nacional Angolana');

INSERT OR REPLACE INTO candidatos_presidenciais
  (id_candidato, id_eleicao, nome_candidato, id_partido, votos, percentagem, posicao)
VALUES
  (101, '1992_GERAL', 'José Eduardo dos Santos',    1,    NULL,  49.57, 1),
  (102, '1992_GERAL', 'Jonas Savimbi',              2,    NULL,  40.07, 2),
  (103, '1992_GERAL', 'António Alberto Neto',       3,    NULL,   2.16, 3),
  (104, '1992_GERAL', 'Holden Roberto',             4,    NULL,   2.11, 4),
  (105, '1992_GERAL', 'Honorato Lando',             5,    NULL,   1.92, 5),
  (106, '1992_GERAL', 'Luís dos Passos',            6,    NULL,   1.47, 6),
  (107, '1992_GERAL', 'Bengui Pedro João',          7,    NULL,   0.97, 7),
  (108, '1992_GERAL', 'Simão Cacete',               8,    NULL,   0.67, 8),
  (109, '1992_GERAL', 'Daniel Chipenda',            NULL, NULL,   0.52, 9),
  (110, '1992_GERAL', 'Anália de Victória Pereira', 5,    11475,  0.29, 10),
  (111, '1992_GERAL', 'Rui de Victória Pereira',    10,   NULL,   0.23, 11);

INSERT OR REPLACE INTO resultados_parlamentares
  (id_resultado, id_eleicao, id_partido, votos, percentagem, assentos)
VALUES
  (5001, '1992_GERAL', 1,  2124126, 53.74, 129),
  (5002, '1992_GERAL', 2,  NULL,    34.10,  70),
  (5003, '1992_GERAL', 4,  NULL,     2.40,   5),
  (5004, '1992_GERAL', 5,  NULL,     2.39,   3),
  (5005, '1992_GERAL', 11, NULL,     2.27,   6),
  (5006, '1992_GERAL', 6,  NULL,     NULL,   1),
  (5007, '1992_GERAL', 12, NULL,     NULL,   1),
  (5008, '1992_GERAL', 7,  NULL,     NULL,   1),
  (5009, '1992_GERAL', 13, NULL,     NULL,   1),
  (5010, '1992_GERAL', 14, NULL,     NULL,   1),
  (5011, '1992_GERAL', 9,  NULL,     NULL,   1);

INSERT OR REPLACE INTO timeline (id, data, titulo, descricao) VALUES
  (1, '1991-05-31', 'Acordos de Bicesse', 'Assinatura em Portugal entre o Governo (MPLA) e a UNITA.'),
  (2, '1992-05-20', 'Início do Registo Eleitoral', 'Abertura do recenseamento; prolonga-se até 31 de julho.'),
  (3, '1992-09-29', 'Eleições Gerais (1.º dia)', 'Realização das primeiras eleições multipartidárias.'),
  (4, '1992-09-30', 'Eleições Gerais (2.º dia)', 'Continuação da votação; participação superior a 91%.'),
  (5, '1992-10-17', 'Anúncio dos Resultados', 'A Comissão Nacional Eleitoral divulga os resultados finais.'),
  (6, '1992-10-31', 'Colapso do Processo de Paz', 'UNITA rejeita os resultados; confrontos armados em Luanda.');

COMMIT;
''',

    "database/migrate-postgres.sql": '''-- Migração SQLite → PostgreSQL

CREATE TABLE IF NOT EXISTS eleicoes (
  id_eleicao          VARCHAR(20)   PRIMARY KEY,
  ano                 INTEGER       NOT NULL,
  data_inicio         DATE          NOT NULL,
  data_fim            DATE          NOT NULL,
  tipo                VARCHAR(100)  NOT NULL,
  eleitores_inscritos INTEGER,
  votantes            INTEGER,
  taxa_participacao   NUMERIC(5,2)
);

CREATE TABLE IF NOT EXISTS partidos (
  id_partido    INTEGER      PRIMARY KEY,
  sigla         VARCHAR(20)  NOT NULL UNIQUE,
  nome_completo VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS candidatos_presidenciais (
  id_candidato   INTEGER      PRIMARY KEY,
  id_eleicao     VARCHAR(20)  NOT NULL REFERENCES eleicoes(id_eleicao),
  nome_candidato VARCHAR(150) NOT NULL,
  id_partido     INTEGER      REFERENCES partidos(id_partido),
  votos          INTEGER,
  percentagem    NUMERIC(5,2),
  posicao        INTEGER
);

CREATE TABLE IF NOT EXISTS resultados_parlamentares (
  id_resultado INTEGER     PRIMARY KEY,
  id_eleicao   VARCHAR(20) NOT NULL REFERENCES eleicoes(id_eleicao),
  id_partido   INTEGER     NOT NULL REFERENCES partidos(id_partido),
  votos        INTEGER,
  percentagem  NUMERIC(5,2),
  assentos     INTEGER     NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS timeline (
  id        SERIAL       PRIMARY KEY,
  data      DATE         NOT NULL,
  titulo    VARCHAR(150) NOT NULL,
  descricao TEXT
);

CREATE OR REPLACE VIEW vw_assentos AS
SELECT p.sigla, p.nome_completo, r.percentagem, r.assentos,
       ROUND(100.0 * r.assentos / NULLIF(SUM(r.assentos) OVER (), 0), 2) AS pct_assentos
FROM resultados_parlamentares r
JOIN partidos p ON p.id_partido = r.id_partido
WHERE r.id_eleicao = '1992_GERAL'
ORDER BY r.assentos DESC;

CREATE OR REPLACE VIEW vw_presidenciais AS
SELECT c.posicao, c.nome_candidato,
       COALESCE(p.sigla, 'Ind.') AS sigla,
       c.votos, c.percentagem
FROM candidatos_presidenciais c
LEFT JOIN partidos p ON p.id_partido = c.id_partido
WHERE c.id_eleicao = '1992_GERAL'
ORDER BY c.posicao;
''',
}

# ======================================================================
# Helpers de escrita
# ======================================================================
def escrever_ficheiro(rel: str, conteudo: str, dry_run: bool, backup: Path | None) -> str:
    destino = PROJETO_DIR / rel
    dados_novos = conteudo.encode("utf-8")

    if destino.exists():
        dados_atuais = destino.read_bytes()
        if dados_atuais == dados_novos:
            return "inalterado"
        if dry_run:
            return "dry-atualizado"
        if backup:
            alvo = backup / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destino, alvo)
        destino.write_bytes(dados_novos)
        return "atualizado"
    else:
        if dry_run:
            return "dry-criado"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(dados_novos)
        return "criado"


def escrever_todos_ficheiros(dry_run: bool) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = None if dry_run else (BACKUP_DIR / timestamp)

    print(C.bold("\n═══ 0. ESCRITA DOS FICHEIROS (versão atual + final) ═══"))
    if dry_run:
        print(C.aviso("  [dry-run] Nenhum ficheiro será escrito."))
    else:
        print(C.info(f"  Backup: {backup}"))

    contagem = {"criado": 0, "atualizado": 0, "inalterado": 0,
                "dry-criado": 0, "dry-atualizado": 0}
    detalhes = []

    # Merge: versão atual primeiro, versão final ganha se houver colisão
    todos = {**FICHEIROS_VERSAO_ATUAL, **FICHEIROS_VERSAO_FINAL}

    for rel, conteudo in todos.items():
        estado = escrever_ficheiro(rel, conteudo, dry_run, backup)
        contagem[estado] = contagem.get(estado, 0) + 1
        detalhes.append((estado, rel))

    # generate_snapshot.py NÃO é reescrito (mantido manualmente)
    # update_repo.py NÃO é reescrito (este ficheiro É o update_repo)

    print()
    for estado, rel in detalhes:
        mapa = {
            "criado":          (C.ok,     "✔ criado       "),
            "atualizado":      (C.aviso,  "✎ atualizado   "),
            "inalterado":      (C.info,   "· inalterado   "),
            "dry-criado":      (C.info,   "· criaria      "),
            "dry-atualizado":  (C.aviso,  "· atualizaria  "),
        }
        cor, rotulo = mapa.get(estado, (C.info, "? "))
        print(f"  {cor(rotulo)} {rel}")

    print()
    print(f"  {C.ok('criados')}     : {contagem['criado']}")
    print(f"  {C.aviso('atualizados')} : {contagem['atualizado']}")
    print(f"  {C.info('inalterados')} : {contagem['inalterado']}")
    if dry_run:
        print(f"  {C.info('criaria')}     : {contagem['dry-criado']}")
        print(f"  {C.aviso('atualizaria')} : {contagem['dry-atualizado']}")

    return contagem


# ======================================================================
# Helpers Git
# ======================================================================
def run_cmd(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd or PROJETO_DIR, shell=isinstance(cmd, str),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"Comando falhou: {cmd}\n{p.stderr}")
    return p.stdout.strip(), p.stderr.strip(), p.returncode


def git(*args, check=True):
    return run_cmd(["git", *args], check=check)


def e_repo_git():
    _, _, code = git("rev-parse", "--is-inside-work-tree", check=False)
    return code == 0


def branch_atual():
    out, _, _ = git("rev-parse", "--abbrev-ref", "HEAD", check=False)
    return out or "(detached)"


def listar_alteracoes():
    out, _, _ = git("status", "--porcelain", check=False)
    itens = []
    for linha in out.splitlines():
        if not linha.strip():
            continue
        itens.append((linha[:2].strip(), linha[3:].strip()))
    return itens


def ultima_tag():
    out, _, _ = git("describe", "--tags", "--abbrev=0", check=False)
    return out or "v0.0.0"


def proxima_versao(tag, tipo):
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not m:
        return "v1.0.0"
    major, minor, patch = map(int, m.groups())
    if tipo in ("feat", "db", "refactor", "perf"):
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"v{major}.{minor}.{patch}"


# ======================================================================
# Validações
# ======================================================================
def validar_gitignore():
    if not GITIGNORE.exists():
        return True, "não existe (será criado)"
    conteudo = GITIGNORE.read_text(encoding="utf-8", errors="replace")
    if "Out-File" in conteudo or re.search(r"^\s*'@", conteudo, re.M):
        return False, "contém here-string colado"
    return True, "OK"


def validar_gitattributes():
    if not GITATTRIBUTES.exists():
        return True, "não existe (opcional)"
    for i, linha in enumerate(GITATTRIBUTES.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = linha.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("@'") or "Out-File" in s or "|" in s:
            return False, f"linha {i} inválida: {linha[:60]}"
    return True, "OK"


def validar_scripts(dry_run: bool = False):
    problemas = []
    for f in SCRIPTS_DIR.glob("*.py"):
        try:
            run_cmd([sys.executable, "-m", "py_compile", str(f)], check=True)
        except Exception as e:
            problemas.append(f"{f.name}: {e}")
    if not problemas:
        return True, "OK"
    if dry_run:
        return True, "aviso (dry-run): " + "; ".join(problemas)[:200]
    return False, "; ".join(problemas)


def validar_geral(dry_run: bool = False):
    ok1, m1 = validar_gitignore()
    ok2, m2 = validar_gitattributes()
    ok3, m3 = validar_scripts(dry_run=dry_run)
    return (ok1 and ok2 and ok3), (ok1, m1, ok2, m2, ok3, m3)


# ======================================================================
# Passos
# ======================================================================
def passo_estado():
    print(C.bold("\n═══ 1. ESTADO DO REPOSITÓRIO ═══"))
    print(f"  Pasta    : {PROJETO_DIR}")
    print(f"  Branch   : {C.ok(branch_atual())}")
    print(f"  Tag atual: {C.ok(ultima_tag())}")
    alteracoes = listar_alteracoes()
    if not alteracoes:
        print(C.ok("  ✔ Nenhuma alteração pendente."))
        return []
    print(C.aviso(f"\n  {len(alteracoes)} alteração(ões):"))
    for i, (status, f) in enumerate(alteracoes, 1):
        c = C.ok if status in ("A", "??") else (C.aviso if status == "M" else C.erro)
        print(f"    [{i:>2}] {c(status):<10} {f}")
    return alteracoes


def passo_validacoes(dry_run: bool = False):
    print(C.bold("\n═══ 2. VALIDAÇÕES ═══"))
    ok, (ok1, m1, ok2, m2, ok3, m3) = validar_geral(dry_run=dry_run)
    print(f"  {C.ok('✔') if ok1 else C.erro('✖')} .gitignore     → {m1}")
    print(f"  {C.ok('✔') if ok2 else C.erro('✖')} .gitattributes → {m2}")
    if dry_run and not ok3:
        print(f"  {C.aviso('⚠')} scripts/*.py   → {m3}")
    else:
        print(f"  {C.ok('✔') if ok3 else C.erro('✖')} scripts/*.py   → {m3}")
    return ok


def passo_snapshot():
    print(C.bold("\n═══ 3. SNAPSHOT ═══"))
    if not GENERATE_SNAP.exists():
        print(C.aviso("  → generate_snapshot.py não existe; a saltar."))
        return None
    out, err, code = run_cmd([sys.executable, str(GENERATE_SNAP)], check=False)
    if code != 0:
        print(C.erro(f"  ✖ Falha no snapshot: {(err or out)[:300]}"))
        return None
    for linha in out.splitlines():
        if "ZIP" in linha and ".zip" in linha:
            print(f"  {C.ok('✔')} {linha.strip()}")
            break
    else:
        print(C.ok("  ✔ Snapshot gerado."))
    return True


def passo_selecao(alteracoes):
    print(C.bold("\n═══ 4. SELEÇÃO DE FICHEIROS ═══"))
    print("  a) TODOS  |  n) Nenhum  |  1,2,3) por número")
    escolha = input(C.info("  Escolha [a/n/lista]: ")).strip().lower()
    if escolha == "n":
        return []
    if escolha in ("a", ""):
        git("add", "-A")
        return [f for _, f in alteracoes]
    indices = [int(p)-1 for p in escolha.split(",") if p.strip().isdigit()]
    for idx in indices:
        if 0 <= idx < len(alteracoes):
            git("add", alteracoes[idx][1])
    return [alteracoes[i][1] for i in indices if 0 <= i < len(alteracoes)]


def sugerir_tipo(ficheiros):
    tipos = []
    for f in ficheiros:
        fl = f.lower()
        if fl.endswith(".md") or "readme" in fl: tipos.append("docs")
        elif "test" in fl: tipos.append("test")
        elif fl.endswith((".yml", ".yaml")) or "docker" in fl: tipos.append("chore")
        elif fl.endswith(".sql"): tipos.append("db")
        elif fl.endswith((".css", ".html")): tipos.append("style")
        elif fl.endswith((".js", ".py")): tipos.append("feat")
        else: tipos.append("chore")
    for t in TIPOS_VALIDOS:
        if t in tipos: return t
    return "chore"


def passo_commit(ficheiros):
    print(C.bold("\n═══ 5. MENSAGEM DE COMMIT ═══"))
    tipo = sugerir_tipo(ficheiros)
    exemplo = f"{tipo}: descreva a alteração em poucas palavras"
    print(f"  Tipos: {', '.join(TIPOS_VALIDOS)}")
    print(f"  Sugestão: {C.ok(exemplo)}")
    msg = input(C.info("  Mensagem: ")).strip()
    if not msg:
        r = input(C.aviso("  Usar sugestão? [s/N]: ")).strip().lower()
        if r != "s":
            print(C.erro("  ✖ Cancelado."))
            return None
        msg = exemplo
    corpo = input(C.info("  Corpo (Enter para saltar): ")).strip()
    if corpo:
        msg = f"{msg}\n\n{corpo}"
    out, err, code = git("commit", "-m", msg, check=False)
    if code != 0:
        print(C.erro(f"  ✖ Falha: {err[:300]}"))
        return None
    print(C.ok("  ✔ Commit criado."))
    return msg.splitlines()[0]


def passo_push():
    print(C.bold("\n═══ 6. PUSH ═══"))
    if input(C.info("  Fazer push? [s/N]: ")).strip().lower() != "s":
        print(C.aviso("  → Ignorado.")); return False
    out, err, code = git("push", check=False)
    if code != 0:
        out, err, code = git("push", "-u", "origin", branch_atual(), check=False)
    if code != 0:
        print(C.erro(f"  ✖ Falhou: {err[:300]}")); return False
    print(C.ok("  ✔ Push OK.")); return True


def passo_tag(tipo):
    print(C.bold("\n═══ 7. TAG ═══"))
    if input(C.info("  Criar tag? [s/N]: ")).strip().lower() != "s":
        print(C.aviso("  → Ignorada.")); return None
    atual = ultima_tag()
    sugerida = proxima_versao(atual, tipo)
    tag = input(C.info(f"  Tag [{sugerida}]: ")).strip() or sugerida
    anot = f"Release {tag} — {datetime.now():%Y-%m-%d}"
    out, err, code = git("tag", "-a", tag, "-m", anot, check=False)
    if code != 0:
        print(C.erro(f"  ✖ Falha: {err}")); return None
    print(C.ok(f"  ✔ Tag {tag} criada."))
    if input(C.info("  Push da tag? [s/N]: ")).strip().lower() == "s":
        git("push", "origin", tag, check=False)
        print(C.ok("  ✔ Tag enviada."))
    return tag


# ======================================================================
# Modo automático
# ======================================================================
def modo_auto(msg, no_snapshot=False, no_push=False, no_tag=False, no_files=False):
    print(C.bold("\n=== MODO AUTOMÁTICO ===\n"))
    if not no_files:
        escrever_todos_ficheiros(dry_run=False)
    if not no_snapshot:
        passo_snapshot()
    git("add", "-A")
    out, err, code = git("commit", "-m", msg, check=False)
    if code != 0:
        if "nothing to commit" in out or "nothing to commit" in err:
            print(C.aviso("⚠ Nada a commitar."))
            return 0
        print(C.erro(f"✖ Falha no commit: {err[:300]}"))
        return 1
    print(C.ok(f"✔ Commit: {msg}"))
    tipo = msg.split(":")[0].strip() if ":" in msg else "chore"
    if not no_push:
        git("push", check=False)
        print(C.ok("✔ Push efetuado."))
    if not no_tag:
        tag = proxima_versao(ultima_tag(), tipo)
        git("tag", "-a", tag, "-m", f"Release {tag}", check=False)
        if not no_push:
            git("push", "origin", tag, check=False)
        print(C.ok(f"✔ Tag {tag}" + ("" if no_push else " criada e enviada")))
    return 0


# ======================================================================
# Modo --fix-now
# ======================================================================
def modo_fix_now(msg, no_snapshot=False, no_push=False, no_tag=False):
    print(C.bold("\n=== MODO FIX-NOW ===\n"))
    contagem = escrever_todos_ficheiros(dry_run=False)
    if contagem["criado"] + contagem["atualizado"] == 0:
        print(C.info("\n· Nenhum ficheiro precisou de ser escrito."))

    print(C.bold("\n═══ VALIDAÇÃO PÓS-ESCRITA ═══"))
    ok, (ok1, m1, ok2, m2, ok3, m3) = validar_geral(dry_run=False)
    print(f"  {C.ok('✔') if ok1 else C.erro('✖')} .gitignore     → {m1}")
    print(f"  {C.ok('✔') if ok2 else C.erro('✖')} .gitattributes → {m2}")
    print(f"  {C.ok('✔') if ok3 else C.erro('✖')} scripts/*.py   → {m3}")

    if not ok:
        print(C.erro("\n✖ Validação falhou."))
        return 1

    if not no_snapshot:
        passo_snapshot()

    git("add", "-A")
    out, err, code = git("commit", "-m", msg, check=False)
    if code != 0:
        if "nothing to commit" in out or "nothing to commit" in err:
            print(C.aviso("⚠ Nada a commitar."))
            return 0
        print(C.erro(f"✖ Falha no commit: {err[:300]}"))
        return 1
    print(C.ok(f"✔ Commit: {msg}"))

    tipo = msg.split(":")[0].strip() if ":" in msg else "chore"

    if not no_push:
        git("push", check=False)
        print(C.ok("✔ Push efetuado."))

    if not no_tag:
        tag = proxima_versao(ultima_tag(), tipo)
        git("tag", "-a", tag, "-m", f"Release {tag}", check=False)
        if not no_push:
            git("push", "origin", tag, check=False)
        print(C.ok(f"✔ Tag {tag}" + ("" if no_push else " criada e enviada")))

    return 0


# ======================================================================
# Main
# ======================================================================
def main():
    ap = argparse.ArgumentParser(description="Gestão completa do repositório + versão final")
    ap.add_argument("--auto", metavar="MSG", help="Commit automático")
    ap.add_argument("--fix-now", metavar="MSG", help="Escreve + valida + commita")
    ap.add_argument("--dry-run", action="store_true", help="Só mostrar")
    ap.add_argument("--files-only", action="store_true", help="Só escrever ficheiros")
    ap.add_argument("--no-files", action="store_true", help="Saltar escrita")
    ap.add_argument("--no-snapshot", action="store_true", help="Sem snapshot")
    ap.add_argument("--no-push", action="store_true", help="Sem push")
    ap.add_argument("--no-tag", action="store_true", help="Sem tag")
    args = ap.parse_args()

    print(C.bold("\n╔══════════════════════════════════════════════╗"))
    print(C.bold("║   UPDATE REPO — VERSÃO FINAL (sem regeneração) ║"))
    print(C.bold("╚══════════════════════════════════════════════╝"))

    if args.files_only:
        contagem = escrever_todos_ficheiros(dry_run=False)
        if contagem["criado"] + contagem["atualizado"] > 0:
            print(C.ok("\n✅ Ficheiros escritos."))
        else:
            print(C.info("\n· Nenhum ficheiro precisou de ser escrito."))
        return 0

    if args.fix_now:
        if not e_repo_git():
            print(C.erro("✖ Não está dentro de um repositório Git."))
            sys.exit(1)
        sys.exit(modo_fix_now(args.fix_now, args.no_snapshot, args.no_push, args.no_tag))

    if not e_repo_git():
        print(C.erro("✖ Não está dentro de um repositório Git."))
        sys.exit(1)

    if not args.no_files:
        escrever_todos_ficheiros(dry_run=args.dry_run)

    alteracoes = passo_estado()
    valido = passo_validacoes(dry_run=args.dry_run)

    if args.dry_run:
        print(C.aviso("\n[dry-run] Nenhuma alteração efetuada."))
        sys.exit(0)

    if not valido:
        print(C.erro("\n✖ Corrija os problemas antes de continuar."))
        sys.exit(1)

    if not alteracoes:
        print(C.ok("\n✔ Nada a fazer. Repositório limpo."))
        sys.exit(0)

    if args.auto:
        sys.exit(modo_auto(args.auto, args.no_snapshot, args.no_push,
                           args.no_tag, no_files=True))

    if not args.no_snapshot:
        passo_snapshot()
    selecionados = passo_selecao(alteracoes)
    if not selecionados:
        print(C.aviso("\n→ Nada adicionado.")); sys.exit(0)
    msg = passo_commit(selecionados)
    if not msg: sys.exit(1)
    tipo = msg.split(":")[0].strip() if ":" in msg else "chore"
    if not args.no_push: passo_push()
    if not args.no_tag:  passo_tag(tipo)

    print(C.ok("\n✅ Ciclo concluído."))
    print(f"   Branch: {branch_atual()} | Última tag: {ultima_tag()}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        print(C.aviso("\n\n⏹ Interrompido.")); sys.exit(130)
    except Exception as e:
        print(C.erro(f"\n✖ Erro: {e}")); sys.exit(1)