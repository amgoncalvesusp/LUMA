# LUMA

**LUMA** (Land Use & Land Cover Analyzer) é um software para análise de uso e cobertura do solo a partir de rasters geoespaciais. Ele permite calcular a distribuição de classes de cobertura, métricas de paisagem, comparação entre pontos e análise temporal usando arquivos GeoTIFF ou fontes remotas compatíveis.

Repositório público: <https://github.com/amgoncalvesusp/LUMA>

Release atual: <https://github.com/amgoncalvesusp/LUMA/releases/tag/v1.0.0>

## Principais recursos

- Análise de uso e cobertura do solo por coordenada central e raio de buffer.
- Leitura de rasters GeoTIFF locais (`.tif` / `.tiff`).
- Uso de fontes remotas compatíveis, incluindo ESA WorldCover.
- Suporte a legendas para MapBiomas, ESA WorldCover, Copernicus Global Land Cover, MODIS e Dynamic World.
- Cálculo de área por classe, porcentagem, pixels válidos e área total.
- Métricas de paisagem, incluindo diversidade de Shannon, diversidade de Simpson, fragmentos, densidade de fragmentos, índice do maior fragmento, agregação, contágio, forma média e índice de área impermeável.
- Análise temporal entre dois anos ou série temporal com múltiplos arquivos.
- Comparação de múltiplos pontos por entrada manual, colagem de tabela, CSV ou Excel.
- Exportação de resultados em CSV, Excel, JSON, PDF e TIFF para mapas comparativos.

## Como baixar

### Opção recomendada: GitHub Release

1. Acesse a página da release:
   <https://github.com/amgoncalvesusp/LUMA/releases/tag/v1.0.0>
2. Baixe o arquivo `LUMA_ULTIMA.rar` em **Assets**.
3. Extraia o pacote em uma pasta local.
4. Execute `LUMA.exe`.

### Opção para clonar o repositório

Este repositório usa **Git LFS** para armazenar arquivos binários grandes, como DLLs e executáveis. Para clonar corretamente:

```powershell
git lfs install
git clone https://github.com/amgoncalvesusp/LUMA.git
cd LUMA
git lfs pull
```

Depois execute:

```powershell
.\LUMA.exe
```

Evite usar apenas o botão **Code > Download ZIP** do GitHub quando precisar da distribuição executável completa, porque arquivos versionados via Git LFS podem ser baixados como ponteiros em vez dos binários reais.

## Requisitos

- Windows 10 ou superior.
- Espaço em disco suficiente para a distribuição completa.
- Conexão com a internet para datasets remotos ou para baixar dados externos.
- Para clonagem via Git: Git e Git LFS instalados.

O pacote já inclui o executável e as bibliotecas necessárias para execução local. Não é necessário instalar Python para usar a versão distribuída.

## Como usar

1. Abra `LUMA.exe`.
2. Informe a latitude e longitude em graus decimais.
   - Exemplo: São Paulo pode ser representado como latitude `-23.55` e longitude `-46.63`.
3. Defina o raio do buffer em metros.
4. Escolha a fonte de dados:
   - **Arquivo Local** para selecionar um raster GeoTIFF já baixado.
   - **Dataset Remoto** para usar uma fonte remota compatível.
5. Escolha a legenda adequada ou use a detecção automática quando o nome do arquivo permitir.
6. Clique em **Analisar**.
7. Consulte os resultados nas abas da interface.
8. Use o menu **Arquivo** para exportar os resultados.

## Entrada de dados

### Arquivos locais

Use arquivos raster GeoTIFF (`.tif` ou `.tiff`) contendo classes de uso e cobertura do solo. O raster deve cobrir a área analisada e estar em um sistema de coordenadas reconhecido.

Fontes suportadas pela legenda do LUMA incluem:

- MapBiomas Brasil, Coleções 9 e 10.
- MapBiomas Amazônia, Mata Atlântica e Chaco.
- ESA WorldCover 2020 e 2021.
- Copernicus Global Land Cover.
- MODIS Land Cover MCD12Q1.
- Google Dynamic World.
- Global Forest Watch / Hansen.

### Datasets remotos

Quando uma fonte remota estiver disponível, o LUMA baixa somente a área necessária para o buffer informado. Esse modo requer conexão com a internet.

## Análises disponíveis

### Análise simples

Calcula a distribuição das classes dentro do buffer:

- área em km² e hectares;
- porcentagem por classe;
- número de pixels;
- métricas de paisagem;
- avisos de qualidade quando a resolução ou a cobertura dos dados forem insuficientes.

### Análise temporal

Permite comparar rasters de anos diferentes:

- matriz de transição entre classes;
- persistência;
- mudança líquida por classe;
- taxa anual de desmatamento FAO;
- série temporal com múltiplos anos.

### Comparação multi-ponto

Permite comparar vários locais na mesma análise:

- entrada manual de pontos;
- colagem de tabela;
- importação de CSV ou Excel;
- mapeamento de colunas de nome, latitude, longitude e raio;
- exportação de mapa comparativo em TIFF.

## Exportação

O LUMA permite exportar os resultados em:

- CSV;
- Excel (`.xlsx`);
- JSON;
- PDF;
- TIFF para mapas comparativos.

Os arquivos exportados são úteis para relatórios técnicos, documentação de análises, comparação entre áreas e arquivamento dos resultados.

## Distribuição no GitHub

O projeto é distribuído publicamente pelo GitHub no repositório:

<https://github.com/amgoncalvesusp/LUMA>

A versão `v1.0.0` foi publicada como release em:

<https://github.com/amgoncalvesusp/LUMA/releases/tag/v1.0.0>

Como a distribuição contém bibliotecas grandes do pacote Windows, o repositório usa Git LFS. Isso permite versionar arquivos maiores do que o limite normal de blobs do GitHub.

Para usuários finais, a recomendação é baixar a versão publicada em **Releases**. Para desenvolvedores ou usuários que precisam clonar o repositório, é necessário usar Git LFS.

## Autores

- Adriano Marques Gonçalves (UNIARA)
- Guilherme Rossi Gorni (UNIARA)

## Licença

Apache License 2.0
