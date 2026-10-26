#!/usr/bin/env python3
"""
remove_bom.py — Remove BOM (Byte Order Mark) de todos os JSONs em public/data/.

Uso:
  python scripts/remove_bom.py
  python scripts/remove_bom.py --dry-run
  python scripts/remove_bom.py --dir public/data
"""

import argparse
import json
import sys
from pathlib import Path


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


def remover_bom_de_ficheiro(caminho: Path, dry_run: bool) -> bool:
    """
    Remove BOM de um ficheiro JSON, reescrevendo-o em UTF-8 sem BOM.
    Devolve True se alterou, False se não tinha BOM ou se falhou.
    """
    try:
        # Verificar se tem BOM (primeiros 3 bytes)
        bytes_iniciais = caminho.read_bytes()[:3]
        tem_bom = bytes_iniciais == b"\xef\xbb\xbf"

        if not tem_bom:
            return False

        if dry_run:
            print(cor(f"  [dry-run] removeria BOM de {caminho.name}", "info"))
            return True

        # Ler com utf-8-sig (remove BOM) e validar JSON
        conteudo = caminho.read_text(encoding="utf-8-sig")
        dados = json.loads(conteudo)

        # Reescrever sem BOM
        caminho.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(cor(f"  OK - BOM removido de {caminho.name}", "ok"))
        return True

    except json.JSONDecodeError as e:
        print(cor(f"  ERRO - JSON invalido em {caminho.name}: {e}", "erro"))
        return False
    except Exception as e:
        print(cor(f"  ERRO - {caminho.name}: {e}", "erro"))
        return False


def remover_bom_diretorio(diretorio: Path, dry_run: bool) -> tuple:
    """
    Remove BOM de todos os JSONs num diretorio.
    Devolve (total, corrigidos, com_bom_antes).
    """
    if not diretorio.exists():
        print(cor(f"ERRO - diretorio nao existe: {diretorio}", "erro"))
        return (0, 0, 0)

    ficheiros = sorted(diretorio.glob("*.json"))
    if not ficheiros:
        print(cor(f"AVISO - nenhum JSON em {diretorio}", "aviso"))
        return (0, 0, 0)

    total = len(ficheiros)
    corrigidos = 0
    com_bom_antes = 0

    print(cor(f"\nVerificando {total} ficheiro(s) JSON em {diretorio}:\n", "bold"))

    for f in ficheiros:
        tem_bom = f.read_bytes()[:3] == b"\xef\xbb\xbf"
        if tem_bom:
            com_bom_antes += 1
        if remover_bom_de_ficheiro(f, dry_run):
            corrigidos += 1
        else:
            if not tem_bom:
                print(cor(f"  -- {f.name} (sem BOM)", "info"))

    return (total, corrigidos, com_bom_antes)


def main():
    ap = argparse.ArgumentParser(
        description="Remove BOM de todos os JSONs em public/data/"
    )
    ap.add_argument(
        "--dir",
        default="public/data",
        help="Diretorio com os JSONs (default: public/data)"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="So mostra o que faria, sem alterar"
    )
    args = ap.parse_args()

    print(cor("\n+----------------------------------------------+", "bold"))
    print(cor("|   REMOVE BOM - JSONS EM public/data/        |", "bold"))
    print(cor("+----------------------------------------------+", "bold"))

    if args.dry_run:
        print(cor("  [dry-run] Nenhum ficheiro sera alterado.\n", "aviso"))

    diretorio = Path(args.dir).resolve()
    total, corrigidos, com_bom_antes = remover_bom_diretorio(diretorio, args.dry_run)

    print(cor("\n+----------------------------------------------+", "bold"))
    print(cor("|   RESUMO                                    |", "bold"))
    print(cor("+----------------------------------------------+", "bold"))
    print(f"  Total de JSONs      : {total}")
    print(f"  Com BOM (antes)     : {com_bom_antes}")
    print(f"  Corrigidos          : {corrigidos}")
    print(f"  Sem BOM (depois)    : {total - (com_bom_antes - corrigidos)}")

    if corrigidos > 0 and not args.dry_run:
        print(cor(f"\nOK - {corrigidos} ficheiro(s) corrigido(s).", "ok"))
    elif args.dry_run:
        print(cor(f"\n[dry-run] {corrigidos} ficheiro(s) seriam corrigidos.", "info"))
    else:
        print(cor("\nNenhum ficheiro precisou de ser corrigido.", "info"))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        print(cor("\n\nInterrompido.", "aviso"))
        sys.exit(130)
    except Exception as e:
        print(cor(f"\nERRO: {e}", "erro"))
        sys.exit(1)