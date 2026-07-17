# Build e release do LUMA

## Executavel portatil

O executavel final para teste local fica em:

`dist\LUMA_ULTIMA\LUMA.exe`

Para recriar o pacote portatil:

```powershell
& 'C:\Users\adria\AppData\Local\Schrodinger\PyMOL3\python.exe' -m PyInstaller --noconfirm --distpath C:\Users\adria\AppData\Local\GeoDudeBuild\dist --workpath C:\Users\adria\AppData\Local\GeoDudeBuild\build luma.spec
```

Depois copie `C:\Users\adria\AppData\Local\GeoDudeBuild\dist\LUMA` para `dist\LUMA_ULTIMA`.

## Instalador Windows

Pre-requisito: Inno Setup 6 instalado.

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1
```

Saida esperada:

`packaging\windows\output\LUMA_Setup_1.2.0.exe`

## GitHub

Nao versionar `dist/`, `build/`, `.venv/`, logs, zips ou instaladores gerados. O repositorio deve conter o codigo fonte, `luma.spec`, `packaging/windows`, documentacao e testes.
