export type YumoriLocale = 'ja' | 'en' | 'pt';

export type YumoriSlide = {
  id: string;
  kicker: string;
  proposition: string;
  number?: string;
  numberLabel?: string;
  explanation: string;
  evidence: string[];
  link: { label: string; href: string };
  visual: 'place' | 'economics' | 'compute' | 'cogdc' | 'floors' | 'ecosystem' | 'agriculture' | 'japan' | 'festival' | 'people';
  image?: string;
  alt?: string;
};

export type YumoriPresentationCopy = {
  label: string;
  title: string;
  controls: { previous: string; next: string; pause: string; play: string; details: string; close: string; slide: string };
  slides: YumoriSlide[];
};

// CANONICAL SOURCE STATE: Japanese is written, reviewed, and approved first.
// Derived languages below must follow this Japanese state and its evidence boundaries.
export const yumoriJa: YumoriPresentationCopy = {
  label: 'YUMORI / PROJECT ESINGULARITY — 10枚のプレゼンテーション',
  title: '壊す前に、未来を比べる。',
  controls: { previous: '前へ', next: '次へ', pause: '自動再生を止める', play: '自動再生を始める', details: '詳しく見る', close: '閉じる', slide: 'スライド' },
  slides: [
    {
      id: 'question', kicker: '01 · THE QUESTION', visual: 'place', image: '/concept-onsen.jpg',
      alt: '温泉と地域の食、人の交流がつながる夜の構想イメージ',
      proposition: 'コンピュートは、この温泉を救い、この地域を再生し、日本を変える力になれるだろうか。',
      explanation: '建物は、まだ立っています。解体は後戻りできません。いま、温泉・学び・仕事・文化を一つにつなぐ再利用案があります。',
      evidence: ['現在の組織は準備委員会です。', '再利用の可能性は、建物・設備・土地・事業性の調査を経て判断します。'],
      link: { label: '現在の計画と市民判断を見る', href: '#city-action' },
    },
    {
      id: 'value', kicker: '02 · ECONOMIC OPTION VALUE', visual: 'economics', image: '/why-preserve.jpg',
      alt: '保存案と解体案の経済的な比較を示す既存資料',
      proposition: '壊す前に、この資産の価値を測っただろうか。',
      number: '約15.8億円', numberLabel: '議会質問資料に示された解体見込み。予算・契約額ではありません。',
      explanation: '2018年度の利用者は129,649人。直接消費は年間約1.30〜7.19億円という検討用スクリーンです。下限は1人1,000円の仮定、上限は福井県2025年日帰り観光消費単価5,546円を用いたMODELLED値で、予測ではありません。',
      evidence: ['VERIFIED：2018年度利用者 129,649人。', 'REPORTED：解体見込み 約15.8億円。予算・契約額ではありません。', 'MODELLED：直接消費 約1.30〜7.19億円／年。波及効果、雇用、税収は未算入。', 'PROJECT RANGE：既存施設活用と同等規模新設の差額 約11〜15億円。施工者見積もり未取得。'],
      link: { label: '経済効果と計算根拠を見る', href: '#story' },
    },
    {
      id: 'compute', kicker: '03 · WHAT IS COMPUTE?', visual: 'compute', image: '/yumori-compute-field.png',
      alt: '福井の田んぼから小規模なコンピュート施設へ連なる構想イメージ',
      proposition: 'データセンターは、コンピュートを育てる田んぼだ。',
      explanation: 'AIは無料で考えるわけではありません。プロセッサが電気を使って数学的な仕事を行い、その役に立つ計算の成果がコンピュートです。田んぼが米を育てるように、データセンターはコンピュートを生み出します。',
      evidence: ['土地 → 設備 → 電力 → プロセッサ → ソフトウェア → 役に立つ計算', 'これは説明の比喩です。農地をデータセンターへ転用するという意味ではありません。'],
      link: { label: 'AIの田んぼをもっと知る', href: '#proposal' },
    },
    {
      id: 'cogdc', kicker: '04 · COMMUNITY FIRST', visual: 'cogdc',
      proposition: 'なぜ、その熱を捨てるのか。',
      number: '約1 MW', numberLabel: '最初の検証規模。契約・許認可済み容量ではありません。',
      explanation: 'COG DCはCOMMUNITY-OWNED GREEN DATA CENTER。ここで生み出すのは、そこで働く人とプロジェクトが使う、私たちのCOG DCコンピュートです。需要、工学、経済性を確かめ、実際の利用が成長を正当化するときだけ広げます。',
      evidence: ['電力 → COG DC → コンピュート + 回収可能な熱 → 地域', '温泉、建物給湯、既存の冬季道路融雪需要、農業などへの熱利用は、温度・距離・年間需要を技術検証します。', 'COG DC設備は温泉棟とは別に配置する構想です。'],
      link: { label: 'COG DC計画を見る', href: 'https://pc.yumori.info' },
    },
    {
      id: 'building', kicker: '05 · THE FOUNDUP LADDER', visual: 'floors',
      proposition: '若者を残す。アイデアを育てる。会社を、ここでつくる。',
      explanation: '下層は温泉・地域・教育・展示・ロボティクス・イベント。3階は有望な学生と初期FoundUpの小さなプロジェクトスタジオ。実用性と実行力を示したプロジェクトは最上階へ進み、独立したAIネイティブ事業を目指します。',
      evidence: ['IDEA → PROJECT → FOUNDUP → VALIDATED FOUNDUP → INDEPENDENT AI-NATIVE BUSINESS', '3階・最上階は通常の賃貸オフィスではありません。選抜、検証、成長の環境です。', '参加者はプロジェクトの運営モデルに沿って、私たちのCOG DCコンピュートへ直接アクセスします。', '階用途は耐震・設備・消防・法令調査と関係者協議で変わります。'],
      link: { label: 'FoundUpsの基盤を見る', href: 'https://github.com/FOUNDUPS/Foundups-Agent' },
    },
    {
      id: 'economies', kicker: '06 · CONNECTED ECONOMIES', visual: 'ecosystem', image: '/satellite-view.jpeg',
      alt: '旧施設、別棟COG DC、周辺土地をつなぐ配置構想イメージ',
      proposition: '一つの資産。いくつもの経済。',
      number: '129,649人', numberLabel: '2018年度利用実績（VERIFIED）',
      explanation: '温泉、COG DC、FoundUps、学生、大学、農業、製造、来訪者、食、イベント、地域雇用を、一つの拠点で短くつなぎます。価値は一つの事業だけでなく、地域内で循環する複数の活動から生まれます。',
      evidence: ['建設時公表費 46.8億円（VERIFIED）。', 'COG DC初期構想 約1 MW（PROJECT VISION）。', '売上、利益、雇用、税収、投資収益は検証前のため掲載しません。'],
      link: { label: '経済効果の検証を見る', href: '#story' },
    },
    {
      id: 'fukui-builds', kicker: '07 · LOCAL PROBLEM TO COMPANY', visual: 'agriculture', image: '/yumori-autonomous-agriculture.png',
      alt: '福井の農家と学生が自律農機やドローンを田んぼで検証する構想イメージ',
      proposition: '福井は、自分たちのコンピュートで何をつくるのか。',
      explanation: 'COG DCは、コンピュートが生産活動になるときに役立ちます。農家が課題を定義し、学生とFoundUpsがAIと私たちのCOG DCコンピュートで試作し、実際の田んぼで確かめます。',
      evidence: ['地域課題 → 学生 / FoundUp → AI + COG DC → 試作 → 現場検証 → 解決策 → 会社', '自律農機、ドローン、画像認識、作物監視、小型除草ロボットは可能性であり、導入済み設備ではありません。'],
      link: { label: '福井のAI・ロボティクス候補を見る', href: '#yumori-outreach' },
    },
    {
      id: 'japan', kicker: '08 · FUKUI AS A PROTOTYPE', visual: 'japan',
      proposition: 'もし、それぞれの地域が、自分たちのコンピュートを育てられたら。',
      explanation: '福井は、全国展開が決まった拠点ではなく、検証するためのプロトタイプです。学校、地域施設、公衆浴場・温泉など、条件の合う遊休公共資産で、巨大拠点を補完する地域中心のコンピュートが可能かを問います。',
      evidence: ['全国展開、他自治体の参加、拠点数は未決定です。', '再利用には建物、安全、電力、通信、熱需要、土地、運営主体の個別検証が必要です。'],
      link: { label: '福井の未来を見る', href: '/future' },
    },
    {
      id: 'festival', kicker: '09 · CULTURE AFTER DARK', visual: 'festival', image: '/campaign-phase-2.jpg',
      alt: 'D-Kを想起させる光で旧施設を文化拠点にする提案イメージ',
      proposition: '毎夜、違う風景。',
      explanation: '提案するD-K / Digital Kakejikuは、残した建物を変化する光の文化拠点へ変えます。温泉、光、祭り、地域の食、夜の来訪、起業をつなぎ、技術施設だけではない「場所」をつくります。',
      evidence: ['D-Kの実績は公式資料で確認できます。', '長谷川章氏が本計画へ参加を確約した事実はありません。現在は提案段階です。'],
      link: { label: 'D-K公式サイトを見る', href: 'https://www.digital-kakejiku.com/' },
    },
    {
      id: 'join', kicker: '10 · BECOME A YUMORI', visual: 'people', image: '/campaign-phase-1.jpg',
      alt: '九頭竜と温泉の未来を守るYUMORI市民キャンペーンのビジュアル',
      proposition: '建物は、まだ立っている。選択肢も、まだ残っている。',
      number: '湯守になる。', numberLabel: '寄付不要・金銭的義務なし・運営責任なし',
      explanation: 'YUMORIに加わるとは、温泉を守り、解体の前に再利用の可能性を調べる努力の守り手・支援者になることです。準備委員会は、人と知識を集め、不可逆な解体と代案を比較できる状態をつくります。',
      evidence: ['現在の組織は準備委員会です。', '登録は寄付、投資、契約、運営責任の引受けではありません。', '本人の許可なく登録名を公開しません。'],
      link: { label: 'YUMORI.meで湯守になる', href: 'https://yumori.me' },
    },
  ],
};

