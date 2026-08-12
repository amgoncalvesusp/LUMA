# LUMA — Land Use & Land Cover Analyzer

> Uma forma mais simples de transformar dados de uso e cobertura da terra em evidências para decisões territoriais.

## Português

### O que é o LUMA?

O LUMA é um aplicativo desktop para análise espacial de uso e cobertura da terra. Ele foi pensado para quem precisa comparar locais, acompanhar mudanças ao longo do tempo e explicar resultados com clareza — sem ter de montar um fluxo diferente em cada programa de geoprocessamento.

A partir de coordenadas, raios de análise ou áreas de interesse, o LUMA recorta os dados raster, identifica as classes presentes, calcula métricas de paisagem e organiza os resultados em mapas, tabelas, gráficos e relatórios.

### O que você pode fazer

- Analisar um ponto usando um buffer definido em metros ou uma área de interesse (AOI).
- Desenhar uma AOI no mapa ou importar GeoJSON, KML/KMZ e Shapefile poligonal.
- Comparar vários pontos ou AOIs usando os mesmos critérios de análise.
- Avaliar transições entre dois anos e acompanhar séries temporais.
- Calcular métricas como ISA, SHDI, SIDI, LPI e número de fragmentos.
- Usar dados do MapBiomas Brasil — Coleção 10.1 e Coleção 3 beta — com validação de anos e acesso remoto a rasters COG.
- Visualizar mapas com legendas, buffers, pontos nomeados e sobreposições comparativas.
- Exportar resultados para PDF, JSON e Excel.
- Exportar pontos e buffers para KML, KMZ e Shapefile WGS84, prontos para QGIS e Google Earth.
- Salvar o mapa em TIFF e escolher qual gráfico exportar em PNG, SVG ou PDF.
- Guardar os parâmetros de uma análise em arquivos `.luma.json`, facilitando a reprodução e a auditoria.

### Como o fluxo funciona

1. Escolha os pontos ou importe uma área de interesse.
2. Defina o raio, os dados e os anos que deseja analisar.
3. Execute a análise espacial, temporal ou comparativa.
4. Leia os resultados no mapa, nas tabelas e nos gráficos.
5. Exporte somente o que precisa para o relatório, o QGIS, o Google Earth ou a próxima etapa do projeto.

O objetivo é manter o processo rastreável: a mesma configuração aplicada a locais diferentes produz comparações mais consistentes e fáceis de explicar para equipes técnicas, gestores, parceiros e comunidades.

### Para quem o LUMA é útil

O LUMA pode apoiar planejamento territorial, monitoramento ambiental, acompanhamento de propriedades e projetos, estudos acadêmicos, relatórios técnicos e avaliações que precisam relacionar um local específico com o contexto da paisagem ao seu redor.

### Executar a partir do código-fonte

O projeto requer Python 3.10 ou superior. Com o ambiente virtual preparado:

```powershell
.venv\Scripts\Activate.ps1
python -m luma.main
```

Para executar os testes da aplicação:

```powershell
python -m pytest -q tests
```

O aplicativo inicia em português do Brasil e permite alternar para inglês pelo menu de configurações.

## English

### What is LUMA?

LUMA is a desktop application for spatial land-use and land-cover analysis. It is designed for people who need to compare places, track change over time, and communicate findings clearly without having to assemble a different GIS workflow for every question.

Given coordinates, analysis radii, or areas of interest, LUMA clips raster data, identifies the classes that occur around each location, calculates landscape metrics, and brings the results together as maps, tables, charts, and reports.

### What you can do

- Analyze a location with a radius in meters or an area of interest (AOI).
- Draw an AOI on the map or import GeoJSON, KML/KMZ, and polygon Shapefiles.
- Compare multiple points or AOIs using the same analysis criteria.
- Measure transitions between two years and inspect multi-year time series.
- Calculate metrics such as ISA, SHDI, SIDI, LPI, and patch counts.
- Work with MapBiomas Brazil data — Collection 10.1 and Collection 3 beta — with year validation and remote COG access.
- View maps with legends, buffers, named points, and comparison overlays.
- Export results to PDF, JSON, and Excel.
- Export points and buffers as WGS84 KML, KMZ, and Shapefile layers ready for QGIS and Google Earth.
- Save the displayed map as TIFF and choose individual charts to export as PNG, SVG, or PDF.
- Store analysis parameters in `.luma.json` project files for reproducible and auditable work.

### How the workflow works

1. Choose your points or import an area of interest.
2. Set the radius, data source, and years to analyze.
3. Run a spatial, temporal, or comparison analysis.
4. Explore the results in the map, tables, and charts.
5. Export exactly what you need for a report, QGIS, Google Earth, or the next stage of your project.

The workflow is intentionally traceable: applying the same configuration to different locations makes comparisons more consistent and easier to explain to technical teams, decision-makers, partners, and communities.

### Who LUMA is for

LUMA can support territorial planning, environmental monitoring, property and project follow-up, academic research, technical reporting, and any assessment that needs to connect a specific location with the landscape around it.

### Run from source

The project requires Python 3.10 or newer. With the virtual environment ready:

```powershell
.venv\Scripts\Activate.ps1
python -m luma.main
```

To run the application tests:

```powershell
python -m pytest -q tests
```

The application starts in Brazilian Portuguese and can be switched to English from the settings menu.

## Authors

- Adriano Marques Gonçalves (UNIARA)
- Guilherme Rossi Gorni (UNIARA)

## License

Apache License 2.0
