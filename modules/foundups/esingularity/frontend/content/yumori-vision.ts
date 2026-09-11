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
    alt: { ja: '実在建物の上層2フロアを60のFoundUpプロジェクトが競い学ぶeSingularityイノベーション・スペースにし、地下をジム・休憩・回復に使う構想', en: 'Upper two floors of the real building adapted as an eSingularity Innovation Space for 60 FoundUp projects, with basement gym, rest and recovery.', pt: 'Dois andares superiores do edifício real adaptados como Espaço de Inovação eSingularity para 60 projetos FoundUp, com academia, descanso e recuperação no subsolo.' },
    title: { ja: '60のFoundUpプロジェクト。1チーム最大3人。あとはAI。', en: '60 FoundUp projects. Max 3 humans per team. The rest is AI.', pt: '60 projetos FoundUp. Máximo de 3 humanos por equipe. O resto é IA.' },
    summary: { ja: '上層2フロアは、人をFoundUpと呼ぶ場所ではなく、小さなチームが課題解決プロジェクトを競い、学び、実証するeSingularityイノベーション・スペースです。', en: 'The upper two floors are an eSingularity Innovation Space where small teams compete, learn and validate problem-solving FoundUp projects; people themselves are not FoundUps.', pt: 'Os dois andares superiores são um Espaço de Inovação eSingularity onde pequenas equipes competem, aprendem e validam projetos FoundUp de solução de problemas; as pessoas não são FoundUps.' },
    evidence: {
      ja: ['FoundUpは人ではなく、課題解決を目的とするプロジェクトです。', '1チーム最大3人は構想上の運営原則で、入居数・選抜方法・階用途は今後の検証事項です。', '地下はジム、休憩、回復スペースとしての再利用候補です。'],
      en: ['A FoundUp is a problem-solving project, not a label for a person.', 'The three-human maximum is a proposed operating principle; occupancy, selection and floor allocation remain to be validated.', 'The basement is a candidate for gym, rest and recovery reuse.'],
      pt: ['FoundUp é um projeto de solução de problemas, não um rótulo para uma pessoa.', 'O máximo de três humanos é um princípio operacional proposto; ocupação, seleção e alocação dos andares ainda precisam ser validadas.', 'O subsolo é candidato a reuso como academia, descanso e recuperação.'],
    },
    link: { label: { ja: 'イノベーション・スペース構想を見る', en: 'See the Innovation Space concept', pt: 'Ver o conceito do Espaço de Inovação' }, href: '#innovation-hub' },
  },
  {
    id: 'local-problem', image: '/vision/slide-08.jpg',
    alt: { ja: '福井の農業課題を農家、学生、小型ロボット、ドローン、COG DCで検証するFoundUp構想', en: 'Fukui agriculture problem-solving concept with farmers, students, robots, drones and COG DC-enabled FoundUp projects.', pt: 'Conceito de solução de problemas agrícolas em Fukui com agricultores, estudantes, robôs, drones e projetos FoundUp apoiados pelo COG DC.' },
    title: { ja: '福井の課題から、福井のFoundUpをつくる。', en: 'Turn local problems into local FoundUp projects.', pt: 'Transformar problemas locais em projetos FoundUp locais.' },
    summary: { ja: '農業、除草、ドローン、画像認識など、地域課題をAIとコンピュートで試作し、現場で検証します。', en: 'Prototype local solutions with AI and compute, then validate them in real fields and workplaces.', pt: 'Prototipar soluções locais com IA e computação e validá-las em campos e locais de trabalho reais.' },
    evidence: {
      ja: ['地域課題 → AI + COG DC → 試作 → 現場検証 → FoundUp。', '自律農機やドローン等は導入済み設備ではなく、検証候補です。'],
      en: ['Local problem → AI + COG DC → prototype → field validation → FoundUp.', 'Autonomous farm machines and drones are validation candidates, not installed equipment.'],
      pt: ['Problema local → IA + COG DC → protótipo → validação em campo → FoundUp.', 'Máquinas agrícolas autônomas e drones são candidatos de validação, não equipamentos já instalados.'],
    },
    link: { label: { ja: '地域活用を見る', en: 'See local applications', pt: 'Ver aplicações locais' }, href: '#innovation-hub' },
  },
  {
    id: 'fukui-prototype', image: '/vision/slide-09.jpg',
    alt: { ja: '福井を起点に、日本各地の学校、地域施設、温泉、大学、産業へ分散型コンピュートの可能性を広げる概念図', en: 'Concept map extending distributed compute from Fukui to schools, civic assets, onsens, universities and industry across Japan.', pt: 'Mapa conceitual estendendo computação distribuída de Fukui para escolas, ativos públicos, onsens, universidades e indústria em todo o Japão.' },
    title: { ja: '福井から、日本の分散型コンピュートへ。', en: 'From Fukui to a distributed compute model for Japan.', pt: 'De Fukui para um modelo de computação distribuída para o Japão.' },
    summary: { ja: '巨大集中型だけではなく、地域に役立つ小さなAIインフラを検証する福井プロトタイプです。', en: 'Fukui is a prototype for testing smaller, region-serving AI infrastructure alongside hyperscale systems.', pt: 'Fukui é um protótipo para testar infraestrutura de IA menor e voltada à região ao lado de sistemas hiperscale.' },
    evidence: {
      ja: ['1→5→10→20+MWは段階的な構想レンジで、確定容量・契約・許認可ではありません。', '他地域への展開は各地の建物、安全、電力、通信、需要、土地、運営主体ごとに検証します。'],
      en: ['1→5→10→20+MW is a staged vision range, not contracted or permitted capacity.', 'Replication elsewhere requires site-specific validation of buildings, safety, power, network, demand, land and operators.'],
      pt: ['1→5→10→20+MW é uma faixa de visão por etapas, não capacidade contratada ou licenciada.', 'Replicação em outros locais exige validação específica de edifícios, segurança, energia, rede, demanda, terreno e operadores.'],
    },
    link: { label: { ja: '福井の未来を見る', en: 'See Fukui’s future', pt: 'Ver o futuro de Fukui' }, href: '/future' },
  },
  {
    id: 'choice', image: '/vision/slide-10.jpg',
    alt: { ja: '実在する建物が残る夕景の中で、解体前に未来を比較しYUMORIに参加する選択を示す構想', en: 'Closing vision of the real building still standing, inviting comparison before demolition and participation through YUMORI.', pt: 'Visão final do edifício real ainda de pé, convidando à comparação antes da demolição e à participação via YUMORI.' },
    title: { ja: '建物は、まだ立っている。選択肢も、まだ残っている。', en: 'The building is still standing. So is the choice.', pt: 'O edifício ainda está de pé. A escolha também.' },
    summary: { ja: '解体前に未来を比較する。その判断を守る人がYUMORIです。', en: 'Compare the future before demolition. YUMORI is the movement that protects that choice.', pt: 'Comparar o futuro antes da demolição. YUMORI é o movimento que protege essa escolha.' },
    evidence: {
      ja: ['YUMORI参加は寄付・投資・契約・運営責任の引受けではありません。', 'eSingularity.aiがビジョン、YUMORI.meが参加の入口です。'],
      en: ['Joining YUMORI is not a donation, investment, contract or operating obligation.', 'eSingularity.ai owns the vision; YUMORI.me is the participation gateway.'],
      pt: ['Participar do YUMORI não é doação, investimento, contrato nem obrigação operacional.', 'eSingularity.ai abriga a visão; YUMORI.me é a porta de participação.'],
    },
    link: { label: { ja: '湯守になる', en: 'Become a YUMORI', pt: 'Tornar-se YUMORI' }, href: 'https://yumori.me' },
  },
];

