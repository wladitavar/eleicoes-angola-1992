# ============================================================
# 1) Corrigir a validação do generate_snapshot.py
# ============================================================
$py = Get-Content scripts\generate_snapshot.py -Raw

$antigo = @'
if not (Path("package.json").exists() or Path("server.js").exists()):
    print(cor("✖ Execute na raiz do projeto.", "erro"))
    sys.exit(1)
'@

$novo = @'
# ---------- Verificação de "raiz do projeto" ----------
marcadores = [
    Path("package.json"),
    Path("server.js"),
    Path("index.html"),
    Path(".git"),
]
if not any(p.exists() for p in marcadores):
    print(cor("✖ Execute na raiz do projeto "
              "(esperado package.json, server.js, index.html ou .git/).", "erro"))
    sys.exit(1)
'@

if ($py.Contains($antigo)) {
    $py = $py.Replace($antigo, $novo)
    Set-Content -Path scripts\generate_snapshot.py -Value $py -Encoding utf8
    Write-Host "✅ generate_snapshot.py atualizado" -ForegroundColor Green
} else {
    Write-Host "⚠ Bloco original não encontrado. Verifique manualmente." -ForegroundColor Yellow
}

# ============================================================
# 2) Confirmar
# ============================================================
Select-String -Path scripts\generate_snapshot.py -Pattern "marcadores|index.html|Execute na raiz" -Context 0,1

# ============================================================
# 3) Correr o snapshot
# ============================================================
python scripts/generate_snapshot.py

# ============================================================
# 4) Ver resultado
# ============================================================
dir snapshots
Get-Content snapshots\angola92_*_*.md