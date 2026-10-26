#!/usr/bin/env python3
"""
update_repo.py — Gestão completa do repositório Git + geração de ficheiros.

Faz, de uma vez:
  0. Escreve/atualiza TODOS os ficheiros da versão atual do projeto
     (backup automático em .backup/<timestamp>/ antes de substituir).
  1. Mostra estado do repositório (branch, tags, alterações).
  2. Valida ficheiros críticos (.gitignore, .gitattributes, scripts).
  3. Gera snapshot (ZIP + MD + JSON + SHA-256).
  4. Adiciona alterações e faz commit convencional.
  5. Cria tag anotada com semver automático.
  6. (Opcional) Push para o remoto.

Uso:
  python scripts/update_repo.py                    # ciclo interativo completo
  python scripts/update_repo.py --auto "feat: X"   # commit automático
  python scripts/update_repo.py --dry-run          # só mostra o que faria
  python scripts/update_repo.py --files-only       # só escreve ficheiros
  python scripts/update_repo.py --fix-now "fix: X" # escreve + valida + commita
  python scripts/update_repo.py --no-files         # salta escrita de ficheiros
  python scripts/update_repo.py --no-snapshot      # sem snapshot
  python scripts/update_repo.py --no-push --no-tag # sem push nem tag
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
# CONTEÚDO DOS FICHEIROS DA VERSÃO ATUAL
# ----------------------------------------------------------------------
# Cada chave é o caminho relativo à raiz do projeto.
# O valor é uma string com o conteúdo completo.
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
  "version": "0.1.0",
  "description": "Frontend estático — versão inicial das eleições de Angola de 1992",
  "private": true,
  "license": "MIT"
}
""",

    # Os scripts são escritos pelo próprio script (para evitar duplicação):
    # scripts/generate_snapshot.py, scripts/update_repo.py — ver secção 3.
}

# ======================================================================
# Helpers de escrita de ficheiros
# ======================================================================
def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sha256_ficheiro(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def escrever_ficheiro(rel: str, conteudo: str, dry_run: bool, backup: Path | None) -> str:
    """
    Escreve (ou atualiza) um ficheiro com o conteúdo dado.
    Devolve: 'criado' | 'atualizado' | 'inalterado' | 'dry-criado' | 'dry-atualizado'
    """
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
    """
    Escreve todos os ficheiros da versão atual.
    Devolve um dicionário com contagem por estado.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = None if dry_run else (BACKUP_DIR / timestamp)

    print(C.bold("\n═══ 0. ESCRITA DOS FICHEIROS DA VERSÃO ATUAL ═══"))
    if dry_run:
        print(C.aviso("  [dry-run] Nenhum ficheiro será escrito."))
    else:
        print(C.info(f"  Backup: {backup}"))

    contagem = {"criado": 0, "atualizado": 0, "inalterado": 0,
                "dry-criado": 0, "dry-atualizado": 0}
    detalhes = []

    # ---------- ficheiros fixos ----------
    for rel, conteudo in FICHEIROS_VERSAO_ATUAL.items():
        estado = escrever_ficheiro(rel, conteudo, dry_run, backup)
        contagem[estado] = contagem.get(estado, 0) + 1
        detalhes.append((estado, rel))

    # ---------- generate_snapshot.py ----------
    conteudo_gen = _conteudo_generate_snapshot()
    estado = escrever_ficheiro("scripts/generate_snapshot.py",
                               conteudo_gen, dry_run, backup)
    contagem[estado] = contagem.get(estado, 0) + 1
    detalhes.append((estado, "scripts/generate_snapshot.py"))

    # ---------- update_repo.py (auto-atualização) ----------
    if SCRIPTS_DIR.joinpath("update_repo.py").exists():
        try:
            conteudo_self = Path(__file__).read_text(encoding="utf-8")
            estado = escrever_ficheiro("scripts/update_repo.py",
                                       conteudo_self, dry_run, backup)
            contagem[estado] = contagem.get(estado, 0) + 1
            detalhes.append((estado, "scripts/update_repo.py"))
        except Exception:
            pass

    # ---------- relatório ----------
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


def _conteudo_generate_snapshot() -> str:
    """
    Conteúdo completo e atualizado de scripts/generate_snapshot.py.
    VERSÃO CORRIGIDA: a string do print() está numa única linha.
    """
    return '''#!/usr/bin/env python3
"""
generate_snapshot.py — Gera um snapshot completo do código da última versão.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXCLUSAO_PADRAO = {
    ".git", "node_modules", "coverage", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", ".DS_Store", ".pytest_cache", ".mypy_cache",
    "dist", "snapshots", ".backup",
}
EXCLUSAO_EXT = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo"}


def cor(txt, tipo="info"):
    m = {"ok": "\\033[92m", "aviso": "\\033[93m", "erro": "\\033[91m",
         "info": "\\033[96m", "bold": "\\033[1m", "fim": "\\033[0m"}
    return f"{m.get(tipo, '')}{txt}{m['fim']}"


def run(cmd, check=True):
    p = subprocess.run(cmd, shell=isinstance(cmd, str),
                       capture_output=True, text=True, check=False)
    if check and p.returncode != 0:
        raise RuntimeError(f"Comando falhou: {cmd}\\n{p.stderr}")
    return p.stdout.strip()


def versao_atual():
    try:
        out = run(["git", "describe", "--tags", "--abbrev=0"], check=False)
        if out:
            return out
    except Exception:
        pass
    pkg = Path("package.json")
    if pkg.exists():
        try:
            return "v" + json.loads(pkg.read_text(encoding="utf-8")).get("version", "0.0.0")
        except Exception:
            pass
    return "v0.0.0"


def commit_atual():
    try:
        return run(["git", "rev-parse", "--short", "HEAD"], check=False) or "n/a"
    except Exception:
        return "n/a"


def branch_atual():
    try:
        return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False) or "n/a"
    except Exception:
        return "n/a"


