/**
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
      connectSrc: [
        "'self'",
        "https://cdn.datatables.net",       // ← DataTables i18n
        "https://cdn.jsdelivr.net"          // ← Chart.js sourcemap (opcional)
      ],
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
    console.log(`\n✅ Servidor em http://localhost:${PORT} (${NODE_ENV})`);
    console.log(`   API:    http://localhost:${PORT}/api/eleicoes/1992/tudo`);
    console.log(`   Health: http://localhost:${PORT}/api/health`);
    console.log(`   Fonte:  ${db.usandoSQLite ? "SQLite" : "JSON"}\n`);
  });
}

if (require.main === module) iniciar();

module.exports = { app, iniciar };
