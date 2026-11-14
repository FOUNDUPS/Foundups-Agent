'use client';

import { useEffect } from 'react';

type Language = 'ja' | 'en' | 'pt';
type CopyTriple = Record<Language, string>;

const triples: CopyTriple[] = [
  { ja: 'イノベーション・スペース', en: 'Innovation Space', pt: 'Espaço de Inovação' },
  { ja: 'しくみ · eSingularity イノベーション・スペース', en: 'HOW · eSINGULARITY INNOVATION SPACE', pt: 'COMO · ESPAÇO DE INOVAÇÃO eSINGULARITY' },
  { ja: '下層階 · 温泉・地域スペース', en: 'LOWER LEVELS · PUBLIC SPACE', pt: 'ANDARES INFERIORES · ESPAÇO PÚBLICO' },
  { ja: '3階 · 挑戦・育成スペース', en: 'THIRD FLOOR · EMERGING PROJECTS', pt: '3º ANDAR · PROJETOS EM DESENVOLVIMENTO' },
  { ja: '最上階 · 実証・発展スペース', en: 'TOP FLOOR · VALIDATED PROJECTS', pt: 'ÚLTIMO ANDAR · PROJETOS VALIDADOS' },
  { ja: '別棟 · COG DC', en: 'SEPARATE · COG DC', pt: 'EDIFÍCIO SEPARADO · COG DC' },
  { ja: '学生・チームと初期FoundUpプロジェクト', en: 'Students, teams + early FoundUp projects', pt: 'Estudantes, equipes + projetos FoundUp iniciais' },
  { ja: '実証を通過したFoundUpプロジェクト', en: 'Validated FoundUp projects', pt: 'Projetos FoundUp validados' },
  { ja: '選抜された学生と小さなチームが、旧客室をプロジェクトスタジオとして使い、地域の実課題を解くFoundUpプロジェクトを育てる。', en: 'Selected students and small teams use former guest rooms as project studios to develop FoundUp projects that solve real local problems.', pt: 'Estudantes selecionados e pequenas equipes usam os antigos quartos como estúdios para desenvolver projetos FoundUp que resolvem problemas locais reais.' },
  { ja: '実用性と実行力を示したFoundUpプロジェクトが上階へ進み、より大きな実証スペースを使う。収益化は目的ではなく、課題を解いた結果として必要な場合に行う。', en: 'FoundUp projects that prove usefulness and execution move upward into larger validation space. Monetization is not the goal; it is used when needed as a result of solving the problem.', pt: 'Projetos FoundUp que comprovam utilidade e execução avançam para espaços maiores de validação. Monetização não é o objetivo; é usada quando necessária como resultado da solução do problema.' },
  { ja: '福井 × COG DC コンピュート', en: 'FUKUI × COG DC COMPUTE', pt: 'FUKUI × COMPUTAÇÃO COG DC' },
  { ja: '私たちのコンピュートが、', en: 'Our compute', pt: 'Nossa computação' },
  { ja: '未来を動かすのは、私たちのCOG DCコンピュート。', en: 'Our COG DC compute helps power the future.', pt: 'Nossa computação COG DC ajuda a mover o futuro.' },
  { ja: '見る · 知る · 共有する · 動く', en: 'VISIT · SHARE · LEARN · ACT', pt: 'VER · COMPARTILHAR · APRENDER · AGIR' },
  { ja: '今、行動する · 九頭竜を守る', en: 'ACT NOW · SAVE KUZURYU', pt: 'AJA AGORA · SALVE KUZURYU' },
  { ja: 'なぜ残すのか · 建物の価値', en: 'WHY · THE BUILDING', pt: 'POR QUÊ · O EDIFÍCIO' },
  { ja: '市民が使ってきた公共資産', en: 'A PUBLIC ASSET WITH A HISTORY', pt: 'UM PATRIMÔNIO PÚBLICO COM HISTÓRIA' },
  { ja: '来訪者経済 · 試算シナリオ', en: 'VISITOR ECONOMY · SCREENING SCENARIO', pt: 'ECONOMIA DE VISITANTES · CENÁRIO DE TRIAGEM' },
  { ja: '現在 · 算定済み', en: 'NOW · CALCULATED', pt: 'AGORA · CALCULADO' },
  { ja: '次段階 · 産業連関分析', en: 'NEXT · INPUT-OUTPUT', pt: 'PRÓXIMO · INSUMO-PRODUTO' },
  { ja: '検証後', en: 'AFTER VALIDATION', pt: 'APÓS VALIDAÇÃO' },
  { ja: '事業シナリオ — 予測ではありません', en: 'PROJECT SCENARIO — NOT A FORECAST', pt: 'CENÁRIO DO PROJETO — NÃO É PREVISÃO' },
  { ja: '議会に求める判断', en: 'THE COUNCIL DECISION', pt: 'A DECISÃO DO CONSELHO' },
  { ja: '比較評価の条件', en: 'THE COMPARISON RULE', pt: 'A REGRA DE COMPARAÇÃO' },
  { ja: 'しくみ · AIの田んぼ', en: 'HOW · AI RICE FIELD', pt: 'COMO · ARROZAL DE IA' },
  { ja: '誰がつくるか · 地域', en: 'WHO · COMMUNITY', pt: 'QUEM · COMUNIDADE' },
  { ja: '上から決めるプロジェクトではない', en: 'NOT A TOP-DOWN PROJECT', pt: 'NÃO É UM PROJETO DE CIMA PARA BAIXO' },
  { ja: 'いつ · 地域で話す', en: 'WHEN · COMMUNITY MEETINGS', pt: 'QUANDO · REUNIÕES COMUNITÁRIAS' },
  { ja: '参加 · 温泉を守る', en: 'JOIN · SAVE THE ONSEN', pt: 'PARTICIPE · SALVE O ONSEN' },
  { ja: '対象施設', en: 'PROJECT SITE', pt: 'LOCAL DO PROJETO' },
  { ja: 'AI × 温泉 × 教育 × 農業 × 地域', en: 'AI × ONSEN × EDUCATION × AGRICULTURE × COMMUNITY', pt: 'IA × ONSEN × EDUCAÇÃO × AGRICULTURA × COMUNIDADE' },
  { ja: 'JHR · レポートを読む ↗', en: 'JHR · READ REPORT ↗', pt: 'JHR · LER RELATÓRIO ↗' },

  // Japanese tab should read like a Japanese public site, not an English design with Japanese paragraphs.
  { ja: 'なぜ · 温泉を守る', en: 'WHY · SAVE THE ONSEN', pt: 'POR QUÊ · SALVAR O ONSEN' },
  { ja: '未来像 · ここがどう変わる？', en: 'WHAT · HOW WILL THIS PLACE CHANGE?', pt: 'VISÃO · COMO ESTE LUGAR VAI MUDAR?' },
  { ja: '敷地構想', en: 'SITE CONCEPT', pt: 'CONCEITO DO LOCAL' },
  { ja: '温泉構想', en: 'ONSEN CONCEPT', pt: 'CONCEITO DO ONSEN' },
  { ja: '01 · 露天風呂', en: '01 · ROTENBURO', pt: '01 · ROTENBURO' },
  { ja: '技術検証が必要', en: 'ENGINEERING VALIDATION REQUIRED', pt: 'VALIDAÇÃO TÉCNICA NECESSÁRIA' },
  { ja: '02 · 食', en: '02 · FOOD', pt: '02 · COMIDA' },
  { ja: 'あわら型 · 地域の食の横丁', en: 'AWARA-INSPIRED COMMUNITY FOOD COURT', pt: 'VILA GASTRONÔMICA COMUNITÁRIA INSPIRADA EM AWARA' },
  { ja: '03 · 夜', en: '03 · NIGHT', pt: '03 · NOITE' },
  { ja: 'D-K / デジタル掛軸 提案構想', en: 'PROPOSED DIGITAL KAKEJIKU EXPERIENCE', pt: 'EXPERIÊNCIA DIGITAL KAKEJIKU PROPOSTA' },
  { ja: '写真', en: 'VISIT', pt: 'VISITAR' },
  { ja: '聴く', en: 'LISTEN', pt: 'OUVIR' },
  { ja: '計画', en: 'PLAN', pt: 'PLANO' },
  { ja: '詳しく', en: 'EXPLORE', pt: 'EXPLORAR' },
  { ja: '参加', en: 'JOIN', pt: 'PARTICIPAR' },
  { ja: '行動', en: 'ACTION', pt: 'AÇÃO' },
  { ja: '反対票', en: 'VOTE NO', pt: 'VOTE NÃO' },
  { ja: '10枚のビジョン', en: 'PRESENTATION', pt: 'APRESENTAÇÃO' },
  { ja: '僧の現在地', en: 'MONK', pt: 'MONGE' },
  { ja: '新着', en: 'NEW', pt: 'NOVO' },
  { ja: '温泉を守る', en: 'SAVE OUR ONSEN', pt: 'SALVE NOSSO ONSEN' },
  { ja: '九頭竜を守る', en: 'SAVE THE DRAGON', pt: 'SALVE KUZURYU' },
  { ja: '停止', en: 'STOP', pt: 'PARAR' },
  { ja: 'チーム形成', en: 'ASSEMBLE', pt: 'FORMAR EQUIPE' },
  { ja: '土地', en: 'LAND', pt: 'TERRENO' },
  { ja: '市', en: 'CITY', pt: 'CIDADE' },
  { ja: '大学', en: 'UNIVERSITIES', pt: 'UNIVERSIDADES' },
  { ja: '顧客・協力者', en: 'CUSTOMERS + PARTNERS', pt: 'CLIENTES + PARCEIROS' },
  { ja: '温泉・地域・教育', en: 'ONSEN · COMMUNITY · EDUCATION', pt: 'ONSEN · COMUNIDADE · EDUCAÇÃO' },
  { ja: '私たちのCOG DCコンピュートを、そこで働く学生、FoundUpプロジェクト、研究・地域プロジェクトが使い、農業AI、教育、研究、ものづくりの開発と検証を支えます。', en: 'Students, FoundUp projects, research and community projects working there can use our COG DC compute to support development and validation in agricultural AI, education, research and manufacturing.', pt: 'Estudantes, projetos FoundUp, pesquisa e projetos comunitários que trabalham ali podem usar nossa computação COG DC para apoiar desenvolvimento e validação em IA agrícola, educação, pesquisa e manufatura.' },
];

