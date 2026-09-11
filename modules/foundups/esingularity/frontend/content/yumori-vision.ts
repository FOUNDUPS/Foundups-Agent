import type { YumoriLocale } from './yumori-presentation';

export type YumoriVisionSlide = {
  id: string;
  image: string;
  alt: string;
  title: string;
  summary: string;
  evidence: string[];
  link: { label: string; href: string };
};

type Localized = Record<YumoriLocale, string>;
type LocalizedList = Record<YumoriLocale, string[]>;

type VisionSource = {
  id: string;
  image: string;
  alt: Localized;
  title: Localized;
  summary: Localized;
  evidence: LocalizedList;
  link: { label: Localized; href: string };
};

const source: VisionSource[] = [
  {
    id: 'vision', image: '/vision/slide-01.jpg',
    alt: {
      ja: '実在する旧すかっとランド九頭竜の建物を残し、夜間照明、温泉、D-K、別棟COG DCを組み合わせる再生構想',
      en: 'Adaptive-reuse vision retaining the real Sukatto Land Kuzuryu building with night lighting, onsen, D-K and a separate COG DC.',
      pt: 'Visão de reuso adaptativo que preserva o edifício real do Sukatto Land Kuzuryu com iluminação noturna, onsen, D-K e COG DC separado.',
    },
    title: { ja: '壊す前に、未来を比べる。', en: 'Before Demolition, Compare the Future.', pt: 'Antes de demolir, compare o futuro.' },
    summary: {
      ja: '既存建物を壊してから考えるのではなく、24時間温泉、COG DC、eSingularity Lab、D-Kを組み合わせた再利用可能性を先に比較します。',
      en: 'Test the reuse option first: a 24-hour onsen, COG DC, eSingularity Lab and D-K around the retained building.',
      pt: 'Testar primeiro a opção de reuso: onsen 24 horas, COG DC, eSingularity Lab e D-K no edifício preservado.',
    },
    evidence: {
      ja: ['建物・設備・法令適合性は未検証で、再利用の成立を保証するものではありません。', 'このビジュアルは実在建物を基にした構想図です。'],
      en: ['Building, systems and code feasibility remain unverified.', 'The visual is a concept based on the real building, not completed construction.'],
      pt: ['A viabilidade estrutural, técnica e legal ainda não foi validada.', 'A imagem é um conceito baseado no edifício real, não uma obra concluída.'],
    },
    link: { label: { ja: '現在の判断を見る', en: 'See the current decision', pt: 'Ver a decisão atual' }, href: '#city-action' },
  },
  {
    id: 'option-value', image: '/vision/slide-02.jpg',
    alt: { ja: '同じ実在建物について解体と再生を左右に比較し、解体見込みとモデル値を示す構想スライド', en: 'Side-by-side demolition versus regeneration comparison of the same real building, with reported and modeled values.', pt: 'Comparação lado a lado entre demolição e regeneração do mesmo edifício real, com valores reportados e modelados.' },
    title: { ja: 'なぜ15.8億円を使って、選択肢を壊すのか。', en: 'Why spend ¥1.58B to erase the option?', pt: 'Por que gastar ¥1,58 bi para eliminar a opção?' },
    summary: { ja: '解体費という不可逆な支出と、再利用の経済的可能性を同じ画面で比較します。', en: 'Compare the irreversible demolition cost with the economic option value of testing reuse.', pt: 'Compare o custo irreversível da demolição com o valor opcional de testar o reuso.' },
    evidence: {
      ja: ['REPORTED：将来の解体見込み 約15.8億円。', 'VERIFIED：2018年度利用者 129,649人。', 'MODELLED：5年売上 約53.7億円、5年累計FCFE 約19.4億円。予測・保証ではありません。'],
      en: ['REPORTED: future demolition estimate about ¥1.58B.', 'VERIFIED: FY2018 users 129,649.', 'MODELLED: about ¥5.37B five-year revenue and ¥1.94B cumulative five-year FCFE; not a forecast or guarantee.'],
      pt: ['REPORTADO: estimativa futura de demolição de cerca de ¥1,58 bi.', 'VERIFICADO: 129.649 usuários no FY2018.', 'MODELADO: cerca de ¥5,37 bi de receita em cinco anos e ¥1,94 bi de FCFE acumulado; não é previsão nem garantia.'],
    },
    link: { label: { ja: '経済根拠を見る', en: 'See economic evidence', pt: 'Ver evidências econômicas' }, href: '#story' },
  },
  {
    id: 'culture-after-dark', image: '/vision/slide-03.jpg',
    alt: { ja: '実在する旧施設の外壁をD-Kに着想を得た光で彩り、夜の文化拠点として活用する構想', en: 'The real building activated at night with D-K-inspired light projections and cultural programming.', pt: 'O edifício real ativado à noite com projeções de luz inspiradas em D-K e programação cultural.' },
    title: { ja: '毎夜、違う景色。', en: 'Every night, a different experience.', pt: 'Cada noite, uma experiência diferente.' },
    summary: { ja: '既存建物を光・音・人の目的地に変えるD-K / Digital Kakejikuの文化構想です。', en: 'A cultural proposal to turn the retained building into a destination for light, sound and people.', pt: 'Uma proposta cultural para transformar o edifício preservado em destino de luz, som e pessoas.' },
    evidence: {
      ja: ['長谷川章氏はD-K / Digital Kakejikuを世界各地で展開しています。', '本サイトへの正式参加・本部化は別途合意が必要で、現時点では提案段階です。'],
      en: ['Akira Hasegawa has installed D-K / Digital Kakejiku internationally.', 'Formal participation or headquarters status requires separate agreement and is not claimed.'],
      pt: ['Akira Hasegawa realizou instalações D-K / Digital Kakejiku internacionalmente.', 'Participação formal ou status de sede exige acordo separado e não é afirmado.'],
    },
    link: { label: { ja: 'D-K公式サイト', en: 'Official D-K site', pt: 'Site oficial D-K' }, href: 'https://www.digital-kakejiku.com/' },
  },
  {
    id: 'onsen-destination', image: '/vision/slide-04.jpg',
    alt: { ja: '実在建物を残した24時間温泉、露天風呂、サウナ、ラウンジ、地下ジムと回復スペースの構想', en: 'Retained-building concept for a 24-hour onsen destination with rotenburo, sauna, lounge, basement gym and recovery space.', pt: 'Conceito com edifício preservado para onsen 24 horas, rotenburo, sauna, lounge, academia no subsolo e área de recuperação.' },
    title: { ja: '24時間温泉。大きな露天風呂。滞在したくなる場所。', en: 'A 24-hour onsen destination designed for staying.', pt: 'Um destino onsen 24 horas feito para permanecer.' },
    summary: { ja: '浴場は公共動線から分離し、温泉、サウナ、休憩、食、小規模な音楽、ジム・回復機能を組み合わせる構想です。', en: 'Private bathing zones remain separated from public circulation while wellness, food, music, gym and recovery functions extend the stay.', pt: 'Áreas de banho privadas ficam separadas da circulação pública, enquanto bem-estar, comida, música, academia e recuperação prolongam a visita.' },
    evidence: {
      ja: ['24時間運営、露天風呂規模、地下用途は事業性・建築・消防・温泉法等の検証が必要です。', '「日本最大」は現時点で事実認定せず、規模目標は比較調査後に表現します。'],
      en: ['24-hour operation, bath scale and basement use require business, building, fire and onsen-law validation.', 'No “Japan’s largest” claim is made before comparative verification.'],
      pt: ['Operação 24h, escala dos banhos e uso do subsolo exigem validação de negócios, construção, incêndio e legislação de onsen.', 'Não se afirma “o maior do Japão” antes de verificação comparativa.'],
    },
    link: { label: { ja: '温泉構想を見る', en: 'See the onsen concept', pt: 'Ver conceito do onsen' }, href: '#future-place' },
  },
  {
    id: 'compute-rice-field', image: '/vision/slide-05.jpg',
    alt: { ja: '福井の田んぼ、電力、プロセッサ、コンピュートを結ぶAI田んぼの比喩と実在施設', en: 'AI rice-field metaphor linking Fukui land, power, processors and compute around the real site.', pt: 'Metáfora do arrozal de IA conectando terra, energia, processadores e computação ao redor do local real.' },
    title: { ja: 'コンピュートは、新しい「田んぼ」だ。', en: 'Compute is the new rice field.', pt: 'Computação é o novo arrozal.' },
    summary: { ja: '1 AI Rice Field ≈ 1 MWを説明単位として、地域の電力を地域で役立つ計算資源へ変える発想です。', en: 'Use “1 AI Rice Field ≈ 1 MW” as a planning metaphor for converting regional power into useful compute.', pt: 'Usar “1 AI Rice Field ≈ 1 MW” como metáfora de planejamento para converter energia regional em computação útil.' },
    evidence: {
      ja: ['土地 → 電力 → プロセッサ → コンピュート。', 'AI田んぼは説明の比喩であり、農地転用を意味しません。'],
      en: ['Land → power → processors → compute.', '“AI rice field” is an explanatory metaphor, not a proposal to convert farmland.'],
      pt: ['Terra → energia → processadores → computação.', '“Arrozal de IA” é uma metáfora explicativa, não uma proposta de conversão de terras agrícolas.'],
    },
    link: { label: { ja: 'COG DC計画を見る', en: 'See the COG DC plan', pt: 'Ver plano COG DC' }, href: 'https://pc.yumori.info' },
  },
  {
    id: 'cogdc', image: '/vision/slide-06.jpg',
    alt: { ja: '実在建物の別棟にCOG DCを配置し、回収熱を温泉、給湯、融雪、農業へ戻す構想', en: 'Separate COG DC beside the real building with recoverable heat routed to onsen, hot water, snowmelt and agriculture.', pt: 'COG DC separado ao lado do edifício real com calor recuperável direcionado ao onsen, água quente, derretimento de neve e agricultura.' },
    title: { ja: '熱を捨てない。地域へ戻す。', en: 'Don’t waste the heat. Return it to the community.', pt: 'Não desperdice o calor. Devolva-o à comunidade.' },
    summary: { ja: 'COG DCを温泉棟とは別配置し、計算で生じる回収可能な熱の地域利用を技術検証します。', en: 'Keep the COG DC separate from the bath building and test useful local applications for recoverable compute heat.', pt: 'Manter o COG DC separado do edifício dos banhos e testar usos locais úteis para o calor recuperável da computação.' },
    evidence: {
      ja: ['温泉加温、館内給湯・暖房、道路融雪、農業は温度・距離・年間需要・設備費を検証します。', '熱利用は成立を前提とせず、工学検証で可否を判断します。'],
      en: ['Onsen heating, building hot water, road snowmelt and agriculture require temperature, distance, annual-demand and cost validation.', 'Heat reuse is a hypothesis, not an assumed outcome.'],
      pt: ['Aquecimento do onsen, água quente do prédio, derretimento de neve e agricultura exigem validação de temperatura, distância, demanda anual e custo.', 'O reuso de calor é uma hipótese, não um resultado presumido.'],
    },
    link: { label: { ja: '技術構想を見る', en: 'See technical concept', pt: 'Ver conceito técnico' }, href: '#proposal' },
  },
  {
    id: 'esingularity-lab', image: '/vision/slide-07.jpg',
    alt: { ja: '実在建物の上層2フロアを60 FoundUpsのeSingularity Labにし、地下をジム・休憩・回復に使う構想', en: 'Upper two floors of the real building adapted for 60 FoundUps, with basement gym, rest and recovery.', pt: 'Dois andares superiores do edifício real adaptados para 60 FoundUps, com academia, descanso e recuperação no subsolo.' },
    title: { ja: '60 FoundUps。1チーム最大3人。あとはAI。', en: '60 FoundUps. Max 3 humans per team. The rest is AI.', pt: '60 FoundUps. Máximo de 3 humanos por equipe. O resto é IA.' },
    summary: { ja: '少人数チームが地域課題を解き、成果を示したFoundUpが上位スペースへ進む競争・学習・実装環境を構想します。', en: 'Small teams solve real problems and advance through a competitive learn-build-demonstrate environment.', pt: 'Pequenas equipes resolvem problemas reais e avançam por um ambiente competitivo de aprender, construir e demonstrar.' },
    evidence: {
      ja: ['FoundUpは問題の収益化より問題解決を先に置くという本プロジェクトの概念です。', '60チーム、最大3人、階用途は構想値で、建物・消防・運営検証により変更されます。'],
      en: ['FoundUp is this project’s concept: solve the problem first; monetization follows value creation.', '60 teams, max three humans and floor uses are design targets subject to building, fire and operating validation.'],
      pt: ['FoundUp é o conceito do projeto: resolver o problema primeiro; monetização vem após criar valor.', '60 equipes, no máximo três humanos e usos dos andares são metas sujeitas a validação construtiva, contra incêndio e operacional.'],
    },
    link: { label: { ja: 'FoundUps基盤を見る', en: 'See FoundUps foundation', pt: 'Ver base FoundUps' }, href: 'https://github.com/FOUNDUPS/Foundups-Agent' },
  },
  {
    id: 'local-problem', image: '/vision/slide-08.jpg',
    alt: { ja: '福井の農業現場で農家、学生、AI、COG DC、ロボット、ドローンが地域課題を検証する構想', en: 'Fukui field-test vision with farmers, students, AI, COG DC, robots and drones solving local problems.', pt: 'Visão de testes em campo em Fukui com agricultores, estudantes, IA, COG DC, robôs e drones resolvendo problemas locais.' },
    title: { ja: '福井の課題から、福井の会社をつくる。', en: 'Turn local problems into local companies.', pt: 'Transformar problemas locais em empresas locais.' },
    summary: { ja: '地域課題 → AI + COG DC → 試作 → 現場検証 → FoundUpという実装ループをつくります。', en: 'Build a local loop: problem → AI + COG DC → prototype → field test → FoundUp.', pt: 'Criar um ciclo local: problema → IA + COG DC → protótipo → teste de campo → FoundUp.' },
    evidence: {
      ja: ['農業、除草、ドローン、画像認識、小型ロボットは候補例であり、導入済み設備ではありません。', '実際のテーマは地域・大学・企業との需要確認から決めます。'],
      en: ['Agriculture, weeding, drones, vision and small robots are candidate examples, not deployed systems.', 'Actual projects should be chosen through demand discovery with local partners.'],
      pt: ['Agricultura, capina, drones, visão e pequenos robôs são exemplos candidatos, não sistemas já implantados.', 'Projetos reais devem ser escolhidos por descoberta de demanda com parceiros locais.'],
    },
    link: { label: { ja: '福井の未来を見る', en: 'See Fukui future', pt: 'Ver futuro de Fukui' }, href: '/future' },
  },
  {
    id: 'fukui-prototype', image: '/vision/slide-09.jpg',
    alt: { ja: '福井を起点に学校、自治体、地域産業、大学、温泉、農村へ分散型コンピュートの可能性を示す日本地図', en: 'Japan map showing Fukui as a prototype node for distributed compute across schools, government, industry, universities, onsen and rural communities.', pt: 'Mapa do Japão mostrando Fukui como nó protótipo de computação distribuída para escolas, governo, indústria, universidades, onsen e comunidades rurais.' },
    title: { ja: '福井から、日本の分散型コンピュートへ。', en: 'From Fukui to a distributed compute model for Japan.', pt: 'De Fukui para um modelo distribuído de computação no Japão.' },
    summary: { ja: '巨大集中だけでなく、条件の合う地域に小さく役立つAIインフラを育てられるか、福井をプロトタイプに検証します。', en: 'Use Fukui as a prototype for community-scale AI infrastructure that complements, rather than merely copies, hyperscale concentration.', pt: 'Usar Fukui como protótipo de infraestrutura de IA em escala comunitária que complemente, em vez de apenas copiar, a concentração hyperscale.' },
    evidence: {
      ja: ['1 → 5 → 10 → 20+ MWは需要・電力・土地・許認可・資本で段階判断する構想です。', '全国展開や他自治体参加は未決定です。'],
      en: ['1 → 5 → 10 → 20+ MW is a staged concept gated by demand, power, land, permits and capital.', 'National replication or participation by other municipalities is not yet decided.'],
      pt: ['1 → 5 → 10 → 20+ MW é um conceito em etapas condicionado por demanda, energia, terreno, licenças e capital.', 'Replicação nacional ou participação de outros municípios ainda não está decidida.'],
    },
    link: { label: { ja: 'JAPAN HYPERSCALER REPORT', en: 'JAPAN HYPERSCALER REPORT', pt: 'JAPAN HYPERSCALER REPORT' }, href: '/reports/jhr' },
  },
  {
    id: 'choice', image: '/vision/slide-10.jpg',
    alt: { ja: '実在建物を残した再生構想の夕景と、解体前に未来を比較するYUMORI参加呼びかけ', en: 'Closing adaptive-reuse vision of the real building and a call to compare futures before demolition.', pt: 'Visão final de reuso adaptativo do edifício real e convite para comparar futuros antes da demolição.' },
    title: { ja: '建物は、まだ立っている。選択肢も、まだ残っている。', en: 'The building is still standing. So is the choice.', pt: 'O edifício ainda está de pé. A escolha também.' },
    summary: { ja: '解体前に未来を比較し、再利用を検証する努力の守り手＝YUMORIを募ります。', en: 'Compare the futures before demolition and become a YUMORI—a guardian of the effort to test reuse.', pt: 'Compare os futuros antes da demolição e torne-se YUMORI — guardião do esforço de testar o reuso.' },
    evidence: {
      ja: ['YUMORI参加は寄付、投資、契約、運営責任の引受けを意味しません。', '現在の組織は設立準備段階です。'],
      en: ['Joining YUMORI does not itself mean donating, investing, contracting or taking operating responsibility.', 'The organization remains in a preparatory stage.'],
      pt: ['Entrar no YUMORI não significa por si só doar, investir, contratar ou assumir responsabilidade operacional.', 'A organização permanece em fase preparatória.'],
    },
    link: { label: { ja: 'YUMORI / 湯守になる', en: 'Become a YUMORI', pt: 'Torne-se YUMORI' }, href: 'https://yumori.me' },
  },
];

