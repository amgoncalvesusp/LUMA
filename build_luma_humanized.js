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
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children: [
      h1('LUMA — Software Overview and Methodology'),

      h2('1. Executive Summary'),
      p('O LUMA ajuda equipes a analisar uso e cobertura do solo sem precisar alternar entre vários programas. O usuário carrega pontos de interesse, define parâmetros, roda a análise e exporta os resultados, tudo dentro do mesmo ambiente.'),
      p('O problema central que o software resolve é prático: comparar locais, períodos ou cenários normalmente exige tempo, ferramentas diferentes e conhecimento técnico que nem todos têm. O LUMA centraliza esse fluxo e gera mapas, tabelas e relatórios prontos para reuniões e auditorias.'),

      h2('2. Core Features and Capabilities'),
      bullet('Carregar pontos de interesse e dados territoriais para análise visual'),
      bullet('Visualizar mapas com legenda, nomes de pontos e camadas de comparação'),
      bullet('Executar análises locais em raios definidos pelo usuário'),
      bullet('Comparar pontos ou áreas lado a lado, com suporte cartográfico'),
      bullet('Avaliar mudanças entre períodos quando há dados de mais de um ano'),
      bullet('Calcular indicadores de paisagem, incluindo o ISA'),
      bullet('Exportar tabelas, relatórios e arquivos para uso externo'),

      h2('3. How It Works'),
      p('O usuário começa informando os pontos que quer avaliar: áreas de projeto, propriedades, unidades institucionais ou qualquer local que precise de análise espacial. Depois define o raio de avaliação e o tipo de análise. Esse raio é o que transforma uma pergunta como "o que existe ao redor desse local?" em um recorte espacial concreto e repetível.'),
      p('Com os parâmetros definidos, o software processa os dados e organiza os resultados por ponto, classe, período ou comparação. Os mapas mostram os nomes dos pontos diretamente, o que facilita a leitura para quem não trabalha com SIG. Quando há comparação entre locais ou momentos, o LUMA abre uma visualização dedicada.'),
      p('No final, tudo pode ser exportado. Os arquivos servem para reuniões, relatórios técnicos, prestação de contas e acompanhamento histórico.'),

      h2('4. Methodology'),
      p('A análise segue uma sequência fixa: define-se o ponto, delimita-se a área, identificam-se as classes presentes, calculam-se os indicadores e comparam-se os resultados. Essa ordem torna o processo repetível — o mesmo critério aplicado em locais diferentes, independentemente de quem está fazendo a análise.'),
      p('O ISA funciona como uma medida resumida da qualidade da paisagem ao redor de cada ponto. Em vez de interpretar vários dados separados, o usuário vê um número que já consolida as informações principais. Útil principalmente quando há muitos pontos para comparar ao mesmo tempo.'),
      p('Os parâmetros usados em cada análise ficam registrados, o que permite revisar e justificar decisões depois. Em contextos onde os resultados precisam ser explicados para diretores, órgãos públicos ou comunidades, esse rastro documentado tem peso.'),

      h2('5. Use Cases'),
      p('Planejamento territorial: Uma equipe carrega pontos candidatos a investimento, define um raio padrão e compara os resultados. Os locais com maior sensibilidade ou pressão de uso ficam visíveis logo, ajudando a priorizar sem depender só de percepção.'),
      p('Monitoramento ao longo do tempo: Uma organização acompanha a mesma região em diferentes anos. O LUMA estrutura a comparação por período e mostra onde houve ganho, perda ou estabilidade na cobertura. O resultado alimenta relatórios de acompanhamento ou auditorias.'),
      p('Comparação entre unidades: Um gestor precisa avaliar várias propriedades com o mesmo critério. O software aplica os mesmos parâmetros para cada ponto e apresenta os resultados com mapa de comparação. Isso reduz discussões baseadas em percepção individual.'),

      h2('6. Key Benefits'),
      p('O ganho mais direto é tempo. Tarefas que antes exigiam vários programas e conhecimento especializado em geoprocessamento passam a funcionar em um fluxo único. Para equipes sem perfil técnico, isso muda o que é possível fazer internamente.'),
      p('Quando todos os pontos são avaliados com os mesmos parâmetros, as comparações fazem sentido. Isso dá mais credibilidade aos resultados quando precisam ser apresentados a parceiros ou órgãos de controle.'),
      p('Os mapas e tabelas tornam os resultados acessíveis para gestores que não trabalham com dados espaciais. Quem toma decisões consegue ver rapidamente quais pontos exigem atenção e qual evidência sustenta cada recomendação.'),
      p('As análises ficam documentadas. A organização acumula um histórico de avaliações que pode ser consultado no futuro, comparado com novos dados ou usado como referência em auditorias.'),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('LUMA_Overview_humanized.docx', buf);
  console.log('Done: LUMA_Overview_humanized.docx');
});
