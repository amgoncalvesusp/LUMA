param(
    [string]$InnoSetupCompiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$distDir = Join-Path $repoRoot "dist\LUMA_ULTIMA"
$exePath = Join-Path $distDir "LUMA.exe"
$issPath = Join-Path $scriptDir "LUMA.iss"

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Build final nao encontrado: $exePath"
}

if (-not (Test-Path -LiteralPath $InnoSetupCompiler)) {
    throw "Inno Setup nao encontrado em '$InnoSetupCompiler'. Instale o Inno Setup 6 ou passe -InnoSetupCompiler."
}

& $InnoSetupCompiler $issPath
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao gerar instalador. ISCC exit code: $LASTEXITCODE"
}

Write-Host "Instalador gerado em: $(Join-Path $scriptDir 'output')"
