// data.js — replica o esquema proposto (Eleicoes, Partidos, Candidatos, Resultados)

const eleicao1992 = {
  id_eleicao: "1992_GERAL",
  ano: 1992,
  data_inicio: "1992-09-29",
  data_fim: "1992-09-30",
  tipo: "Geral (Presidencial + Legislativa)",
  eleitores_inscritos: 4828468,
  votantes: 4410575,
  taxa_participacao: 91.34
};

const partidos = [
  { id_partido: 1,  sigla: "MPLA",  nome_completo: "Movimento Popular de Libertação de Angola" },
  { id_partido: 2,  sigla: "UNITA", nome_completo: "União Nacional para a Independência Total de Angola" },
  { id_partido: 3,  sigla: "PDA",   nome_completo: "Partido Democrático de Angola" },
  { id_partido: 4,  sigla: "FNLA",  nome_completo: "Frente Nacional de Libertação de Angola" },
  { id_partido: 5,  sigla: "PLD",   nome_completo: "Partido Liberal Democrático" },
  { id_partido: 6,  sigla: "PRD",   nome_completo: "Partido Renovador Democrático" },
  { id_partido: 7,  sigla: "PSD",   nome_completo: "Partido Social Democrata" },
  { id_partido: 8,  sigla: "FD",    nome_completo: "Frente Democrática" },
  { id_partido: 9,  sigla: "PNDA",  nome_completo: "Partido Nacional Democrático Angolano" },
  { id_partido: 10, sigla: "PRA",   nome_completo: "Partido Reformador Angolano" },
  { id_partido: 11, sigla: "PRS",   nome_completo: "Partido Renovador Socialista" },
  { id_partido: 12, sigla: "AAD-COA", nome_completo: "Coligação – Aliança Democrática" },
  { id_partido: 13, sigla: "PAJOCA", nome_completo: "Partido da Aliança dos Jovens, Operários e Camponeses de Angola" },
  { id_partido: 14, sigla: "PDP-ANA", nome_completo: "Partido Democrático Pelo Progresso / Aliança Nacional Angolana" }
];

const candidatosPresidenciais = [
  { id_candidato: 101, nome_candidato: "José Eduardo dos Santos", id_partido: 1,  votos: null, percentagem: 49.57, posicao: 1 },
  { id_candidato: 102, nome_candidato: "Jonas Savimbi",           id_partido: 2,  votos: null, percentagem: 40.07, posicao: 2 },
  { id_candidato: 103, nome_candidato: "António Alberto Neto",    id_partido: 3,  votos: null, percentagem: 2.16,  posicao: 3 },
  { id_candidato: 104, nome_candidato: "Holden Roberto",          id_partido: 4,  votos: null, percentagem: 2.11,  posicao: 4 },
  { id_candidato: 105, nome_candidato: "Honorato Lando",          id_partido: 5,  votos: null, percentagem: 1.92,  posicao: 5 },
  { id_candidato: 106, nome_candidato: "Luís dos Passos",         id_partido: 6,  votos: null, percentagem: 1.47,  posicao: 6 },
  { id_candidato: 107, nome_candidato: "Bengui Pedro João",       id_partido: 7,  votos: null, percentagem: 0.97,  posicao: 7 },
  { id_candidato: 108, nome_candidato: "Simão Cacete",            id_partido: 8,  votos: null, percentagem: 0.67,  posicao: 8 },
  { id_candidato: 109, nome_candidato: "Daniel Chipenda",         id_partido: null, votos: null, percentagem: 0.52, posicao: 9 },
  { id_candidato: 110, nome_candidato: "Anália de Victória Pereira", id_partido: 5, votos: 11475, percentagem: 0.29, posicao: 10 },
  { id_candidato: 111, nome_candidato: "Rui de Victória Pereira", id_partido: 10, votos: null, percentagem: 0.23,  posicao: 11 }
];

const resultadosParlamentares = [
  { id_resultado: 5001, id_partido: 1,  votos: 2124126, percentagem: 53.74, assentos: 129 },
  { id_resultado: 5002, id_partido: 2,  votos: null,    percentagem: 34.10, assentos: 70 },
  { id_resultado: 5003, id_partido: 4,  votos: null,    percentagem: 2.40,  assentos: 5 },
  { id_resultado: 5004, id_partido: 5,  votos: null,    percentagem: 2.39,  assentos: 3 },
  { id_resultado: 5005, id_partido: 11, votos: null,    percentagem: 2.27,  assentos: 6 },
  { id_resultado: 5006, id_partido: 6,  votos: null,    percentagem: null,  assentos: 1 },
  { id_resultado: 5007, id_partido: 12, votos: null,    percentagem: null,  assentos: 1 },
  { id_resultado: 5008, id_partido: 7,  votos: null,    percentagem: null,  assentos: 1 },
  { id_resultado: 5009, id_partido: 13, votos: null,    percentagem: null,  assentos: 1 },
  { id_resultado: 5010, id_partido: 14, votos: null,    percentagem: null,  assentos: 1 },
  { id_resultado: 5011, id_partido: 9,  votos: null,    percentagem: null,  assentos: 1 }
];

const timeline = [
  { data: "1991-05-31", titulo: "Acordos de Bicesse", descricao: "Assinatura em Portugal entre o Governo (MPLA) e a UNITA. Cessar-fogo e calendário eleitoral." },
  { data: "1992-05-20", titulo: "Início do Registo Eleitoral", descricao: "Abertura do recenseamento; prolonga-se até 31 de julho de 1992." },
  { data: "1992-09-29", titulo: "Eleições Gerais (1.º dia)", descricao: "Realização das primeiras eleições multipartidárias (presidenciais e legislativas)." },
  { data: "1992-09-30", titulo: "Eleições Gerais (2.º dia)", descricao: "Continuação da votação; participação superior a 91%." },
  { data: "1992-10-17", titulo: "Anúncio dos Resultados", descricao: "A Comissão Nacional Eleitoral divulga os resultados finais." },
  { data: "1992-10-31", titulo: "Colapso do Processo de Paz", descricao: "UNITA rejeita os resultados; confrontos armados em Luanda levam ao regresso à guerra civil." }
];