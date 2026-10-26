-- Seed — Dados das Eleições Gerais de Angola (1992)

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
