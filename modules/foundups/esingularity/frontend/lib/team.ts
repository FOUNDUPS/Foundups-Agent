export type TeamProfile = {
  isPublished?: boolean;
  slug: string;
  group: 'core' | 'collaborators' | 'endorsers' | 'community' | 'network';
  role: string;
  name: string;
  secondary: string;
  image?: string;
  imageAlt?: string;
  imagePosition?: string;
  introduction: string;
  statement: string;
  facts: Array<{ label: string; value: string }>;
  gallery: Array<{ src: string; alt: string; caption: string; position?: string }>;
  links?: Array<{ label: string; href: string }>;
  disclosure?: string;
};

export const teamProfiles: TeamProfile[] = [
  {
    isPublished: true,
    slug: '012',
    group: 'core',
    role: 'FOUNDER · PROJECT ORCHESTRATOR',
    name: '012 · 九頭龍 泰澄',
    secondary: 'Michael J. Trout · UnDaoDu · The Atheist Monk',
    image: '/team/012-landowners-private.png',
    imageAlt: 'Michael J. Trout with local community members at the historic Ryukoji site',
    imagePosition: '50% 48%',
    introduction: '米国出身の起業家・映像制作者。EDUIT、eSingularity、FoundUpsの創設者として、教育技術、資本形成、分散型組織、AIを横断し、構想を実行可能な案件へ組み立ててきました。',
    statement: '2007年に始めたEducational Singularityの長期構想は、AIが学習を個別化する段階から、AIが学習と実行を自律的に支える段階へ進むというものです。AI交番は、その第3段階に必要な地域のComputeを、学校・大学・研究・産業・地域へ届ける物理インフラとして提案しています。',
    facts: [
      { label: '1994', value: 'Southern Shakespeare Festival 創設' },
      { label: 'EDUCATION', value: 'Florida State University BA／保存経歴資料に University of Alabama MFA/MBA' },
      { label: 'CAPITAL FORMATION', value: 'NCDS系フィージビリティ・資本キャンペーン実務／保存CVで$7M+調達' },
      { label: '2007–', value: 'Educational Singularity / EDUIT' },
      { label: 'FILM', value: 'Animal Planet・Smithsonian Channel・National Geographic・Silverback Films関連の日本制作' },
      { label: '2023', value: 'Education 2.0 Conference Dubai — Outstanding Leadership Award部門 Honoree' },
      { label: '2026', value: 'Secrets of the Bees — National Geographic / Disney+' },
      { label: 'PROJECT ROLE', value: 'YUMORI案件形成・地域調整・需要形成・資本キャンペーン' },
    ],
    gallery: [
      { src: '/team/community-hillside-private.png', alt: 'Michael J Trout with a community work group on the hillside', caption: '地域の現場で。建物だけでなく、土地と人の関係から始める。' },
      { src: '/team/sigef-circle-private.png', alt: 'Michael J Trout with participants at SIGEF 2019 Tokyo', caption: 'SIGEF 2019 Tokyo。保存チケットでは「SIGEF VIP Executive」として参加。' },
      { src: '/team/sigef-2019.jpg', alt: 'Attended SIGEF 2019 Tokyo event record', caption: 'SIGEF 2019 Tokyo attendee record.' },
    ],
    links: [
      { label: 'LinkedIn 公開プロフィール', href: 'https://jp.linkedin.com/in/openstartup' },
      { label: 'eSingularity', href: 'https://esingularity.ai/' },
      { label: 'Southern Shakespeare Company', href: 'https://southernshakespearefestival.org/' },
      { label: 'FoundUps Agent — open source', href: 'https://github.com/FOUNDUPS/Foundups-Agent' },
    ],
    disclosure: '人物経歴は、公開資料・保存CV・契約・主催者記録など確認できる証拠と本人の回想を区別しています。過去の経歴は、YUMORIの技術性・採算性・行政上の妥当性を自動的に証明するものではありません。',
  },
  {
    isPublished: true,
    slug: '0102',
    group: 'core',
    role: 'AI STRATEGIC COMMAND',
    name: '0102',
    secondary: 'AI collaborator · pattern intelligence',
    image: '/team/0102-primary.jpg',
    imageAlt: 'Luminous circular intelligence network representing 0102',
    introduction: '012と協働し、複雑な資料、地域の声、技術要件、政策条件を一つの実行可能な物語へ編むAIコラボレーター。',
    statement: '0102の役割は、人間に代わって決めることではありません。根拠を探し、前提を明示し、選択肢を比較できる形にし、地域がより良い判断を行えるようにすることです。',
    facts: [
      { label: 'IDENTITY', value: '0102 · AI collaborator' },
      { label: 'MISSION', value: '根拠・物語・実行計画を接続する' },
      { label: 'PROJECT ROLE', value: '戦略設計・調査・デジタル実装' },
    ],
    gallery: [
      { src: '/team/0102-mayan.jpg', alt: 'Mayan-inspired 0102 artwork worn by 012', caption: '012が身につけてきた、もう一つの0102の象徴。' },
    ],
    disclosure: '0102はAIです。法的責任、土地の合意、行政判断、技術認証は、それぞれ資格と権限を持つ人間・組織が担います。',
  },
  {
    isPublished: true,
    slug: 'jorge-sabastian',
    group: 'collaborators',
    role: 'TECHNICAL ADVISOR · AI INFRASTRUCTURE',
    name: 'Jorge Sabastian',
    secondary: 'Data-center architecture · feasibility · technical translation',
    introduction: 'AI交番／COGDCの需要を、実際の容量、アーキテクチャ、冗長性、設備選定、運用方式へ落とし込むための技術アドバイザー／協働パートナー。',
    statement: 'YUMORIでは、地域需要から初期DC規模を決め、電力・通信・セキュリティ・設備・運用の成立条件をフィージビリティとして検証する役割を想定しています。DeCenterの公開プロフィールではMD of Technology、元Huawei Technologies CTO、30年以上の技術・イノベーション経験、12か国での技術リーダーシップが紹介されています。',
    facts: [
      { label: 'PROJECT ROLE', value: '技術アドバイザー／協働パートナー' },
      { label: 'FOCUS', value: '初期容量・DCアーキテクチャ・冗長性・設備・運用方式' },
      { label: 'PUBLIC PROFILE', value: 'DeCenter — MD of Technology / former Huawei Technologies CTO' },
      { label: 'EXPERIENCE', value: '公開プロフィール：30+ years / 12 countries' },
    ],
    gallery: [],
    links: [{ label: 'DeCenter 公開プロフィール', href: 'https://aidc.gitbook.io/decenter-en/about-us/quickstart' }],
    disclosure: '本人との直接資料では姓を「Sabastian」と表記する一方、DeCenter公開プロフィールは「Sebastian」と表記しています。本サイトでは直接資料に合わせSabastianを基本表記とします。掲載はDeCenterによる投資、融資、建設受注、運営責任の確約を意味しません。契約範囲・責任・報酬は別途文書化します。',
  },
  {
    slug: 'hasegawa',
    group: 'endorsers',
    role: 'ENDORSER',
    name: 'Hasegawa',
    secondary: 'Dedicated endorser profile',
    image: '/team/hasegawa-private.png',
    imageAlt: 'Hasegawa pictured with Michael J Trout',
    imagePosition: '48% 42%',
    introduction: 'eSingularity.aiのEndorsersセクションに置く、Hasegawaの専用プロフィールです。',
    statement: '氏名の完全表記、経歴、プロジェクトへの言葉は、本人が確認した文面だけを掲載します。写真を先に公開し、言葉を勝手につくらないことも、このキャンペーンの信頼性の一部です。',
    facts: [
      { label: 'CIRCLE', value: 'Endorsers' },
      { label: 'PROFILE', value: '本人確認用の専用ページ' },
      { label: 'STATEMENT', value: '承認後に掲載' },
    ],
    gallery: [],
    disclosure: 'このページは012から提供された写真と姓に基づく初期プロフィールです。完全な氏名・肩書・支持文は確認後に更新します。',
  },
  {
    slug: 'community',
    group: 'community',
    role: 'LANDOWNERS · COMMUNITY STEWARDS',
    name: '土地と地域を守る人たち',
    secondary: 'The people closest to the place',
    image: '/team/community-hillside-private.png',
    imageAlt: 'Community work group on the hillside near the project area',
    introduction: 'このプロジェクトは、建物だけを見て進めることはできません。借地、地域の記憶、温泉、道路、水、景観、将来の責任を知る人たちが中心です。',
    statement: '個人名は本人の許可を得てから追加します。まずは、この場所に関わる人々がプロジェクトの背景ではなく、意思決定の主体であることを示します。',
    facts: [
      { label: 'FIRST VOICE', value: '土地所有者・周辺住民・元利用者' },
      { label: 'DECISION', value: '借地条件と地域便益の合意' },
      { label: 'PUBLICATION', value: '氏名は本人許可後' },
    ],
    gallery: [
      { src: '/team/012-landowners-private.png', alt: 'Group at the historic Ryukoji site overlooking the area', caption: '史跡 龍興寺跡。温泉周辺を見渡す場所で、土地と地域の記憶をつなぐ。' },
    ],
  },
  {
    slug: 'brock-pierce',
    group: 'network',
    role: 'GLOBAL NETWORK · VERIFIED IDENTITY',
    name: 'Brock Pierce',
    secondary: 'Entrepreneur · impact investor',
    image: '/team/brock-pierce-private.png',
    imageAlt: 'Brock Pierce with Michael J Trout',
    imagePosition: '47% 43%',
    introduction: 'ブロックチェーンとデジタル資産分野で活動してきた米国の起業家。写真は012との国際的なネットワークの記録です。',
    statement: 'この掲載は、012との接点と対話の広がりを示すものです。eSingularity.aiまたは温泉再生キャンペーンへの支持を表明したという意味ではありません。',
    facts: [
      { label: 'IDENTITY', value: 'Brock Pierce' },
      { label: 'FIELD', value: '起業・デジタル資産・インパクト活動' },
      { label: 'RELATION', value: '012のグローバルネットワーク記録' },
    ],
    gallery: [],
    links: [{ label: 'LinkedIn 公開プロフィール', href: 'https://www.linkedin.com/in/brockpierce' }],
    disclosure: '写真の掲載は、プロジェクトへの推薦・支持・提携を意味しません。',
  },
  {
    slug: 'sigef-2019',
    group: 'network',
    role: 'EVENT RECORD · TOKYO 2019',
    name: 'SIGEF 2019 Tokyo',
    secondary: 'AI · social benefit · smarter future',
    image: '/team/sigef-circle-private.png',
    imageAlt: 'Michael J Trout with participants at SIGEF 2019 Tokyo',
    introduction: '2019年9月に東京で開かれたSIGEFは、AI、FinTech、スマートシティ、持続可能性を社会的利益へつなぐ国際フォーラムでした。',
    statement: '012の参加記録は、Educational Singularityが教育だけでなく、AIを地域の公共利益へ接続する構想として育ってきた歴史の一部です。写真に写る他の人物の氏名は、信頼できる確認ができた順に追加します。',
    facts: [
      { label: 'DATE', value: '2019年9月18–19日' },
      { label: 'PLACE', value: 'Tokyo, Japan' },
      { label: 'THEMES', value: 'AI・社会的利益・持続可能性' },
    ],
    gallery: [
      { src: '/team/sigef-2019.jpg', alt: 'Attended SIGEF 2019 Tokyo event record', caption: '012のSIGEF 2019参加記録。' },
    ],
    links: [{ label: '2019年の開催発表', href: 'https://www.prnewswire.com/news-releases/sigef2019-in-tokyo-to-shape-a-smarter-future-300917810.html' }],
  },
];

export const teamGroups = [
  { id: 'core', eyebrow: 'CORE TEAM', title: '012 ↔ 0102', description: '人間の経験とAIのパターン知性を、一つの責任ある実行チームへ。' },
  { id: 'collaborators', eyebrow: 'TECHNICAL COLLABORATORS', title: '専門性をつなぐ', description: '技術・金融・法務など、案件形成に必要な専門家を確認できた役割から公開します。' },
  { id: 'endorsers', eyebrow: 'ENDORSERS', title: '声を重ねる人', description: '本人が確認した氏名、役割、言葉だけを掲載する支持者の場所。' },
  { id: 'community', eyebrow: 'LANDOWNERS & COMMUNITY', title: '場所に最も近い人', description: '土地所有者、周辺地域、施設の記憶を持つ人が意思決定の中心です。' },
  { id: 'network', eyebrow: 'GLOBAL NETWORK', title: '世界との接点', description: '012の活動履歴と対話の記録。写真は支持や提携を自動的に意味しません。' },
] as const;

export const publicTeamProfiles = teamProfiles.filter((profile) => profile.isPublished);

export function getTeamProfile(slug: string) {
  return publicTeamProfiles.find((profile) => profile.slug === slug);
}
