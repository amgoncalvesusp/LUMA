# Build e release do LUMA

## Executavel portatil

O executavel final para teste local fica em:

`dist\LUMA_RELEASE\LUMA.exe`

Para recriar o pacote portatil:

```powershell
$buildRoot = 'C:\Users\adria\AppData\Local\GeoDudeBuild'
if (Test-Path $buildRoot) { Remove-Item $buildRoot -Recurse -Force }
& '.venv\Scripts\python.exe' -m PyInstaller --clean --noconfirm --distpath "$buildRoot\dist" --workpath "$buildRoot\build" luma.spec
```

Depois copie somente o resultado novo de `C:\Users\adria\AppData\Local\GeoDudeBuild\dist\LUMA` para `dist\LUMA_RELEASE`. A pasta final deve conter `LUMA.exe` e `_internal\PySide6\plugins\platforms\qwindows.dll`; não deve haver DLLs Qt ou uma pasta `plugins` ao lado de `LUMA.exe`.

## Instalador Windows

Pre-requisito: Inno Setup 6 instalado.

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1
```

Saida esperada:

`packaging\windows\output\LUMA_Setup_1.2.1.exe`

## GitHub

Nao versionar `dist/`, `build/`, `.venv/`, logs, zips ou instaladores gerados. O repositorio deve conter o codigo fonte, `luma.spec`, `packaging/windows`, documentacao e testes.
