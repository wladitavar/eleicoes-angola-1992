# ============================================================
# 1) Configuração — linhas confirmadas
# ============================================================
$path   = "scripts\generate_snapshot.py"
$inicio = 192
$fim    = 194

# ============================================================
# 2) Ler o ficheiro
# ============================================================
$linhas = Get-Content $path -Encoding utf8

# ============================================================
# 3) Mostrar o que será substituído (confirmação visual)
# ============================================================
Write-Host "`n--- Linhas a substituir ---" -ForegroundColor Yellow
for ($i = $inicio; $i -le $fim; $i++) {
    "  {0,4}: [{1}]" -f $i, $linhas[$i - 1]
}

# ============================================================
# 4) Novo bloco (12 linhas, indentação 4 espaços)
# ============================================================
$novoBloco = @(
    '    # ---------- Verificação de "raiz do projeto" ----------',
    '    # Aceita: package.json, server.js, index.html ou .git/',
    '    marcadores = [',
    '        Path("package.json"),',
    '        Path("server.js"),',
    '        Path("index.html"),',
    '        Path(".git"),',
    '    ]',
    '    if not any(p.exists() for p in marcadores):',
    '        print(cor("✖ Execute na raiz do projeto '
        + '(esperado package.json, server.js, index.html ou .git/).", "erro"))',
    '        sys.exit(1)'
)

# ============================================================
# 5) Reconstruir: antes + novo + depois
# ============================================================
$antes  = if ($inicio -gt 1) { $linhas[0..($inicio - 2)] } else { @() }
$depois = if ($fim -lt $linhas.Count) { $linhas[$fim..($linhas.Count - 1)] } else { @() }
$resultado = @($antes) + @($novoBloco) + @($depois)

# ============================================================
# 6) Gravar (UTF-8 sem BOM, LF)
# ============================================================
$texto = ($resultado -join "`n") + "`n"
[System.IO.File]::WriteAllText(
    (Resolve-Path $path).Path,
    $texto,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "`n✅ $path atualizado ($($novoBloco.Count) linhas novas)." -ForegroundColor Green