def deve_excluir(caminho: Path, raiz: Path, incluir_db: bool) -> bool:
    rel = caminho.relative_to(raiz)
    for p in rel.parts:
        if p in EXCLUSAO_PADRAO:
            return True
    if caminho.suffix.lower() in EXCLUSAO_EXT and not incluir_db:
        return True
    if caminho.name == "eleicoes.db" and not incluir_db:
        return True
    return False


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def gerar_snapshot(tag, output_dir, incluir_db):
    raiz = Path.cwd()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    versao_limpa = tag.lstrip("v").replace("/", "-")
    base_nome = f"angola92_{versao_limpa}_{timestamp}"

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path  = output_dir / f"{base_nome}.zip"
    md_path   = output_dir / f"{base_nome}.md"
    json_path = output_dir / f"{base_nome}.json"
    sha_path  = output_dir / f"{base_nome}.sha256"

    ficheiros = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for caminho in sorted(raiz.rglob("*")):
            if not caminho.is_file():
                continue
            if deve_excluir(caminho, raiz, incluir_db):
                continue
            rel = caminho.relative_to(raiz)
            zf.write(caminho, rel.as_posix())
            ficheiros.append({
                "caminho": rel.as_posix(),
                "bytes":   caminho.stat().st_size,
                "sha256":  sha256(caminho),
            })

    meta = {
        "versao":          tag,
        "commit":          commit_atual(),
        "branch":          branch_atual(),
        "gerado_em":       timestamp,
        "total_ficheiros": len(ficheiros),
        "total_bytes":     sum(f["bytes"] for f in ficheiros),
        "zip_sha256":      sha256(zip_path),
        "ficheiros":       ficheiros,
    }
    json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    linhas = [
        "# Snapshot — Eleições Angola 1992",
        "",
        f"- **Versão:** `{tag}`",
        f"- **Commit:** `{meta['commit']}`",
        f"- **Branch:** `{meta['branch']}`",
        f"- **Gerado em:** {timestamp}",
        f"- **Ficheiros:** {meta['total_ficheiros']}",
        f"- **Tamanho total:** {meta['total_bytes']:,} bytes".replace(",", "."),
        f"- **SHA-256 do ZIP:** `{meta['zip_sha256']}`",
        "",
        "## Ficheiros incluídos",
        "",
        "| # | Caminho | Bytes | SHA-256 (12 primeiros) |",
        "|---|---------|------:|------------------------|",
    ]
    for i, f in enumerate(ficheiros, 1):
        linhas.append(f"| {i} | `{f['caminho']}` | {f['bytes']} | `{f['sha256'][:12]}` |")
    md_path.write_text("\\n".join(linhas), encoding="utf-8")

    sha_path.write_text(f"{meta['zip_sha256']}  {zip_path.name}\\n", encoding="utf-8")

    return {"zip": zip_path, "md": md_path, "json": json_path,
            "sha256": sha_path, "meta": meta}