export const visionUi = {
  ja: { label: 'YUMORI / PROJECT eSINGULARITY — 10枚の未来', title: '10枚で未来を見る', fullscreen: '全画面で見る', exit: '全画面を閉じる', previous: '前へ', next: '次へ', pause: '停止', play: '再生', details: '根拠・注記', jhr: 'JHRを読む', join: 'YUMORIに参加' },
  en: { label: 'YUMORI / PROJECT eSINGULARITY — 10-SLIDE VISION', title: 'See the future in 10 slides', fullscreen: 'View fullscreen', exit: 'Exit fullscreen', previous: 'Previous', next: 'Next', pause: 'Pause', play: 'Play', details: 'Evidence & notes', jhr: 'Read JHR', join: 'Join YUMORI' },
  pt: { label: 'YUMORI / PROJECT eSINGULARITY — VISÃO EM 10 SLIDES', title: 'Veja o futuro em 10 slides', fullscreen: 'Ver em tela cheia', exit: 'Sair da tela cheia', previous: 'Anterior', next: 'Próximo', pause: 'Pausar', play: 'Reproduzir', details: 'Evidências e notas', jhr: 'Ler JHR', join: 'Entrar no YUMORI' },
} as const;

export function getYumoriVisionSlides(locale: YumoriLocale): YumoriVisionSlide[] {
  return source.map((slide) => ({
    id: slide.id,
    image: slide.image,
    alt: slide.alt[locale],
    title: slide.title[locale],
    summary: slide.summary[locale],
    evidence: slide.evidence[locale],
    link: { label: slide.link.label[locale], href: slide.link.href },
  }));
}