export const yumoriEn: YumoriPresentationCopy = {
  label: 'YUMORI / PROJECT ESINGULARITY — TEN-SLIDE PRESENTATION',
  title: 'Compare the futures before demolition.',
  controls: { previous: 'Previous', next: 'Next', pause: 'Pause autoplay', play: 'Start autoplay', details: 'Learn more', close: 'Close', slide: 'Slide' },
  slides: yumoriJa.slides.map((slide, index) => ({ ...slide, ...[
    { alt: 'Concept image connecting an onsen, local food, and people gathering at night', proposition: 'Can compute save this onsen, revitalize this community, and help reshape Japan?', explanation: 'The building is still standing. Demolition is irreversible. A reuse proposal now connects onsen, learning, work, and culture.', evidence: ['The current organization is a preparatory committee.', 'Reuse depends on building, systems, land, and commercial studies.'], link: { label: 'See the plan and civic decision', href: '#city-action' } },
    { alt: 'Existing campaign material comparing the economic choice between preservation and demolition', proposition: 'Before demolishing it, have we measured the value of this asset?', numberLabel: 'Reported estimate in a council question document—not a budget or contract.', explanation: 'FY2018 recorded 129,649 users. Direct spending of ¥129.6M–¥719.0M per year is a MODELLED screening range, not a forecast.', evidence: ['VERIFIED: 129,649 FY2018 users.', 'REPORTED: about ¥1.58B demolition estimate; not a budget or contract.', 'MODELLED: ¥129.6M–¥719.0M annual direct spending; excludes multipliers, jobs, and tax.', 'PROJECT RANGE: reuse versus equivalent new build difference of about ¥1.1B–¥1.5B; no contractor quote yet.'], link: { label: 'See economic evidence and method', href: '#story' } },
    { alt: 'Concept image transitioning from a Fukui rice field to a small compute facility', proposition: 'A data center is a field that grows compute.', explanation: 'AI does not think for free. Processors use electricity to perform mathematical work. The useful result is compute—grown conceptually as a field grows rice.', evidence: ['Land → equipment → electricity → processors → software → useful computation', 'This is an explanatory metaphor, not a proposal to convert farmland.'], link: { label: 'Learn about the AI rice field', href: '#proposal' } },
    { proposition: 'Why throw that heat away?', numberLabel: 'Initial validation scale—not contracted or permitted capacity.', explanation: 'COG DC means Community-Owned Green Data Center. It produces our COG DC compute for the people and projects working there. Start small, validate demand, engineering, and economics, and grow only when use justifies it.', evidence: ['Energy → COG DC → compute + recoverable heat → community', 'Onsen, hot water, buildings, existing winter road snow-melting demand, and agriculture require engineering validation.', 'COG DC infrastructure is proposed separately from the onsen building.'], link: { label: 'See the COG DC plan', href: 'https://pc.yumori.info' } },
    { proposition: 'Keep the youth. Grow the ideas. Build the companies here.', explanation: 'Public and community uses occupy the lower levels. The third floor develops promising students and early FoundUps. Validated projects can progress to the top floor and toward independent AI-native businesses.', evidence: ['IDEA → PROJECT → FOUNDUP → VALIDATED FOUNDUP → INDEPENDENT AI-NATIVE BUSINESS', 'These floors are a selective development environment, not ordinary tenancy.', 'Participants access our COG DC compute through the project operating model.', 'Uses may change after structural, systems, fire, legal, and stakeholder review.'], link: { label: 'Explore the FoundUps foundation', href: 'https://github.com/FOUNDUPS/Foundups-Agent' } },
    { alt: 'Concept site plan connecting the retained facility, separate COG DC, and surrounding land', proposition: 'One asset. Multiple economies.', numberLabel: 'FY2018 attendance (VERIFIED)', explanation: 'Onsen, COG DC, FoundUps, students, universities, agriculture, manufacturing, visitors, food, events, and local work become a short, connected loop.', evidence: ['Original published construction cost: ¥4.68B (VERIFIED).', 'Initial COG DC concept: about 1 MW (PROJECT VISION).', 'Revenue, profit, jobs, tax, and investor returns remain unpublished until validated.'], link: { label: 'See the economic validation', href: '#story' } },
    { alt: 'Concept image of a Fukui farmer and students testing autonomous farm equipment and drones', proposition: 'What will Fukui build with its compute?', explanation: 'Farmers define real problems. Students and FoundUps prototype with AI and our COG DC compute, then test in real fields.', evidence: ['LOCAL PROBLEM → STUDENT / FOUNDUP → AI + COG DC → PROTOTYPE → FIELD TEST → SOLUTION → COMPANY', 'Autonomous machinery, drones, vision, monitoring, and weeding robots are possibilities—not installed equipment.'], link: { label: 'See Fukui AI and robotics candidates', href: '#yumori-outreach' } },
    { proposition: 'What if every community could grow its own compute?', explanation: 'Fukui is a prototype, not a guaranteed rollout. The question is whether suitable dormant civic assets can support community-first compute alongside hyperscale infrastructure.', evidence: ['No national deployment, participating municipalities, or site count has been decided.', 'Each reuse requires separate building, safety, power, network, heat-demand, land, and operating review.'], link: { label: 'See Fukui’s future', href: '/future' } },
    { alt: 'Proposal image of the retained facility illuminated as an evolving cultural destination', proposition: 'A different landscape every night.', explanation: 'The proposed D-K / Digital Kakejiku can turn the retained building into an evolving cultural destination connecting onsen, light, festivals, food, evening visitors, and entrepreneurship.', evidence: ['D-K history is documented by official sources.', 'Akira Hasegawa has not committed to this project; this remains a proposal.'], link: { label: 'Visit the official D-K site', href: 'https://www.digital-kakejiku.com/' } },
    { alt: 'Campaign image of people gathering to protect the onsen and its future', proposition: 'The building is still standing. The option still remains.', number: 'Become a YUMORI.', numberLabel: 'No donation, financial obligation, or operational responsibility.', explanation: 'Joining YUMORI means becoming a guardian or supporter of the effort to preserve and investigate the reuse option before irreversible demolition.', evidence: ['The current organization is a preparatory committee.', 'Registration is not a donation, investment, contract, or operating obligation.', 'Names will not be made public without permission.'], link: { label: 'Become a guardian at YUMORI.me', href: 'https://yumori.me' } },
  ][index] })),
};

