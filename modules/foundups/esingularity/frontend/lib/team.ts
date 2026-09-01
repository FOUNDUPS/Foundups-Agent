export type TeamProfile = {
  isPublished?: boolean;
  slug: string;
  group: 'core' | 'endorsers' | 'community' | 'network';
  role: string;
  name: string;
  secondary: string;
  image: string;
  imageAlt: string;
  imagePosition?: string;
  introduction: string;
  statement: string;
  facts: Array<{ label: string; value: string }>;
  gallery: Array<{ src: string; alt: string; caption: string; position?: string }>;
  links?: Array<{ label: string; href: string }>;
  feature?: {
    kind: 'video';
    eyebrow: string;
    title: string;
    description: string;
    cta: string;
    href: string;
    image: string;
    imageAlt: string;
  };
  disclosure?: string;
};

export const teamProfiles: TeamProfile[] = [
  {
    isPublished: true,
    slug: '012',
    group: 'core',
    role: 'FOUNDER · CAMPAIGN DIRECTOR',
    name: '012 · Monk UnDaoDu',
    secondary: 'Michael J Trout · The Atheist Monk',
    image: '/team/012-landowners-private.png',
    imageAlt: 'Michael J Trout with local community members at the historic Ryukoji site',
    imagePosition: '50% 48%',
    introduction: 'EDUITとeSingularityの創設者。重度のディスレクシアを持つ学習者としての経験から、誰もが自律して学べる未来を追い続けています。',
    statement: '2007年に「Educational Singularity」という言葉と三段階の未来像を提唱。いま、その第3段階に必要な地域の計算力を、福井の教育・農業・産業のためにつくろうとしています。',
    facts: [
      { label: 'IDENTITY', value: '012 / Monk UnDaoDu' },
      { label: 'MISSION', value: '教育と地域革新のための計算基盤' },
      { label: 'PROJECT ROLE', value: '創設者・キャンペーンディレクター' },
    ],
    gallery: [
      { src: '/team/community-hillside-private.png', alt: 'Michael J Trout with a community work group on the hillside', caption: '地域の現場で。建物だけでなく、土地と人の関係から始める。' },
      { src: '/team/sigef-circle-private.png', alt: 'Michael J Trout with participants at SIGEF 2019 Tokyo', caption: 'SIGEF 2019 Tokyo。AIと社会的利益をめぐる国際的な対話の記録。' },
      { src: '/team/sigef-2019.jpg', alt: 'Attended SIGEF 2019 Tokyo event record', caption: 'SIGEF 2019 Tokyo attendee record.' },
    ],
    links: [
      { label: 'LinkedIn 公開プロフィール', href: 'https://jp.linkedin.com/in/openstartup' },
      { label: 'eSingularity の公開記録', href: 'https://www.linkedin.com/company/esingularity' },
    ],
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
    slug: 'hasegawa',
    group: 'endorsers',
    role: 'D-K · DIGITAL KAKEJIKU',
    name: '長谷川 章',
    secondary: 'Akira Hasegawa · D-K artist',
    image: '/team/hasegawa-private.png',
    imageAlt: 'Akira Hasegawa pictured with Michael J Trout',
    imagePosition: '48% 42%',
    introduction: 'D-K（デジタル掛軸）を生み出したアーティスト、長谷川章。',
    statement: '光が建物の表情をゆっくり変え、同じ景色を二度と繰り返さないD-K。閉じた施設を、夜に人が集まる九頭竜のランドマークへ変える文化構想として紹介します。',
    facts: [
      { label: 'ART', value: 'D-K / Digital Kakejiku' },
      { label: 'ARTIST', value: '長谷川 章 / Akira Hasegawa' },
      { label: 'SITE VISION', value: '夜の文化・九頭竜のランドマーク' },
    ],
    gallery: [],
    feature: {
      kind: 'video',
      eyebrow: 'D-K IN MOTION',
      title: '静止画では伝わらない光を、映像で。',
      description: 'D-Kが建築と夜の風景をどう変えるのか。まず作品の動きを見て、その可能性を感じてください。',
      cta: 'YouTubeで映像を見る',
      href: 'https://www.youtube.com/watch?v=jI9decHbUIY',
      image: '/team/hasegawa-private.png',
      imageAlt: 'Akira Hasegawa and Michael J Trout, used as the D-K video link poster',
    },
    links: [
      { label: 'D-K デジタル掛軸 公式サイト', href: 'https://www.digital-kakejiku.com/' },
      { label: 'D-Kを映像で見る', href: 'https://www.youtube.com/watch?v=jI9decHbUIY' },
    ],
    disclosure: '映像と公式サイトはD-Kを理解するための外部資料です。この掲載だけで、施設への設置契約やプロジェクトへの正式な支持を意味するものではありません。',
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
  { id: 'endorsers', eyebrow: 'ENDORSERS', title: '声を重ねる人', description: '本人が確認した氏名、役割、言葉だけを掲載する支持者の場所。' },
  { id: 'community', eyebrow: 'LANDOWNERS & COMMUNITY', title: '場所に最も近い人', description: '土地所有者、周辺地域、施設の記憶を持つ人が意思決定の中心です。' },
  { id: 'network', eyebrow: 'GLOBAL NETWORK', title: '世界との接点', description: '012の活動履歴と対話の記録。写真は支持や提携を自動的に意味しません。' },
] as const;

export const publicTeamProfiles = teamProfiles.filter((profile) => profile.isPublished);

export function getTeamProfile(slug: string) {
  return publicTeamProfiles.find((profile) => profile.slug === slug);
}