def main():
    ap = argparse.ArgumentParser(description="Gera snapshot do código da última versão")
    ap.add_argument("--tag", help="Tag/versão a usar no nome (default: última tag Git)")
    ap.add_argument("--output", default="snapshots", help="Diretório de saída")
    ap.add_argument("--include-db", action="store_true", help="Incluir *.db / *.sqlite")
    args = ap.parse_args()

    marcadores = [
        Path("package.json"),
        Path("server.js"),
        Path("index.html"),
        Path(".git"),
    ]
    if not any(p.exists() for p in marcadores):
        # ---- MENSAGEM NUMA ÚNICA LINHA (corrige SyntaxError) ----
        print(cor("✖ Execute na raiz do projeto (esperado package.json, server.js, index.html ou .git/).", "erro"))
        sys.exit(1)

    tag = args.tag or versao_atual()
    output = Path(args.output).resolve()

    print(cor("\\n╔══════════════════════════════════════════════╗", "bold"))
    print(cor("║   SNAPSHOT DO CÓDIGO — ÚLTIMA VERSÃO        ║", "bold"))
    print(cor("╚══════════════════════════════════════════════╝", "bold"))
    print(f"  Versão : {cor(tag, 'ok')}")
    print(f"  Commit : {commit_atual()}")
    print(f"  Branch : {branch_atual()}")
    print(f"  Output : {output}")

    try:
        r = gerar_snapshot(tag, output, args.include_db)
    except Exception as e:
        print(cor(f"\\n✖ Erro: {e}", "erro"))
        sys.exit(1)

    m = r["meta"]
    print(cor("\\n✅ Snapshot gerado.", "ok"))
    print(f"   ZIP            : {r['zip']}")
    print(f"   Manifesto MD   : {r['md']}")
    print(f"   Metadados JSON : {r['json']}")
    print(f"   SHA-256        : {r['sha256']}")
    print(f"   Ficheiros      : {m['total_ficheiros']}  |  "
          f"Tamanho: {m['total_bytes']:,} bytes".replace(",", "."))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(cor("\\n\\n⏹ Interrompido.", "aviso"))
        sys.exit(130)