export const visionUi: Record<YumoriLocale, { label: string; title: string; previous: string; next: string; pause: string; play: string; details: string; fullscreen: string; exit: string; join: string; jhr: string }> = {
  ja: { label: 'YUMORI / PROJECT ESINGULARITY — 10枚のビジョン', title: '壊す前に、未来を比べる。', previous: '前へ', next: '次へ', pause: '自動再生を止める', play: '自動再生', details: '根拠と注記', fullscreen: '全画面で見る', exit: '全画面を閉じる', join: 'YUMORIに参加', jhr: 'JHRを読む' },
  en: { label: 'YUMORI / PROJECT ESINGULARITY — 10-SLIDE VISION', title: 'Before Demolition, Compare the Future.', previous: 'Previous', next: 'Next', pause: 'Pause autoplay', play: 'Autoplay', details: 'Evidence & notes', fullscreen: 'View full screen', exit: 'Exit full screen', join: 'Join YUMORI', jhr: 'Read JHR' },
  pt: { label: 'YUMORI / PROJECT ESINGULARITY — VISÃO EM 10 SLIDES', title: 'Antes de demolir, compare o futuro.', previous: 'Anterior', next: 'Próximo', pause: 'Pausar reprodução', play: 'Reprodução automática', details: 'Evidências e notas', fullscreen: 'Ver em tela cheia', exit: 'Sair da tela cheia', join: 'Participar do YUMORI', jhr: 'Ler JHR' },
};

export function getYumoriVisionSlides(locale: YumoriLocale): YumoriVisionSlide[] {
  return source.map((item) => ({
    id: item.id,
    image: item.image,
    alt: item.alt[locale],
    title: item.title[locale],
    summary: item.summary[locale],
    evidence: item.evidence[locale],
    link: { label: item.link.label[locale], href: item.link.href },
  }));
}
