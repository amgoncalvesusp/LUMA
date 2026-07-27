param(
    [string]$InnoSetupCompiler = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$distDir = Join-Path $repoRoot "dist\LUMA_RELEASE"
$exePath = Join-Path $distDir "LUMA.exe"
$issPath = Join-Path $scriptDir "LUMA.iss"
$platformPlugin = Join-Path $distDir "_internal\PySide6\plugins\platforms\qwindows.dll"

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Build final nao encontrado: $exePath"
}

if (-not (Test-Path -LiteralPath $platformPlugin)) {
    throw "Plugin Qt qwindows.dll nao encontrado no layout esperado: $platformPlugin. Gere o pacote em diretorio limpo antes de criar o instalador."
}

# Qt must have one authoritative runtime under PyInstaller's _internal tree.
# Leftover DLLs beside LUMA.exe can win Windows' DLL search order and make the
# bundled platform plugin fail to initialize on a clean machine.
$rootQtFiles = Get-ChildItem -LiteralPath $distDir -File | Where-Object {
    $_.Name -match '^(Qt6|pyside6|shiboken6|MSVCP|VCRUNTIME|libEGL|libGLES)'
}
if ($rootQtFiles) {
    $names = ($rootQtFiles.Name -join ', ')
    throw "Runtime Qt duplicado ao lado de LUMA.exe: $names. Limpe dist\\LUMA_RELEASE e copie uma compilacao nova."
}

if ([string]::IsNullOrWhiteSpace($InnoSetupCompiler)) {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $InnoSetupCompiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not $InnoSetupCompiler -or -not (Test-Path -LiteralPath $InnoSetupCompiler)) {
    throw "Inno Setup nao encontrado. Instale o Inno Setup 6 ou passe -InnoSetupCompiler."
}

& $InnoSetupCompiler $issPath
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao gerar instalador. ISCC exit code: $LASTEXITCODE"
}

Write-Host "Instalador gerado em: $(Join-Path $scriptDir 'output')"
