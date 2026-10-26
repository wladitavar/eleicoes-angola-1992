/**
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
