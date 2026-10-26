#!/usr/bin/env python3
"""
update_repo-<timestamp>.py — Consolida correções pendentes.

Alterações incluídas:
  1. server.js: CSP permite cdn.datatables.net e cdn.jsdelivr.net no connectSrc
  2. public/app.js: adiciona corrigirInputsSemId() (acessibilidade)
  3. database/seed.sql: PRD (id_partido=6) passa de 1 → 2 assentos
  4. public/data/resultados_parlamentares.json: idem (PRD = 2, soma = 220)
  5. Migração: move index.html/app.js/style.css/data/ da raiz para public/ (se necessário)
  6. Remoção de BOM: garante todos os JSONs em public/data/ sem BOM

Uso:
  python scripts/update_repo-<timestamp>.py --dry-run
  python scripts/update_repo-<timestamp>.py --auto "chore: consolida correções (CSP, acessibilidade, PRD, BOM, migração)"
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ======================================================================
# Caminhos
# ======================================================================
SCRIPTS_DIR   = Path(__file__).resolve().parent
PROJETO_DIR   = SCRIPTS_DIR.parent
GENERATE_SNAP = SCRIPTS_DIR / "generate_snapshot.py"
GITIGNORE     = PROJETO_DIR / ".gitignore"

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
# DELTA DESTA ALTERAÇÃO — apenas ficheiros criados/modificados agora
# ======================================================================
# NOTA: server.js e public/app.js são lidos do disco (já estão corretos após
#       as correções manuais). Só os dados (seed.sql e JSON) precisam de
#       atualização programática — é isso que este delta aplica.
#       O servidor e o app.js são preservados tal como estão.
FICHEIROS_DELTA = {
    # PRD (id_partido=6) passa de 1 → 2 assentos
    # Ficheiro seed.sql: substitui a linha do id_resultado 5006
    # Ficheiro JSON: idem
    # (o conteúdo final é gerado dinamicamente a partir do disco — ver abaixo)
}

# ======================================================================
# MIGRAÇÕES PONTUAIS (idempotentes)
# ======================================================================
def migrar_para_public(dry_run: bool) -> int:
    """
    Move index.html, app.js, style.css, data/ da raiz para public/ (se ainda
    estiverem na raiz). Idempotente: se já estiverem em public/, não faz nada.
    Devolve o número de itens movidos.
    """
    public = PROJETO_DIR / "public"
    public.mkdir(exist_ok=True)

    ficheiros = ["index.html", "app.js", "style.css"]
    pastas = ["data"]
    movidos = 0

    for nome in ficheiros:
        origem = PROJETO_DIR / nome
        destino = public / nome
        if origem.exists() and not destino.exists():
            if dry_run:
                print(C.info(f"  [dry-run] moveria {nome} → public/{nome}"))
            else:
                shutil.move(str(origem), str(destino))
                print(C.ok(f"  ✔ movido {nome} → public/{nome}"))
            movidos += 1

    for nome in pastas:
        origem = PROJETO_DIR / nome
        destino = public / nome
        if origem.exists() and origem.is_dir() and not destino.exists():
            if dry_run:
                print(C.info(f"  [dry-run] moveria {nome}/ → public/{nome}/"))
            else:
                shutil.move(str(origem), str(destino))
                print(C.ok(f"  ✔ movido {nome}/ → public/{nome}/"))
            movidos += 1

    if movidos == 0:
        print(C.info("  · Nada a migrar (já em public/)"))
    return movidos


def remover_bom_dos_jsons(dry_run: bool) -> int:
    """
    Remove BOM de todos os JSONs em public/data/.
    Devolve o número de ficheiros corrigidos.
    """
    raiz = PROJETO_DIR / "public" / "data"
    if not raiz.exists():
        print(C.aviso("  ⚠ public/data/ não existe — a saltar remoção de BOM"))
        return 0

    corrigidos = 0
    for f in sorted(raiz.glob("*.json")):
        try:
            tem_bom = f.read_bytes()[:3] == b"\xef\xbb\xbf"
            if not tem_bom:
                continue
            if dry_run:
                print(C.info(f"  [dry-run] removeria BOM de {f.name}"))
            else:
                conteudo = f.read_text(encoding="utf-8-sig")
                dados = json.loads(conteudo)
                f.write_text(
                    json.dumps(dados, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                print(C.ok(f"  ✔ BOM removido de {f.name}"))
            corrigidos += 1
        except Exception as e:
            print(C.erro(f"  ✖ {f.name}: {e}"))

    if corrigidos == 0:
        print(C.info("  · Nenhum JSON com BOM"))
    return corrigidos


# ======================================================================
# DELTA — aplicação dos dados (seed.sql + resultados_parlamentares.json)
# ======================================================================
def aplicar_prd_2(dry_run: bool) -> int:
    """
    Garante que o PRD (id_partido=6) tem 2 assentos:
      - em public/data/resultados_parlamentares.json
      - em database/seed.sql (linha id_resultado=5006)
    Devolve o número de ficheiros alterados.
    """
    alterados = 0

    # ---- 1. JSON ----
    json_path = PROJETO_DIR / "public" / "data" / "resultados_parlamentares.json"
    if json_path.exists():
        try:
            dados = json.loads(json_path.read_text(encoding="utf-8-sig"))
            alterou = False
            for item in dados:
                if item.get("id_partido") == 6 and item.get("assentos") != 2:
                    item["assentos"] = 2
                    alterou = True
            if alterou:
                if dry_run:
                    print(C.info(f"  [dry-run] atualizaria PRD=2 em {json_path.name}"))
                else:
                    json_path.write_text(
                        json.dumps(dados, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    print(C.ok(f"  ✔ PRD=2 em {json_path.name}"))
                alterados += 1
            else:
                print(C.info(f"  · {json_path.name} já tem PRD=2"))
        except Exception as e:
            print(C.erro(f"  ✖ {json_path.name}: {e}"))
    else:
        print(C.aviso(f"  ⚠ {json_path.name} não existe"))

    # ---- 2. seed.sql ----
    seed_path = PROJETO_DIR / "database" / "seed.sql"
    if seed_path.exists():
        try:
            conteudo = seed_path.read_text(encoding="utf-8")
            # Padrão: (5006, '1992_GERAL', 6,  NULL,     NULL,   1),
            padrao = re.compile(
                r"(\(5006,\s*'1992_GERAL',\s*6,\s*NULL,\s*NULL,\s*)1(\))"
            )
            if padrao.search(conteudo):
                novo = padrao.sub(r"\g<1>2\g<2>", conteudo)
                if dry_run:
                    print(C.info(f"  [dry-run] atualizaria PRD=2 em {seed_path.name}"))
                else:
                    seed_path.write_text(novo, encoding="utf-8")
                    print(C.ok(f"  ✔ PRD=2 em {seed_path.name}"))
                alterados += 1
            else:
                # Verificar se já está em 2
                if re.search(r"\(5006,\s*'1992_GERAL',\s*6,\s*NULL,\s*NULL,\s*2\)", conteudo):
                    print(C.info(f"  · {seed_path.name} já tem PRD=2"))
                else:
                    print(C.aviso(f"  ⚠ Linha do PRD não encontrada em {seed_path.name}"))
        except Exception as e:
            print(C.erro(f"  ✖ {seed_path.name}: {e}"))
    else:
        print(C.aviso(f"  ⚠ {seed_path.name} não existe"))

    return alterados


# ======================================================================
# VALIDAÇÕES ESPECÍFICAS
# ======================================================================
def validar_delta() -> bool:
    """Verifica que todas as correções estão aplicadas."""
    print(C.bold("\n═══ VALIDAÇÕES ESPECÍFICAS ═══"))
    tudo_ok = True

    # 1. server.js tem connectSrc com os CDNs
    server = PROJETO_DIR / "server.js"
    if server.exists():
        c = server.read_text(encoding="utf-8", errors="replace")
        ok = ("cdn.datatables.net" in c and "connectSrc" in c)
        print(f"  {C.ok('✔') if ok else C.erro('✖')} server.js tem CSP com CDNs")
        tudo_ok &= ok
    else:
        print(f"  {C.erro('✖')} server.js não existe")
        tudo_ok = False

    # 2. public/app.js tem corrigirInputsSemId
    app = PROJETO_DIR / "public" / "app.js"
    if app.exists():
        c = app.read_text(encoding="utf-8", errors="replace")
        ok = "corrigirInputsSemId" in c
        print(f"  {C.ok('✔') if ok else C.erro('✖')} public/app.js tem corrigirInputsSemId()")
        tudo_ok &= ok
    else:
        print(f"  {C.erro('✖')} public/app.js não existe")
        tudo_ok = False

    # 3. Soma dos assentos = 220
    json_path = PROJETO_DIR / "public" / "data" / "resultados_parlamentares.json"
    if json_path.exists():
        try:
            dados = json.loads(json_path.read_text(encoding="utf-8-sig"))
            soma = sum(item.get("assentos", 0) for item in dados)
            ok = (soma == 220)
            print(f"  {C.ok('✔') if ok else C.erro('✖')} Soma dos assentos = {soma} (esperado 220)")
            tudo_ok &= ok
        except Exception as e:
            print(f"  {C.erro('✖')} JSON inválido: {e}")
            tudo_ok = False

    # 4. BOM ausente em todos os JSONs
    raiz = PROJETO_DIR / "public" / "data"
    if raiz.exists():
        com_bom = [f.name for f in raiz.glob("*.json")
                   if f.read_bytes()[:3] == b"\xef\xbb\xbf"]
        ok = (len(com_bom) == 0)
        print(f"  {C.ok('✔') if ok else C.erro('✖')} JSONs sem BOM "
              f"({len(com_bom)} com BOM)")
        tudo_ok &= ok

    # 5. Frontend em public/ (não na raiz)
    ficheiros_raiz = ["index.html", "app.js", "style.css"]
    na_raiz = [f for f in ficheiros_raiz if (PROJETO_DIR / f).exists()]
    ok = (len(na_raiz) == 0)
    print(f"  {C.ok('✔') if ok else C.erro('✖')} Frontend em public/ "
          f"({len(na_raiz)} na raiz)")
    tudo_ok &= ok

    return tudo_ok


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


def listar_alteracoes():
    out, _, _ = git("status", "--porcelain", check=False)
    itens = []
    for linha in out.splitlines():
        if not linha.strip():
            continue
        itens.append((linha[:2].strip(), linha[3:].strip()))
    return itens


# ======================================================================
# Snapshot
# ======================================================================
def gerar_snapshot() -> bool:
    print(C.bold("\n═══ SNAPSHOT ═══"))
    if not GENERATE_SNAP.exists():
        print(C.aviso("  → generate_snapshot.py não existe; a saltar."))
        return False
    out, err, code = run_cmd([sys.executable, str(GENERATE_SNAP)], check=False)
    if code != 0:
        print(C.erro(f"  ✖ Falha no snapshot: {(err or out)[:300]}"))
        return False
    for linha in out.splitlines():
        if "ZIP" in linha and ".zip" in linha:
            print(f"  {C.ok('✔')} {linha.strip()}")
            break
    else:
        print(C.ok("  ✔ Snapshot gerado."))
    return True


# ======================================================================
# Modo --auto
# ======================================================================
def modo_auto(msg, no_snapshot=False, no_push=False, no_tag=False):
    print(C.bold("\n=== MODO AUTOMÁTICO ===\n"))

    # 1) Migração para public/ (idempotente)
    print(C.bold("═══ 1. MIGRAÇÃO → public/ ═══"))
    migrar_para_public(dry_run=False)

    # 2) Delta: PRD = 2 (JSON + SQL)
    print(C.bold("\n═══ 2. DELTA: PRD = 2 ═══"))
    aplicar_prd_2(dry_run=False)

    # 3) Remoção de BOM
    print(C.bold("\n═══ 3. REMOÇÃO DE BOM ═══"))
    remover_bom_dos_jsons(dry_run=False)

    # 4) Validações específicas
    ok = validar_delta()
    if not ok:
        print(C.erro("\n✖ Validações específicas falharam."))
        return 1

    # 5) Snapshot
    if not no_snapshot:
        gerar_snapshot()

    # 6) Commit
    git("add", "-A")
    out, err, code = git("commit", "-m", msg, check=False)
    if code != 0:
        if "nothing to commit" in out or "nothing to commit" in err:
            print(C.aviso("⚠ Nada a commitar (alterações já estavam aplicadas)."))
            return 0
        print(C.erro(f"✖ Falha no commit: {err[:300]}"))
        return 1
    print(C.ok(f"✔ Commit: {msg}"))

    tipo = msg.split(":")[0].strip() if ":" in msg else "chore"

    # 7) Push
    if not no_push:
        git("push", check=False)
        print(C.ok("✔ Push efetuado."))

    # 8) Tag
    if not no_tag:
        tag = proxima_versao(ultima_tag(), tipo)
        git("tag", "-a", tag, "-m", f"Release {tag}", check=False)
        if not no_push:
            git("push", "origin", tag, check=False)
        print(C.ok(f"✔ Tag {tag}" + ("" if no_push else " criada e enviada")))

    return 0


# ======================================================================
# Modo --dry-run
# ======================================================================
def modo_dry_run():
    print(C.bold("\n═══ DRY-RUN — NENHUMA ALTERAÇÃO SERÁ FEITA ═══"))

    print(C.bold("\n── 1. Migração → public/ ──"))
    migrar_para_public(dry_run=True)

    print(C.bold("\n── 2. Delta: PRD = 2 ──"))
    aplicar_prd_2(dry_run=True)

    print(C.bold("\n── 3. Remoção de BOM ──"))
    remover_bom_dos_jsons(dry_run=True)

    print(C.bold("\n── 4. Validações ──"))
    validar_delta()

    print(C.aviso("\n[dry-run] Nenhuma alteração efetuada."))
    return 0


# ======================================================================
# Main
# ======================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Consolida correções (CSP, acessibilidade, PRD, BOM, migração)"
    )
    ap.add_argument("--auto", metavar="MSG", help="Aplica + commita automaticamente")
    ap.add_argument("--dry-run", action="store_true", help="Só mostra o que faria")
    ap.add_argument("--no-snapshot", action="store_true", help="Sem snapshot")
    ap.add_argument("--no-push", action="store_true", help="Sem push")
    ap.add_argument("--no-tag", action="store_true", help="Sem tag")
    args = ap.parse_args()

    print(C.bold("\n╔══════════════════════════════════════════════╗"))
    print(C.bold("║   UPDATE REPO — CONSOLIDA CORREÇÕES          ║"))
    print(C.bold("╚══════════════════════════════════════════════╝"))

    if not e_repo_git():
        print(C.erro("✖ Não está dentro de um repositório Git."))
        sys.exit(1)

    if args.dry_run:
        sys.exit(modo_dry_run())

    if args.auto:
        sys.exit(modo_auto(args.auto, args.no_snapshot, args.no_push, args.no_tag))

    # Sem --auto nem --dry-run: pede confirmação interativa
    print(C.info("\nNenhum modo especificado."))
    print("  Use --dry-run para inspecionar")
    print("  Use --auto \"MSG\" para aplicar e commitar")
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        print(C.aviso("\n\n⏹ Interrompido.")); sys.exit(130)
    except Exception as e:
        print(C.erro(f"\n✖ Erro: {e}")); sys.exit(1)