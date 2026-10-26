-- Migração SQLite → PostgreSQL
-- Uso:
--   1) sqlite3 eleicoes.db .dump > dump.sql
--   2) Ajustar AUTOINCREMENT → SERIAL
--   3) psql -U postgres -f migrate-postgres.sql

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