'''


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
    linhas = GITATTRIBUTES.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, linha in enumerate(linhas, 1):
        s = linha.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("@'") or "Out-File" in s or "|" in s:
            return False, f"linha {i} inválida: {linha[:60]}"
    return True, "OK"


def validar_scripts(dry_run: bool = False):
    """
    Valida a sintaxe dos scripts Python.
    Em dry-run, os scripts podem ainda estar no estado antigo (com erros),
    por isso reporta mas não falha o ciclo.
    """
    problemas = []
    for f in SCRIPTS_DIR.glob("*.py"):
        try:
            run_cmd([sys.executable, "-m", "py_compile", str(f)], check=True)
        except Exception as e:
            # Em dry-run, só avisa (não conta como falha)
            problemas.append(f"{f.name}: {e}")
    if not problemas:
        return True, "OK"
    if dry_run:
        return True, "aviso (dry-run): " + "; ".join(problemas)[:200]
    return False, "; ".join(problemas)


def validar_geral(dry_run: bool = False):
    """Valida tudo de uma vez."""
    ok1, m1 = validar_gitignore()
    ok2, m2 = validar_gitattributes()
    ok3, m3 = validar_scripts(dry_run=dry_run)
    return ok1 and ok2 and ok3, (ok1, m1, ok2, m2, ok3, m3)


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
    # Em dry-run, scripts podem estar em estado antigo — apresentar como aviso
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
        print(C.erro(f"  ✖ Falha: {err}"))
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
# Modo --fix-now (escreve + valida + commita numa só passagem)
# ======================================================================
def modo_fix_now(msg, no_snapshot=False, no_push=False, no_tag=False):
    """
    Atalho que resolve o cenário atual:
      1. Escreve todos os ficheiros (substitui os quebrados).
      2. Valida tudo.
      3. Gera snapshot.
      4. Commit + push + tag.
    """
    print(C.bold("\n=== MODO FIX-NOW ===\n"))

    # 1) Escrever ficheiros
    contagem = escrever_todos_ficheiros(dry_run=False)
    if contagem["criado"] + contagem["atualizado"] == 0:
        print(C.info("\n· Nenhum ficheiro precisou de ser escrito."))

    # 2) Validar (agora sim, os scripts já estão corretos)
    print(C.bold("\n═══ VALIDAÇÃO PÓS-ESCRITA ═══"))
    ok, (ok1, m1, ok2, m2, ok3, m3) = validar_geral(dry_run=False)
    print(f"  {C.ok('✔') if ok1 else C.erro('✖')} .gitignore     → {m1}")
    print(f"  {C.ok('✔') if ok2 else C.erro('✖')} .gitattributes → {m2}")
    print(f"  {C.ok('✔') if ok3 else C.erro('✖')} scripts/*.py   → {m3}")

    if not ok:
        print(C.erro("\n✖ Validação falhou. Corrija os erros acima e tente de novo."))
        return 1

    # 3) Snapshot
    if not no_snapshot:
        passo_snapshot()

    # 4) Commit + push + tag
    git("add", "-A")
    out, err, code = git("commit", "-m", msg, check=False)
    if code != 0:
        if "nothing to commit" in out or "nothing to commit" in err:
            print(C.aviso("⚠ Nada a commitar (ficheiros já estavam sincronizados)."))
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
    ap = argparse.ArgumentParser(description="Gestão completa do repositório + ficheiros")
    ap.add_argument("--auto", metavar="MSG", help="Commit automático")
    ap.add_argument("--fix-now", metavar="MSG", help="Escreve + valida + commita numa só passagem")
    ap.add_argument("--dry-run", action="store_true", help="Só mostrar (não escreve nem commita)")
    ap.add_argument("--files-only", action="store_true", help="Só escrever ficheiros")
    ap.add_argument("--no-files", action="store_true", help="Saltar escrita de ficheiros")
    ap.add_argument("--no-snapshot", action="store_true", help="Sem snapshot")
    ap.add_argument("--no-push", action="store_true", help="Sem push")
    ap.add_argument("--no-tag", action="store_true", help="Sem tag")
    args = ap.parse_args()

    print(C.bold("\n╔══════════════════════════════════════════════╗"))
    print(C.bold("║   UPDATE REPO — GESTÃO + FICHEIROS          ║"))
    print(C.bold("╚══════════════════════════════════════════════╝"))

    # ---------- modo --files-only ----------
    if args.files_only:
        contagem = escrever_todos_ficheiros(dry_run=False)
        if contagem["criado"] + contagem["atualizado"] > 0:
            print(C.ok("\n✅ Ficheiros escritos. Use 'git add -A && git commit' para versionar."))
        else:
            print(C.info("\n· Nenhum ficheiro precisou de ser escrito."))
        return 0

    # ---------- modo --fix-now ----------
    if args.fix_now:
        if not e_repo_git():
            print(C.erro("✖ Não está dentro de um repositório Git."))
            sys.exit(1)
        sys.exit(modo_fix_now(args.fix_now, args.no_snapshot, args.no_push, args.no_tag))

    # ---------- exigir repositório Git (a partir daqui) ----------
    if not e_repo_git():
        print(C.erro("✖ Não está dentro de um repositório Git."))
        sys.exit(1)

    # ---------- 0. escrita de ficheiros ----------
    if not args.no_files:
        escrever_todos_ficheiros(dry_run=args.dry_run)

    # ---------- 1–2. estado + validações ----------
    alteracoes = passo_estado()
    valido = passo_validacoes(dry_run=args.dry_run)

    if args.dry_run:
        print(C.aviso("\n[dry-run] Nenhuma alteração efetuada."))
        # Em dry-run, os erros de scripts não contam como falha (podem ser antigos)
        sys.exit(0)

    if not valido:
        print(C.erro("\n✖ Corrija os problemas antes de continuar."))
        sys.exit(1)

    if not alteracoes:
        print(C.ok("\n✔ Nada a fazer. Repositório limpo."))
        sys.exit(0)

    # ---------- modo automático ----------
    if args.auto:
        sys.exit(modo_auto(args.auto, args.no_snapshot, args.no_push,
                           args.no_tag, no_files=True))

    # ---------- modo interativo ----------
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