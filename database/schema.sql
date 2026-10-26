-- Esquema SQLite/PostgreSQL — Eleições Angola 1992

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