const aliases: Record<string, CopyTriple> = {};
for (const triple of triples) {
  aliases[triple.ja] = triple;
  aliases[triple.en] = triple;
  aliases[triple.pt] = triple;
}

const sourceAliases: Record<string, CopyTriple> = {
  'AI拠点': triples[0],
  'HOW · ESINGULARITY INNOVATION HUB': triples[1],
  'LOWER LEVELS · PUBLIC': triples[2],
  'THIRD FLOOR · EMERGING': triples[3],
  'TOP FLOOR · ADVANCED': triples[4],
  'SEPARATE INFRASTRUCTURE': triples[5],
  '学生と初期FoundUps': triples[6],
  '検証されたFoundUps': triples[7],
  '選抜された学生と若いチームが、旧客室を小さなプロジェクトスタジオとして使い、実課題を解く。': triples[8],
  '実用性、実行力、現実の価値を示したプロジェクトが上階へ進み、独立したAIネイティブ事業を目指す。': triples[9],
  'FUKUI × COG DC COMPUTE': triples[10],
  '私たちのComputeが、': triples[11],
  '未来を動かすのは、私たちのCOG DC Compute。': triples[12],
  'VISIT · SHARE · LEARN · ACT': triples[13],
  'ACT NOW · SAVE THE DRAGON': triples[14],
  'WHY / THE BUILDING': triples[15],
  'A PUBLIC ASSET WITH A HISTORY': triples[16],
  'VISITOR ECONOMY · SCREENING SCENARIO': triples[17],
  'NOW · CALCULATED': triples[18],
  'NEXT · INPUT-OUTPUT': triples[19],
  'AFTER VALIDATION': triples[20],
  'PROJECT SCENARIO — NOT A FORECAST': triples[21],
  'THE COUNCIL AMENDMENT': triples[22],
  'THE RULE': triples[23],
  'HOW / AI RICE FIELD': triples[24],
  'WHO / COMMUNITY': triples[25],
  'NOT A TOP-DOWN PROJECT': triples[26],
  'WHEN · COMMUNITY MEETINGS': triples[27],
  'ADD YOUR NAME · SAVE THE ONSEN': triples[28],
  'PROJECT SITE': triples[29],
  'AI × ONSEN × EDUCATION × AGRICULTURE × COMMUNITY': triples[30],
  'JHR · レポートを読む / READ REPORT ↗': triples[31],
  'WHY · 温泉を守る': triples[32],
  'WHAT · ここがどう変わる？': triples[33],
  'SITE CONCEPT': triples[34],
  'ONSEN CONCEPT': triples[35],
  '01 · ROTENBURO': triples[36],
  'ENGINEERING VALIDATION REQUIRED': triples[37],
  '02 · FOOD': triples[38],
  'AWARA-INSPIRED COMMUNITY FOOD COURT': triples[39],
  '03 · NIGHT': triples[40],
  'PROPOSED DIGITAL KAKEJIKU EXPERIENCE': triples[41],
  'VISIT': triples[42],
  'LISTEN': triples[43],
  'PLAN': triples[44],
  'EXPLORE': triples[45],
  'JOIN': triples[46],
  'ACTION': triples[47],
  'VOTE NO': triples[48],
  'PRESENTATION': triples[49],
  'MONK': triples[50],
  'NEW': triples[51],
  'SAVE OUR ONSEN': triples[52],
  'SAVE THE DRAGON': triples[53],
  'STOP': triples[54],
  'ASSEMBLE': triples[55],
  'LAND': triples[56],
  'CITY': triples[57],
  'UNIVERSITIES': triples[58],
  'CUSTOMERS + PARTNERS': triples[59],
  'この施設が農機を直接動かすわけではありません。私たちのCOG DCコンピュートを、そこで働く学生、FoundUps、研究・地域プロジェクトが使い、農業AI、教育、研究、ものづくりの開発と検証を支えます。': triples[61],
};
Object.assign(aliases, sourceAliases);

function currentLanguage(): Language {
  const lang = document.documentElement.lang.toLowerCase();
  return lang.startsWith('pt') ? 'pt' : lang.startsWith('en') ? 'en' : 'ja';
}

function polishTextNodes(language: Language) {
  const root = document.body;
  if (!root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const raw = node.nodeValue ?? '';
    const trimmed = raw.trim();
    const triple = aliases[trimmed];
    if (triple) {
      const target = triple[language];
      if (trimmed !== target) node.nodeValue = raw.replace(trimmed, target);
    }
    node = walker.nextNode();
  }
}

export default function JapaneseSurfacePolisher() {
  useEffect(() => {
    let polishing = false;
    const run = () => {
      if (polishing) return;
      polishing = true;
      queueMicrotask(() => {
        polishTextNodes(currentLanguage());
        polishing = false;
      });
    };
    run();
    const observer = new MutationObserver(run);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
