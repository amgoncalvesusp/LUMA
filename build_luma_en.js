const { Document, Packer, Paragraph, TextRun, HeadingLevel } = require('docx');
const fs = require('fs');

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text, bold: true, size: 28 })],
  spacing: { before: 300, after: 120 },
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text, bold: true, size: 24 })],
  spacing: { before: 240, after: 100 },
});

const p = (text) => new Paragraph({
  children: [new TextRun({ text })],
  spacing: { after: 160 },
});

const bullet = (text) => new Paragraph({
  bullet: { level: 0 },
  children: [new TextRun({ text })],
  spacing: { after: 80 },
});

const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children: [
      h1('LUMA — Software Overview and Methodology'),

      h2('1. Executive Summary'),
      p('LUMA helps teams analyze land use and land cover without switching between multiple programs. The user loads points of interest, sets parameters, runs the analysis, and exports results — all in the same environment.'),
      p('The core problem the software solves is practical: comparing locations, time periods, or scenarios normally takes time, multiple tools, and technical knowledge that not everyone has. LUMA centralizes that workflow and produces maps, tables, and reports ready for meetings and audits.'),

      h2('2. Core Features and Capabilities'),
      bullet('Load points of interest and territorial data for visual analysis'),
      bullet('Display maps with legends, point labels, and comparison layers'),
      bullet('Run local analyses within user-defined radii'),
      bullet('Compare points or areas side by side with cartographic support'),
      bullet('Assess changes across time periods when multi-year data is available'),
      bullet('Calculate landscape indicators, including the ISA'),
      bullet('Export tables, reports, and files for external use'),

      h2('3. How It Works'),
      p('The user starts by entering the points they want to evaluate: project areas, properties, institutional units, or any location that needs spatial analysis. Then they set the analysis radius and type. That radius is what turns a vague question like "what surrounds this location?" into a concrete, repeatable spatial scope.'),
      p('With the parameters set, the software processes the territorial data and organizes results by point, class, period, or comparison. Maps display point names directly, which makes reading easier for users who do not work with GIS. When comparing locations or time periods, LUMA opens a dedicated visualization.'),
      p('At the end, everything can be exported. The files are useful for meetings, technical reports, accountability records, and historical tracking.'),

      h2('4. Methodology'),
      p('The analysis follows a fixed sequence: define the point, delimit the area, identify the land cover classes present, calculate the indicators, and compare the results. That order makes the process repeatable — the same criteria applied across different locations, regardless of who runs the analysis.'),
      p('The ISA works as a summary measure of landscape quality around each point. Instead of interpreting several data points separately, the user sees a single number that already consolidates the main information. This is most useful when comparing many points at once.'),
      p('The parameters used in each analysis are recorded, which makes it possible to review and justify decisions later. In contexts where results need to be explained to directors, public agencies, or communities, having that documented trail matters.'),

      h2('5. Use Cases'),
      p('Territorial planning: A team loads candidate investment sites, sets a standard radius, and compares results. Locations with higher sensitivity or land use pressure stand out immediately, helping prioritize without relying on gut feeling.'),
      p('Long-term monitoring: An organization tracks the same region across different years. LUMA structures the comparison by period and shows where there were gains, losses, or stability in land cover. The output feeds directly into progress reports or audits.'),
      p('Comparing units: A manager needs to evaluate multiple properties under the same criteria. The software applies the same parameters to each point and presents results with a comparison map. This reduces discussions driven by individual perception.'),

      h2('6. Key Benefits'),
      p('The most direct gain is time. Tasks that previously required several programs and specialized GIS knowledge now work within a single workflow. For teams without a technical background, that changes what is possible to do internally.'),
      p('When every point is evaluated with the same parameters, comparisons hold up. That makes results more credible when they need to be presented to partners or oversight bodies.'),
      p('Maps and tables make results accessible to managers who do not work with spatial data. Decision-makers can quickly see which points need attention and what evidence supports each recommendation.'),
      p('Analyses are documented. The organization builds a record of assessments that can be revisited in the future, compared against new data, or used as a reference in audits.'),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('LUMA_Overview_EN.docx', buf);
  console.log('Done: LUMA_Overview_EN.docx');
});
