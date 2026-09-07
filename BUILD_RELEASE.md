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

## Validacao da correcao CONTAG (2026-09-07, ainda sem release)

- Base: tag `v1.2.1`, commit `8ce58e0`. Nenhum instalador novo foi gerado.
- TDD: nove regressões falharam antes da correção; testes cobrem cálculo manual
  FRAGSTATS, rotação, reflexão, classes numéricas arbitrárias, máscara de fundo,
  valores indefinidos e apresentação GUI/PDF.
- Windows/Python 3.13: 57 testes aprovados no ambiente original e em ambiente
  isolado atualizado. Cobertura com branches: 47% global e 81% em `core/stats.py`.
  A cobertura global permanece abaixo de 80%; este patch não constitui auditoria
  completa da interface.
- Ambiente isolado: Pillow 12.3.0, click 8.5.0, idna 3.19, urllib3 2.7.0,
  pip 26.2.1 e setuptools 84.0.0; `pip-audit` sem vulnerabilidades conhecidas e
  dependências compatíveis. O mínimo declarado do Pillow passou a 12.3.0.
- O ambiente original foi preservado e ainda precisa das atualizações de
  dependências identificadas na auditoria antes de um próximo empacotamento.
