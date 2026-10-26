#!/usr/bin/env python3
"""
git_cycle.py — Ciclo interativo de gestão de alterações ao repositório Git.

Funcionalidades:
  • Verifica o estado do repositório (branch, alterações pendentes).
  • Mostra diff resumido por ficheiro.
  • Permite selecionar ficheiros a adicionar (ou todos).
  • Sugere mensagem de commit convencional (feat/fix/docs/...).
  • Cria o commit com assinatura (opcional).
  • Faz push para o remoto (opcional).
  • Cria tag de versão (opcional).

Uso:
  python3 scripts/git_cycle.py
  python3 scripts/git_cycle.py --auto "feat: adiciona endpoint X"
  python3 scripts/git_cycle.py --dry-run
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
COR = {
    "ok":    "\033[92m",
    "aviso": "\033[93m",
    "erro":  "\033[91m",
    "info":  "\033[96m",
    "fim":   "\033[0m",
    "bold":  "\033[1m",
}

def c(texto, tipo="info"):
    return f"{COR.get(tipo, '')}{texto}{COR['fim']}"

def run(cmd, check=True, capture=True):
    """Executa um comando e devolve (stdout, stderr, código)."""
    try:
        p = subprocess.run(
            cmd, shell=isinstance(cmd, str),
            capture_output=capture, text=True, check=False
        )
        if check and p.returncode != 0:
            raise RuntimeError(f"Comando falhou: {cmd}\n{p.stderr}")
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except FileNotFoundError as e:
        raise RuntimeError(f"Comando não encontrado: {e}")

def git(*args, check=True):
    return run(["git", *args], check=check)

def e_repo_git():
    _, _, code = git("rev-parse", "--is-inside-work-tree", check=False)
    return code == 0

def branch_atual():
    out, _, _ = git("rev-parse", "--abbrev-ref", "HEAD", check=False)
    return out or "(detached)"

def tem_alteracoes():
    out, _, _ = git("status", "--porcelain", check=False)
    return bool(out)

def listar_alteracoes():
    """Devolve lista de tuplos (status, ficheiro)."""
    out, _, _ = git("status", "--porcelain", check=False)
    itens = []
    for linha in out.splitlines():
        if not linha.strip():
            continue
        status = linha[:2].strip()
        ficheiro = linha[3:].strip()
        itens.append((status, ficheiro))
    return itens

def resumo_diff():
    out, _, _ = git("diff", "--stat", check=False)
    if not out:
        out, _, _ = git("diff", "--cached", "--stat", check=False)
    return out

def sugerir_tipo(ficheiros):
    """Sugere prefixo convencional com base nos ficheiros alterados."""
    tipos = []
    for _, f in ficheiros:
        f = f.lower()
        if f.endswith(".md") or "readme" in f:
            tipos.append("docs")
        elif "test" in f or f.endswith(".test.js"):
            tipos.append("test")
        elif f.endswith((".yml", ".yaml")) or "docker" in f:
            tipos.append("chore")
        elif f.endswith(".sql"):
            tipos.append("db")
        elif f.endswith((".css", ".html")):
            tipos.append("style")
        elif f.endswith(".js") or f.endswith(".py"):
            tipos.append("feat")
        else:
            tipos.append("chore")
    # Prioridade: feat > fix > docs > test > chore
    for t in ("feat", "fix", "docs", "test", "db", "style", "chore"):
        if t in tipos:
            return t
    return "chore"

def ultima_tag():
    out, _, _ = git("describe", "--tags", "--abbrev=0", check=False)
    return out or "v0.0.0"

def proxima_versao(tag, tipo):
    """Incrementa semver com base no tipo de commit."""
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", tag)
    if not m:
        return "v1.0.0"
    major, minor, patch = map(int, m.groups())
    if tipo in ("feat", "db"):
        minor += 1
        patch = 0
    elif tipo == "fix":
        patch += 1
    elif tipo in ("docs", "test", "chore", "style"):
        patch += 1
    return f"v{major}.{minor}.{patch}"

# ----------------------------------------------------------------------
# Passos do ciclo
# ----------------------------------------------------------------------
def passo_estado():
    print(c("\n═══ 1. ESTADO DO REPOSITÓRIO ═══", "bold"))
    print(f"  Branch : {c(branch_atual(), 'ok')}")
    print(f"  Última tag: {c(ultima_tag(), 'ok')}")

    alteracoes = listar_alteracoes()
    if not alteracoes:
        print(c("  ✔ Nenhuma alteração pendente.", "ok"))
        return []

    print(c(f"\n  {len(alteracoes)} alteração(ões):", "aviso"))
    for i, (status, f) in enumerate(alteracoes, 1):
        cor = "ok" if status in ("A", "??") else ("aviso" if status == "M" else "erro")
        print(f"    [{i:>2}] {c(status, cor):<10} {f}")

    diff = resumo_diff()
    if diff:
        print(c("\n  Resumo do diff:", "info"))
        for linha in diff.splitlines():
            print(f"    {linha}")
    return alteracoes

def passo_selecao(alteracoes):
    print(c("\n═══ 2. SELEÇÃO DE FICHEIROS ═══", "bold"))
    print("  Opções:")
    print("    a) Adicionar TODOS")
    print("    n) Adicionar nenhum (apenas inspecionar)")
    print("    1,2,3) Adicionar ficheiros por número (ex.: 1,3)")
    escolha = input(c("  Escolha [a/n/lista]: ", "info")).strip().lower()

    if escolha == "n":
        return []
    if escolha in ("a", ""):
        git("add", "-A")
        return [f for _, f in alteracoes]

    indices = []
    for parte in escolha.split(","):
        parte = parte.strip()
        if parte.isdigit():
            idx = int(parte) - 1
            if 0 <= idx < len(alteracoes):
                indices.append(idx)
    for idx in indices:
        git("add", alteracoes[idx][1])
    return [alteracoes[i][1] for i in indices]

def passo_commit(ficheiros_selecionados):
    print(c("\n═══ 3. MENSAGEM DE COMMIT ═══", "bold"))
    tipo_sug = sugerir_tipo([("", f) for f in ficheiros_selecionados])
    exemplo = f"{tipo_sug}: descreva a alteração em poucas palavras"

    print(f"  Tipos convencionais: feat, fix, docs, test, db, style, chore")
    print(f"  Sugestão: {c(exemplo, 'ok')}")
    msg = input(c("  Mensagem de commit: ", "info")).strip()

    if not msg:
        msg = input(c("  (vazio) Deseja usar a sugestão? [s/N]: ", "aviso")).strip().lower()
        if msg == "s":
            msg = exemplo
        else:
            print(c("  ✖ Commit cancelado.", "erro"))
            return None

    # Corpo opcional
    corpo = input(c("  Corpo (opcional, Enter para saltar): ", "info")).strip()
    if corpo:
        msg = f"{msg}\n\n{corpo}"

    out, err, code = git("commit", "-m", msg, check=False)
    if code != 0:
        print(c(f"  ✖ Falha no commit: {err}", "erro"))
        return None
    print(c(f"  ✔ Commit criado.", "ok"))
    for linha in out.splitlines()[:3]:
        print(f"    {linha}")
    return msg.splitlines()[0]

def passo_push():
    print(c("\n═══ 4. PUSH PARA O REMOTO ═══", "bold"))
    resp = input(c("  Fazer push? [s/N]: ", "info")).strip().lower()
    if resp != "s":
        print(c("  → Push ignorado.", "aviso"))
        return False

    out, err, code = git("push", check=False)
    if code != 0:
        # tentar --set-upstream
        branch = branch_atual()
        out, err, code = git("push", "-u", "origin", branch, check=False)
    if code != 0:
        print(c(f"  ✖ Push falhou: {err}", "erro"))
        return False
    print(c("  ✔ Push concluído.", "ok"))
    return True

def passo_tag(tipo):
    print(c("\n═══ 5. TAG DE VERSÃO ═══", "bold"))
    resp = input(c("  Criar tag? [s/N]: ", "info")).strip().lower()
    if resp != "s":
        print(c("  → Tag ignorada.", "aviso"))
        return None

    atual = ultima_tag()
    sugerida = proxima_versao(atual, tipo)
    tag = input(c(f"  Tag [{sugerida}]: ", "info")).strip() or sugerida
    anot = f"Release {tag} — {datetime.now():%Y-%m-%d}"

    out, err, code = git("tag", "-a", tag, "-m", anot, check=False)
    if code != 0:
        print(c(f"  ✖ Falha ao criar tag: {err}", "erro"))
        return None
    print(c(f"  ✔ Tag {tag} criada.", "ok"))

    resp = input(c("  Fazer push da tag? [s/N]: ", "info")).strip().lower()
    if resp == "s":
        git("push", "origin", tag, check=False)
        print(c("  ✔ Tag enviada para o remoto.", "ok"))
    return tag

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Ciclo de gestão de alterações Git")
    ap.add_argument("--auto", metavar="MSG", help="Commit automático com a mensagem indicada")
    ap.add_argument("--dry-run", action="store_true", help="Apenas mostrar estado, sem alterar")
    ap.add_argument("--no-push", action="store_true", help="Não fazer push")
    ap.add_argument("--no-tag", action="store_true", help="Não criar tag")
    args = ap.parse_args()

    if not e_repo_git():
        print(c("✖ Não está dentro de um repositório Git.", "erro"))
        sys.exit(1)

    print(c("\n╔══════════════════════════════════════════════╗", "bold"))
    print(c("║   CICLO DE GESTÃO DE ALTERAÇÕES — GIT        ║", "bold"))
    print(c("╚══════════════════════════════════════════════╝", "bold"))

    alteracoes = passo_estado()
    if not alteracoes:
        sys.exit(0)

    if args.dry_run:
        print(c("\n[dry-run] Nenhuma alteração efetuada.", "aviso"))
        sys.exit(0)

    # Modo automático
    if args.auto:
        git("add", "-A")
        out, err, code = git("commit", "-m", args.auto, check=False)
        if code != 0:
            print(c(f"✖ Falha no commit: {err}", "erro"))
            sys.exit(1)
        print(c(f"✔ Commit: {args.auto}", "ok"))
        tipo = args.auto.split(":")[0]
        if not args.no_push:
            git("push", check=False)
            print(c("✔ Push efetuado.", "ok"))
        if not args.no_tag:
            tag = proxima_versao(ultima_tag(), tipo)
            git("tag", "-a", tag, "-m", f"Release {tag}", check=False)
            git("push", "origin", tag, check=False)
            print(c(f"✔ Tag {tag} criada e enviada.", "ok"))
        sys.exit(0)

    # Modo interativo
    selecionados = passo_selecao(alteracoes)
    if not selecionados:
        print(c("\n→ Nada foi adicionado. A sair.", "aviso"))
        sys.exit(0)

    msg = passo_commit(selecionados)
    if not msg:
        sys.exit(1)

    tipo = msg.split(":")[0] if ":" in msg else "chore"

    if not args.no_push:
        passo_push()
    if not args.no_tag:
        passo_tag(tipo)

    print(c("\n✅ Ciclo concluído.", "ok"))
    print(f"   Branch: {branch_atual()} | Última tag: {ultima_tag()}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n\n⏹ Interrompido pelo utilizador.", "aviso"))
        sys.exit(130)
    except Exception as e:
        print(c(f"\n✖ Erro: {e}", "erro"))
        sys.exit(1)