export const yumoriPt: YumoriPresentationCopy = {
  ...yumoriEn,
  label: 'YUMORI / PROJECT ESINGULARITY — APRESENTAÇÃO EM DEZ SLIDES',
  title: 'Compare os futuros antes da demolição.',
  controls: { previous: 'Anterior', next: 'Próximo', pause: 'Pausar reprodução', play: 'Iniciar reprodução', details: 'Saiba mais', close: 'Fechar', slide: 'Slide' },
  slides: yumoriJa.slides.map((slide, index) => ({ ...slide, ...[
    { alt: 'Imagem conceitual conectando onsen, comida local e pessoas reunidas à noite', proposition: 'A computação pode salvar este onsen, revitalizar esta comunidade e ajudar a transformar o Japão?', explanation: 'O edifício continua de pé. A demolição é irreversível. Uma proposta de reutilização conecta onsen, aprendizagem, trabalho e cultura.', evidence: ['A organização atual é um comitê preparatório.', 'A reutilização depende de estudos do edifício, sistemas, terreno e viabilidade.'], link: { label: 'Ver o plano e a decisão cívica', href: '#city-action' } },
    { alt: 'Material da campanha comparando a escolha econômica entre preservação e demolição', proposition: 'Antes de demolir, medimos o valor deste patrimônio?', numberLabel: 'Estimativa citada em documento de pergunta parlamentar — não é orçamento nem contrato.', explanation: 'No ano fiscal de 2018 foram registrados 129.649 usuários. O gasto direto anual de ¥129,6–719,0 milhões é uma faixa MODELADA para análise, não uma previsão.', evidence: ['VERIFICADO: 129.649 usuários no ano fiscal de 2018.', 'RELATADO: estimativa de demolição de cerca de ¥1,58 bilhão; não é orçamento nem contrato.', 'MODELADO: ¥129,6–719,0 milhões por ano em gasto direto; exclui multiplicadores, empregos e tributos.', 'FAIXA DO PROJETO: diferença de cerca de ¥1,1–1,5 bilhão entre reutilização e nova construção equivalente; ainda sem cotação de empreiteira.'], link: { label: 'Ver evidências econômicas e método', href: '#story' } },
    { alt: 'Imagem conceitual passando de um arrozal de Fukui para uma pequena instalação de computação', proposition: 'Um data center é um campo que cultiva computação.', explanation: 'A IA não pensa de graça. Processadores usam eletricidade para realizar trabalho matemático. O resultado útil é a computação — cultivada, em conceito, como um arrozal cultiva arroz.', evidence: ['Terreno → equipamento → eletricidade → processadores → software → computação útil', 'Esta é uma metáfora explicativa, não uma proposta de converter terras agrícolas.'], link: { label: 'Conhecer o arrozal de IA', href: '#proposal' } },
    { proposition: 'Por que desperdiçar esse calor?', numberLabel: 'Escala inicial de validação — não é capacidade contratada nem licenciada.', explanation: 'COG DC significa Community-Owned Green Data Center. Ele produz nossa computação COG DC para as pessoas e os projetos que trabalham ali. Começamos pequenos, validamos demanda, engenharia e economia e só crescemos quando o uso justificar.', evidence: ['Energia → COG DC → computação + calor recuperável → comunidade', 'Onsen, água quente, edifícios, derretimento de neve nas estradas e agricultura exigem validação de engenharia.', 'A infraestrutura COG DC é proposta separadamente do edifício do onsen.'], link: { label: 'Ver o plano COG DC', href: 'https://pc.yumori.info' } },
    { proposition: 'Manter os jovens. Cultivar as ideias. Construir as empresas aqui.', explanation: 'Os níveis inferiores atendem ao público e à comunidade. O terceiro andar desenvolve estudantes promissores e FoundUps iniciais. Projetos validados avançam ao último andar e a negócios nativos de IA independentes.', evidence: ['IDEIA → PROJETO → FOUNDUP → FOUNDUP VALIDADO → NEGÓCIO NATIVO DE IA INDEPENDENTE', 'Esses andares formam um ambiente seletivo de desenvolvimento, não locação comum.', 'Participantes acessam nossa computação COG DC pelo modelo operacional do projeto.', 'Os usos podem mudar após avaliações estruturais, técnicas, de incêndio, legais e comunitárias.'], link: { label: 'Explorar a base FoundUps', href: 'https://github.com/FOUNDUPS/Foundups-Agent' } },
    { alt: 'Planta conceitual conectando a instalação preservada, o COG DC separado e o terreno ao redor', proposition: 'Um patrimônio. Várias economias.', numberLabel: 'Público no ano fiscal de 2018 (VERIFICADO)', explanation: 'Onsen, COG DC, FoundUps, estudantes, universidades, agricultura, indústria, visitantes, gastronomia, eventos e trabalho local formam um ciclo curto e conectado.', evidence: ['Custo original publicado: ¥4,68 bilhões (VERIFICADO).', 'Conceito inicial de COG DC: cerca de 1 MW (VISÃO DO PROJETO).', 'Receita, lucro, empregos, tributos e retorno ao investidor não serão publicados antes da validação.'], link: { label: 'Ver a validação econômica', href: '#story' } },
    { alt: 'Imagem conceitual de agricultor e estudantes de Fukui testando máquinas agrícolas autônomas e drones', proposition: 'O que Fukui construirá com sua computação?', explanation: 'Agricultores definem problemas reais. Estudantes e FoundUps criam protótipos com IA e nossa computação COG DC e depois testam em campos reais.', evidence: ['PROBLEMA LOCAL → ESTUDANTE / FOUNDUP → IA + COG DC → PROTÓTIPO → TESTE DE CAMPO → SOLUÇÃO → EMPRESA', 'Máquinas autônomas, drones, visão computacional, monitoramento e robôs de capina são possibilidades — não equipamentos instalados.'], link: { label: 'Ver candidatos de IA e robótica em Fukui', href: '#yumori-outreach' } },
    { proposition: 'E se cada comunidade pudesse cultivar sua própria computação?', explanation: 'Fukui é um protótipo, não uma implantação garantida. A pergunta é se patrimônios cívicos ociosos e adequados podem apoiar computação comunitária ao lado de infraestrutura de hiperescala.', evidence: ['Nenhuma implantação nacional, município participante ou número de locais foi decidido.', 'Cada reutilização exige análise específica de edifício, segurança, energia, rede, demanda térmica, terreno e operação.'], link: { label: 'Ver o futuro de Fukui', href: '/future' } },
    { alt: 'Imagem proposta da instalação preservada iluminada como destino cultural em evolução', proposition: 'Uma paisagem diferente todas as noites.', explanation: 'O D-K / Digital Kakejiku proposto pode transformar o edifício preservado em um destino cultural em evolução, conectando onsen, luz, festivais, comida, visitantes noturnos e empreendedorismo.', evidence: ['A história do D-K é documentada por fontes oficiais.', 'Akira Hasegawa não assumiu compromisso com este projeto; continua sendo uma proposta.'], link: { label: 'Visitar o site oficial do D-K', href: 'https://www.digital-kakejiku.com/' } },
    { alt: 'Imagem da campanha com pessoas reunidas para proteger o onsen e seu futuro', proposition: 'O edifício continua de pé. A opção ainda existe.', number: 'Torne-se YUMORI.', numberLabel: 'Sem doação, obrigação financeira ou responsabilidade operacional.', explanation: 'Participar do YUMORI é tornar-se guardião ou apoiador do esforço para preservar e investigar a opção de reutilização antes da demolição irreversível.', evidence: ['A organização atual é um comitê preparatório.', 'O cadastro não é doação, investimento, contrato nem obrigação operacional.', 'Nomes não serão publicados sem autorização.'], link: { label: 'Torne-se guardião em YUMORI.me', href: 'https://yumori.me' } },
  ][index] })),
};

export const yumoriPresentation: Record<YumoriLocale, YumoriPresentationCopy> = { ja: yumoriJa, en: yumoriEn, pt: yumoriPt };
