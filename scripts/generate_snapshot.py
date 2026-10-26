#!/usr/bin/env python3
"""
generate_snapshot.py — Gera um snapshot completo do codigo da ultima versao.

Produz:
  - snapshots/angola92_<versao>_<timestamp>.zip
  - snapshots/angola92_<versao>_<timestamp>.md
  - snapshots/angola92_<versao>_<timestamp>.json
  - snapshots/angola92_<versao>_<timestamp>.sha256

Exclui por omissao: .git, node_modules, coverage, *.db, __pycache__, .venv,
dist/, snapshots/, .backup/

Uso:
  python scripts/generate_snapshot.py
  python scripts/generate_snapshot.py --tag v1.0.0 --output ./dist
  python scripts/generate_snapshot.py --include-db
"""

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ======================================================================
# Exclusoes por omissao
# ======================================================================
EXCLUSAO_PADRAO = {
    ".git", "node_modules", "coverage", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", ".DS_Store", ".pytest_cache", ".mypy_cache",
    "dist", "snapshots", ".backup",
}
EXCLUSAO_EXT = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo"}


# ======================================================================
# Cores (ASCII-friendly, nunca quebra)
# ======================================================================
def cor(txt, tipo="info"):
    m = {
        "ok": "\033[92m",
        "aviso": "\033[93m",
        "erro": "\033[91m",
        "info": "\033[96m",
        "bold": "\033[1m",
        "fim": "\033[0m",
    }
    return f"{m.get(tipo, '')}{txt}{m['fim']}"


# ======================================================================
# Helpers Git
# ======================================================================
def run(cmd, check=True):
    p = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        capture_output=True, text=True, check=False
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"Comando falhou: {cmd}\n{p.stderr}")
    return p.stdout.strip()


def versao_atual():
    """Tenta obter a ultima tag Git; fallback: versao do package.json."""
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


# ======================================================================
# Filtro de ficheiros
# ======================================================================
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


# ======================================================================
# Snapshot
# ======================================================================
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
    json_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Manifesto Markdown
    linhas = [
        "# Snapshot - Eleicoes Angola 1992",
        "",
        f"- **Versao:** `{tag}`",
        f"- **Commit:** `{meta['commit']}`",
        f"- **Branch:** `{meta['branch']}`",
        f"- **Gerado em:** {timestamp}",
        f"- **Ficheiros:** {meta['total_ficheiros']}",
        f"- **Tamanho total:** {meta['total_bytes']:,} bytes".replace(",", "."),
        f"- **SHA-256 do ZIP:** `{meta['zip_sha256']}`",
        "",
        "## Ficheiros incluidos",
        "",
        "| # | Caminho | Bytes | SHA-256 (12 primeiros) |",
        "|---|---------|------:|------------------------|",
    ]
    for i, f in enumerate(ficheiros, 1):
        linhas.append(
            f"| {i} | `{f['caminho']}` | {f['bytes']} | `{f['sha256'][:12]}` |"
        )
    md_path.write_text("\n".join(linhas), encoding="utf-8")

    # Checksum do ZIP
    sha_path.write_text(
        f"{meta['zip_sha256']}  {zip_path.name}\n",
        encoding="utf-8"
    )

    return {
        "zip": zip_path,
        "md": md_path,
        "json": json_path,
        "sha256": sha_path,
        "meta": meta,
    }


# ======================================================================
# Main
# ======================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Gera snapshot do codigo da ultima versao"
    )
    ap.add_argument("--tag", help="Tag/versao a usar no nome (default: ultima tag Git)")
    ap.add_argument("--output", default="snapshots", help="Diretorio de saida")
    ap.add_argument("--include-db", action="store_true", help="Incluir *.db / *.sqlite")
    args = ap.parse_args()

    # Verificacao de raiz do projeto (aceita frontend estatico ou API Node)
    marcadores = [
        Path("package.json"),
        Path("server.js"),
        Path("public/index.html"),
        Path("public/app.js"),
        Path(".git"),
    ]
    if not any(p.exists() for p in marcadores):
        print(cor("ERRO: execute na raiz do projeto.", "erro"))
        sys.exit(1)

    tag = args.tag or versao_atual()
    output = Path(args.output).resolve()

    print(cor("\n+----------------------------------------------+", "bold"))
    print(cor("|   SNAPSHOT DO CODIGO - ULTIMA VERSAO        |", "bold"))
    print(cor("+----------------------------------------------+", "bold"))
    print(f"  Versao : {cor(tag, 'ok')}")
    print(f"  Commit : {commit_atual()}")
    print(f"  Branch : {branch_atual()}")
    print(f"  Output : {output}")

    try:
        r = gerar_snapshot(tag, output, args.include_db)
    except Exception as e:
        print(cor(f"\nERRO: {e}", "erro"))
        sys.exit(1)

    m = r["meta"]
    print(cor("\nOK - Snapshot gerado.", "ok"))
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
        print(cor("\n\nInterrompido.", "aviso"))
        sys.exit(130)