# Eleições Angola 1992

> Aplicação web com os dados históricos das primeiras eleições multipartidárias de Angola, realizadas a 29 e 30 de setembro de 1992.

---

## Sobre o projeto

O projeto inclui uma API REST em Node.js, um frontend estático com DataTables e Chart.js, base de dados em JSON ou SQLite, testes automatizados, Docker e scripts Python de automação.

O objetivo é preservar e tornar acessíveis os dados das primeiras eleições multipartidárias de Angola, permitindo consulta interativa e consumo programático.

---

## Requisitos

| Ferramenta | Versão mínima | Obrigatório |
| --- | --- | --- |
| Node.js | 18 | Sim |
| npm | 9 | Sim |
| Git | 2.30 | Sim |
| Python | 3.10 | Opcional |
| Docker | 20 | Opcional |

---

## Instalação

### 1. Clonar o repositório

    git clone https://github.com/wladitavar/eleicoes-angola-1992.git
    cd eleicoes-angola-1992

### 2. Instalar dependências

    npm install

### 3. Criar base SQLite (opcional)

    python -c "import sqlite3; c = sqlite3.connect('eleicoes.db'); c.executescript(open('database/schema.sql', encoding='utf-8').read()); c.executescript(open('database/seed.sql', encoding='utf-8').read()); c.commit(); c.close()"

---

## Execução

### Modo desenvolvimento

    npm run dev

Reinicia automaticamente quando o código muda.

### Modo produção

    npm start

O servidor fica disponível em http://localhost:8000.

---

## URLs principais

| URL | Descrição |
| --- | --- |
| http://localhost:8000 | Frontend |
| http://localhost:8000/api/health | Estado da API |
| http://localhost:8000/api/eleicoes/1992 | Metadados da eleição |
| http://localhost:8000/api/eleicoes/1992/partidos | Lista de partidos |
| http://localhost:8000/api/eleicoes/1992/presidenciais | Candidatos presidenciais |
| http://localhost:8000/api/eleicoes/1992/parlamentares | Resultados parlamentares |
| http://localhost:8000/api/eleicoes/1992/timeline | Cronologia |
| http://localhost:8000/api/eleicoes/1992/tudo | Todos os dados |

---

## Testes

    npm test

Cobertura:

    npm run test:coverage

---

## Docker

Construir e arrancar:

    docker compose up -d --build

Verificar:

    docker compose ps

Parar:

    docker compose down

---

## Estrutura do projeto

    eleicoes-angola-1992/
      public/               Frontend (index.html, app.js, style.css)
      public/data/          Ficheiros JSON com os dados
      database/             Esquema SQL e dados iniciais
      scripts/              Scripts Python de automação
      tests/                Testes Jest
      server.js             Servidor Express
      db.js                 Camada de dados
      package.json          Dependências e scripts
      Dockerfile            Imagem Docker
      docker-compose.yml    Orquestração

---

## API REST

### Endpoints disponíveis

- GET /api/health
- GET /api/eleicoes/:ano
- GET /api/eleicoes/:ano/partidos
- GET /api/eleicoes/:ano/presidenciais
- GET /api/eleicoes/:ano/parlamentares
- GET /api/eleicoes/:ano/timeline
- GET /api/eleicoes/:ano/tudo

### Exemplo de resposta

Pedido:

    GET /api/health

Resposta:

    {
      "status": "ok",
      "fonte": "json",
      "ambiente": "development"
    }

---

## Dados disponíveis

| Conjunto | Quantidade |
| --- | --- |
| Eleições | 1 (1992) |
| Partidos | 14 |
| Candidatos presidenciais | 11 |
| Resultados parlamentares | 11 (220 assentos) |
| Eventos na cronologia | 6 |

---

## Scripts de automação

### Atualizar o repositório

    python scripts/update_repo.py --auto "feat: descrição da alteração"

### Gerar snapshot do código

    python scripts/generate_snapshot.py

### Testar o script de atualização

    python scripts/test_update_repo.py

### Remover BOM dos ficheiros JSON

    python scripts/remove_bom.py

---

## Segurança

- Helmet com Content Security Policy
- CORS restrito por origem
- Limite de pedidos por IP
- Compressão gzip
- Sem credenciais no código

---

## Licença

MIT. Ver o ficheiro LICENSE para mais informação.

---

## Autor

Wladimir Tavares

---

## Contribuições

Contribuições são bem-vindas. Abrir uma issue ou um pull request no repositório do GitHub.

Repositório: https://github.com/wladitavar/eleicoes-angola-1992