import type { Metadata } from "next";
import type { ReactNode } from "react";

const YUMORI_ME = "https://yumori.me/";
const YUMORI_INFO = "https://yumori.info/";
const EVIDENCE_03 = "https://docs.google.com/document/d/1yeO6-6_mTLW8QswosVKmCVCHSRgWiacq-7FL7-9clsE/edit";

export const metadata: Metadata = {
  title: "JHR #003｜誰が日本の「AI田んぼ」を持つのか｜eSingularity",
  description: "ハイパースケーラー、地域所有、廃校GPUデータセンター、福井のAI交番を一次資料と現地確認から追う日本語版JHR。",
  openGraph: {
    title: "JHR #003 — 誰が日本の「AI田んぼ」を持つのか",
    description: "福井の土地と電力がAI時代を支えるなら、計算資源と価値を誰が持つのか。ハイパースケーラー、チャンピオン、AI交番を比較する。",
    images: [{ url: "/jhr/jhr-003-ai-rice-fields.svg", width: 560, height: 590, alt: "福井の「いま」と「これから」を対比するAI田んぼ構想図" }],
  },
  twitter: { card: "summary_large_image", images: ["/jhr/jhr-003-ai-rice-fields.svg"] },
};

const pill = { display: "inline-flex", alignItems: "center", gap: 8, padding: "9px 13px", border: "1px solid currentColor", borderRadius: 999, color: "inherit", textDecoration: "none", fontWeight: 850, marginRight: 10, marginBottom: 10 } as const;
const tag = { display: "inline-block", padding: "3px 8px", border: "1px solid currentColor", borderRadius: 999, fontSize: ".78rem", fontWeight: 800, letterSpacing: ".04em", marginRight: 8 } as const;

export default function JhrLayout({ children }: { children: ReactNode }) {
  return (
    <>

      <section id="jhr-003" style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px 8px", lineHeight: 1.78, scrollMarginTop: 96 }}>
        <article style={{ border: "1px solid #173b67", borderRadius: 20, overflow: "hidden", background: "#fbfdff", boxShadow: "0 24px 70px rgba(3,18,38,.14)" }}>
          <div style={{ padding: "36px clamp(22px,5vw,52px) 28px", background: "linear-gradient(145deg,#07172d,#0d2c54)", color: "#f6fbff" }}>
            <p style={{ margin: 0, fontWeight: 900, letterSpacing: ".1em", color: "#70ddff" }}>ジャパン・ハイパースケーラー・レポート / JHR #003 · 2026-09-28</p>
            <p style={{ margin: "10px 0 0", fontSize: ".94rem", opacity: .78 }}>最新号を上に、過去号を下に積み重ねる継続記録</p>
            <h1 style={{ fontSize: "clamp(2.15rem,6vw,4.7rem)", lineHeight: 1.04, margin: "28px 0 18px", letterSpacing: "-.035em" }}>誰が日本の「AI田んぼ」を持つのか</h1>
            <p style={{ fontSize: "1.18rem", maxWidth: 820, opacity: .94 }}>ハイパースケーラー、チャンピオン、AI交番。福井が土地と電力を供給するなら、計算資源とAI時代の価値を誰が持つのか。</p>
            <p>
              <a href="#jhr-002" style={pill}>JHR #002へ ↓</a>
              <a href={EVIDENCE_03} target="_blank" rel="noreferrer" style={pill}>03｜根拠資料</a>
              <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={pill}>YUMORI.me｜参加</a>
              <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={pill}>YUMORI.info｜資料</a>
            </p>
          </div>

          <div style={{ padding: "34px clamp(22px,5vw,52px) 46px", color: "#06101c" }}>
            <p>日本のハイパースケーラー建設はすでに始まり、福井の政策環境も一段進んだ。2026年9月11日、経済産業省は福井県（福井市・小浜市）をGX戦略地域第1弾の「脱炭素電源活用型」として認定した。[S21] これは「データセンター集積型」の認定ではなく、脱炭素電源を核に産業団地と産業クラスターを形成する別類型である。[S3][S21] 千葉県印西市では、大和ハウス工業が8万坪を超える敷地に14棟のデータセンターを計画し、最大1,000MWの電力供給能力を掲げるキャンパスを開発している。[S11] 福井県も大型データセンター誘致を明確に進め、9月2日の知事会見では、原子力発電所から大型データセンターへ専用線で直接給電する仕組みについて、現行制度での可否や必要な規制見直しを国に検討するよう求めている。[S12] オプテージは美浜町で原子力由来100％のCO2フリー電力を使う生成AI向けコンテナ型データセンターを準備している。[S14] 福井にとって、これはもはや遠い地域だけの話ではない。</p>
            <p>福井で見慣れた田んぼ、そば畑、集落と山を結ぶ道路の先に、一棟の倉庫ではなく、24時間電力を消費する巨大なデータホール群が並ぶ光景を想像してみる。ハイパースケーラーは、産業規模の「計算農場」だ。そこで育てるのは米でもそばでもない。AIが学習し、推論し、生成し、検索し、行動するために使う膨大な計算能力である。だから問いは単純だ。福井が土地と電力と地域の合意を提供するなら、その「畑」を誰が所有し、誰が収穫を受け取り、誰がその計算能力を使うために料金を払うのか。</p>
            <p>これは主権の問題でもある。地域にはすでに「地域IP」と呼べるものがある。特許や形式的な知的財産だけではなく、農業、学校、工場、病院、公共サービス、言語、歴史、日々の運用に蓄積された知識そのものだ。その知識を発展させるたびに遠方のプラットフォームから希少な計算資源を借りなければならないなら、福井はインフラを供給しながら、生産能力の主導権を外へ渡すことになりかねない。もう一つの選択肢は、福井自身も一部の計算資源を育てることだ。学生や地域プロジェクトには無償または大幅に低廉な計算資源を、大学やスタートアップには本格的な利用環境を、農業・製造・公共サービスには継続的に働くAIエージェントを提供する。目的は本物の田んぼをAI田んぼに置き換えることではない。AI田んぼを使って、福井の本物の田んぼと、その周囲の地域をより生産的にすることである。</p>

            <figure style={{ margin: "34px 0" }}>
              <img src="/jhr/jhr-003-ai-rice-fields.svg" alt="福井の「いま」と「これから」を対比するAI田んぼ構想図" style={{ width: "100%", height: "auto", borderRadius: 14 }} />
              <figcaption style={{ fontSize: ".86rem", opacity: .76 }}>構想図。福井の田園風景と大規模データセンターの対比を示す。福井で確定した建設計画を示すものではない。</figcaption>
            </figure>

            <h2>Intelligent Internet：チャンピオン</h2>
            <p>2026年9月、Stability AIの創設者・元CEOであるEmad Mostaqueが設立したIntelligent Internet（II）は、「チャンピオン」と呼ぶ地域AI企業の構想を公表した。IIはこれからの移行を「インテリジェンス時代」と表現する。私たちの枠組みでは、同じ移行をeSingularity.ai、すなわち豊富な機械知能が教育、仕事、行政、日常生活の基盤層になる転換として捉えている。IIの発表タイトルは、この課題を端的に表している。「インテリジェンス時代は正しく構築されなければならない」。[S9]</p>
            <p>チャンピオンは、IIが所有の問題に対して示した答えである。最先端モデル、クラウド事業者、インフラ供給者が変わっても、顧客関係、運用記録、統合能力、経済参加を地域に残すことを狙う、地域で設立され広く所有されるAI企業という構想だ。IIの現行設立論文では、地域の人々・組織が過半数の所有を維持し、Intelligent Internetが設立時の持分10％を受け取り、適格な地域の若者向け信託に別の10％を割り当て、将来の新生児世代にも追加持分を割り当てる案が示されている。[S10]</p>
            <p>言い換えれば、チャンピオンが問うのは、AIが学校、病院、企業、行政、市民へ届くための「地域の制度」を誰が所有するのか、ということだ。最先端モデルやハイパースケーラーを拒否する必要はない。必要なのは、地域の制度と地域社会との関係を、地域に対して説明責任を持つ形で残すことである。</p>
            <p>ただし、所有の制度層だけでは十分ではない。AIには実際に動くための計算場所が必要である。</p>

            <h2>AI交番：物理インフラ層</h2>
            <p>日本には、地域に分散した拠点という馴染みのあるモデルがある。交番だ。警察本部は集中していても、交番は住民の近くに、顔の見える拠点を置く。AI交番は、この分散構造の考え方をAIの物理インフラへ応用する。</p>
            <p>AI交番が主に答えるのは、チャンピオンだけでは扱いきれない物理側の問いだ。計算資源はどこで生産されるのか。誰が利用できる価格になるのか。学校、大学、行政、病院、農業、スタートアップ、地域産業とどうつながるのか。AI交番は単なる地域サーバールームでも、小型ハイパースケーラーでもない。計算資源、AIエージェント、地域の各機関を結ぶ分散ノードである。</p>
            <p>日本は、このネットワークを構築するうえで独特の優位性を持つ。必要な物理資産の一部がすでに存在し、しかも再利用モデルはすでに実際に動いている。文部科学省によると、2024年5月1日時点で、2004年度以降に発生し施設が現存する廃校は全国7,612校、そのうち1,951校は未活用だった。[S18] ハイレゾはすでに二つの廃校をGPUデータセンターへ転換している。佐賀県玄海町の旧有徳小学校を活用した玄海町データセンターは2025年8月に運用を開始し、香川県綾川町では旧綾上中学校を活用した綾川町GPUデータセンターが2026年3月3日に開所した。ハイレゾによると、綾川では旧体育館下の空間を計算設備に転換し、校舎部分は地域コミュニティスペースとして活用する計画である。[S19][S20] 「廃校を計算基盤へ転換できるか」は、もはや日本では仮説だけではない。</p>
            <p>一部の処理は今後も最先端モデルやハイパースケーラーを使う。一方、より低コストの地域設備で十分に動く処理もある。目標は、実用的な計算資源の豊かさだ。学生や地域プロジェクトには利用時無償または大幅に低廉な計算資源を、大学やスタートアップには手の届く本格的な能力を、地域課題には常時稼働するAIエージェントを提供する。各AI交番の背後にあるのがAI田んぼ、すなわち地域の計算農場である。本物の米やそばの田畑を置き換えるのではなく、それらと周囲の地域をより生産的にするための計算基盤だ。</p>
            <p>チャンピオンは、地域所有と制度の層を示す。AI交番は、計算資源の生産、アクセス、物理統合の層を加える。この二つを組み合わせると、AIそのものは世界から調達しつつ、それを使う能力と、そこから生まれる価値の意味ある一部を地域に残すという構造が見えてくる。</p>

            <h2>福井には、すでに最初の候補ノードがある</h2>
            <p>これは土地の問いを変える。福井は、計算資源を増やすたびに新しい農地を造成するところからAIの未来を始める必要はない。最初のAI交番候補になり得る建物は、すでに立っている。</p>
            <p>2026年9月15日から、福井市は旧下宇坂小学校と旧羽生小学校について民間による利活用提案を募集し、校舎、体育館、敷地を含めた活用を検討対象としている。[S16] AI交番の構想では、この二つの学校跡地を同じ役割にはしない。旧下宇坂小学校は敷地が広く、教育、地域利用、防災、研究、モジュール型計算基盤を組み合わせる拡張候補である。旧羽生小学校は、まず系統条件を確認する「系統先行」の候補であり、近隣の電力インフラが新たな負荷を実際に支えられるかが重要になる。どちらも校舎・体育館・敷地をすべてサーバー空間へ変えるのではなく、複合的な地域資産として扱う。</p>
            <p>旧羽生小学校では、現地調査で大規模な変電・送電設備がすぐ近くにあることを確認した。この近接性は重要だが、「近い」ことは「使える容量がある」ことを意味しない。電力会社による正式な系統接続確認と、冗長な業務用光回線の調査が先である。旧下宇坂小学校は性格が異なる。より広い敷地があり、教育・地域利用を含む大きなキャンパスへ展開できる余地がある一方、実際の受電余力とキャリア級通信の上限は未確認である。</p>

            <figure style={{ margin: "34px 0" }}>
              <img src="/jhr/jhr-003-hanyu-grid-field.svg" alt="旧羽生小学校周辺で確認した送電・変電設備" style={{ width: "100%", height: "auto", borderRadius: 14 }} />
              <figcaption style={{ fontSize: ".86rem", opacity: .76 }}>現地写真 — 旧羽生小学校付近の送変電設備（2026年9月26日）。設備が近接していることは目視できるが、利用可能容量、設備所有、電圧区分、接続権は未確認である。</figcaption>
            </figure>

            <p>地域ハブ候補は、旧すかっとランド九頭竜の温浴施設である。福井市は過去に同施設を低・未利用財産として民間提案の対象に掲載した実績がある。[S17] YUMORI.me / eSingularity.aiの構想では、すかっとランドを温泉、教育、起業、イノベーションの地域ハブとし、計算設備は別系統として配置する。工学的に成立する用途については、回収可能なサーバー排熱を浴場、給湯、暖房、融雪、農業へ振り向ける。</p>
            <p>これが地域スケールのAI交番である。一つの巨大キャンパスで景観を置き換えるのではなく、地域がすでに知っている場所に、役割の異なる計算ノードを組み込むネットワークだ。</p>

            <h2>基本モデルはすでに実例がある。次は、地域へ賢く展開する</h2>
            <p>福井が「廃校をGPUデータセンターにできるか」そのものを証明する必要はない。日本ではすでに実例がある。AI交番の課題はもっと大きい。個別の再利用案件を、教育、イノベーション、地域アクセス、地域ガバナンスを計算基盤の周囲に加えた、再現可能な地域ネットワークへ発展させることだ。ただし、各ノードは拡張するだけの根拠を自ら示さなければならない。容量を最初にMWで決めるのではなく、顧客・地域需要、サービス構成、採算性から必要な計算量を求め、工学的にIT負荷と施設負荷へ変換し、最後に確認済みの電力、通信、建物条件で実際に導入できる規模を決める。実需要とインフラが正当化した場合だけ拡張する。</p>
            <p>通信も同じ考え方で検証する。専用10Gbpsを初期目標とし、条件が整う場合は40/100Gbpsや物理的に異なる経路へ拡張する。電力、光回線、安全な建物条件、実需要を確保できないサイトは拡張しない。設計を変えるか、候補から外す。いま問うべきなのは「学校がデータセンターになれるか」ではない。AI交番という層によって、その計算資源を周辺の学校、大学、農業、スタートアップ、行政、地域がどれだけ有効に使えるようにできるか、そしてその運用モデルを日本各地へ再現できるかである。</p>

            <h2>YUMORI.me / eSingularity.ai の事業構造</h2>
            <p>地域インフラには資本、顧客、専門的な運営が必要である。そのため現在のYUMORI.me / eSingularity.aiモデルでは、商業的な計算基盤の層と、地域公共目的の層を分離する。</p>
            <p>データセンター設備、電力契約、資金調達、顧客、運営リスクはSPC／SPVまたは関連する運営会社に置く。投資家は商業インフラへ資本を提供し、顧客は計算サービスに対価を支払う。その商業能力の一部を、学生や地域プロジェクト向けの利用時無償または補助付き計算資源へ転換する。具体的な配分は、財務・ガバナンス構造で決定する。</p>
            <p>公共利益の層は別にする。教育、地域アクセス、文化利用、住民参加、長期的な管理責任を担う。公共ミッションは維持する一方、最終的な日本法上の法人形態、市の参加、議決権、福井市との関係は、正式な行政・法的手続によって決定する。</p>
            <p>この分離の目的は明確である。地域ミッションそのものを投資商品にしなくても、商業資本によって計算設備を拡張できる構造にするためだ。</p>
            <p>このモデルは、自治体がGPU運営事業者になることや、計算サービス収益を保証することを前提としない。公共側の参加は、適法な資産利用、公共サービス成果、PPP/PFI構造、監督へ集中できる。商業的な計算基盤リスクは商業層に残す。</p>

            <h2>なぜ今なのか</h2>
            <p>国の方向性を見れば、いま動く理由がある。2023年時点で日本のデータセンターは床面積ベースで約90％が東京・大阪圏に集中していた一方、国の政策は地理的分散と「ワット・ビット連携」、すなわち電力インフラと通信インフラを一体で計画する方向を強めている。[S2][S3] 経済産業省は、今後10年程度でデータセンターの電力需要が約5GW増える可能性を示し、地域によっては系統接続に10年以上を要するケースがあるとしている。[S4]</p>
            <p>市場もすでに適応を始めている。2026年8月、NTTドコモビジネスと東京電力パワーグリッドは、分散配置と新しいAIサーバー需要を想定した「コンテナDCパーク」の取り組みを公表した。[S5] 同時に福井市は、廃校を民間活用提案の対象へ戻している。[S16] いま行うインフラ判断によって、地域の計算基盤が「地域が置き場所を提供するもの」になるのか、「地域が実際に使えるもの」になるのかが変わる。</p>

            <h2>2026年9月：福井のGX政策とAI交番の接点</h2>
            <p>福井の現在地は「ハイパースケーラーに選ばれた」ではない。正確には、福井県（福井市・小浜市）がGX戦略地域の「脱炭素電源活用型」に認定され、同時に県が大型データセンター誘致を加速している、という二つの政策が並行している。[S12][S21] 「データセンター集積型」は電力・通信インフラを効率的に整備してDC集積を核に産業クラスターを形成する別類型である。[S3][S21]</p>
            <p>福井市内では稲津町・荒木新保町の県営産業団地整備が進んでいる。[S22] 旧羽生小学校・旧下宇坂小学校・旧すかっとランド九頭竜は、その認定産業団地そのものではない。GX認定だけで三地点の支援対象、電力確保、行政承認を意味しない。</p>
            <p>YUMORIの政策上の接点は、既存公共資産を使う分散型ノードが福井のGX産業立地・ワット・ビット連携を補完できるかを、PPP/PFI事前相談で正式に確認することにある。確認事項は、県・市GX政策との接続、電力・通信・土地利用・事業者調整のフィージビリティへの組込み、将来の適格事業会社／SPVが設備投資支援を利用できる条件である。</p>
            <p>福井県のAI型データセンター立地補助は投下固定資産額100億円以上、補助率20％、新設上限6億円・増設上限3億円、企業グループ通算上限30億円で、建物を建設するDCが対象、コンテナ型は対象外である。[S23] 現在のHanyu初期モデルはこの規模に達しておらず、初期資金として計上しない。</p>
            <p>国のGX地域共創補助金にはデータセンター設備投資型があり、脱炭素電力利用と電源立地地域への貢献を条件に大規模設備投資を支援する。[S24] これは地域認定とは別の事業者選定型であり、適格事業者、権利、電力調達、需要、投資規模、財務・運営体制の確認が必要である。</p>

            <h2>福井が選ぶべき問い</h2>
            <p>ハイパースケーラーは日本のAI基盤の一部になる。最先端モデル、大規模データセンター、全国規模の電力網、クラウド事業者は必要なインフラだ。しかし、それだけが日本のAI基盤のすべてである必要はない。</p>
            <p>戦略上の問いは、それらの周囲に日本が何を構築するかである。チャンピオンはAIの「最後の一里」を地域が所有する制度モデルを示す。AI交番は、地域での計算資源生産、手の届くアクセス、物理統合を加える。YUMORI.me / eSingularity.aiは、これらの考え方を既存資産の再利用と、商業層・地域公共層を分ける構造へ結びつける。</p>
            <p>地域はAI田んぼの「置き場所」になっても、その収穫を所有できるとは限らない。福井が単に機械を受け入れる地域になるのか、それとも、その機械が生み出す計算能力を使うための制度、人材、企業、アクセスも地域内に育てるのかは、インフラと所有の設計で決まる。</p>
            <p>福井がインテリジェンス時代、すなわちeSingularity.aiが描く転換を電力面から支えるなら、重要なのは何MWを受け入れられるかだけではない。</p>
            <p style={{ fontSize: "1.24rem", fontWeight: 900 }}>そのMWが、福井にどれだけの知能活用能力、人材、研究力、新しい企業を残すのかである。</p>

            <h2>出典と適用範囲</h2>
            <ol>
              <li>[S1] 印西市 — 2026年の印西牧の原東地区における地区計画変更。市が公表する都市計画上の課題と手続を裏付ける資料であり、全国的な反対運動を示すものではない。</li>
              <li>[S2] 資源エネルギー庁／経済産業省 — エネルギー白書2025、DX/GXおよびワット・ビット連携。東京・大阪圏への集中割合と国の政策方向を裏付ける。</li>
              <li>[S3] 経済産業省 — GX戦略地域制度。データセンター集積型、脱炭素電源活用型、脱炭素電源地域貢献型など制度類型の区別を裏付ける。</li>
              <li>[S4] 経済産業省 — データセンター集積に関する課題と方向性。約5GWの需要増加見通しと、一部の系統接続に10年以上を要するケースを裏付ける。</li>
              <li>[S5] NTTドコモビジネス＋東京電力パワーグリッド — 2026年8月27日、コンテナDCパークの取り組み。両社によるデータセンター分散化プロジェクトの一次資料。</li>
              <li>[S6] AWS — 日本のインフラ投資に関する発表。2.26兆円規模の投資計画と、AWS自身によるGDP・雇用効果の試算に関する一次資料。</li>
              <li>[S7] 日本マイクロソフト — 2025年3月27日、国内データセンター拡張。既発表の4,400億円投資計画に基づく拡張の一次資料。</li>
              <li>[S8] Google Japan — 2023年4月13日、印西データセンター開設。施設、1,000億円規模のデジタル・フューチャー構想、地域教育支援に関する一次資料。</li>
              <li>[S9] Intelligent Internet／Emad Mostaque — 「インテリジェンス時代は正しく構築されなければならない」（2026年9月4日）。地域で設立され、広く所有され、AIの「最後の一里」を担う公共利益目的の民間企業としてのチャンピオン構想に関する一次資料。</li>
              <li>[S10] Intelligent Internet — 「AI企業設立論文」（2026年）。地域側の過半所有、IIの設立時持分10％、若者・新生児向け持分の仕組みを含む、チャンピオンの資本・所有構造案に関する一次資料。</li>
              <li>[S11] 大和ハウス工業 — DPDC印西パーク概要。14棟計画、8万坪超の敷地、最大1,000MWの電力供給能力に関する一次資料。</li>
              <li>[S12] 福井県 — 2026年9月2日知事記者会見。県による大型データセンター誘致方針と、原子力発電所からの専用線給電の検討要請に関する一次資料。</li>
              <li>[S13] 福井県 — 原子力発電概要（2026年4月1日更新）。県内15基、再稼働7基、県内発電所総発電量の約84％が原子力由来であることに関する一次資料。</li>
              <li>[S14] オプテージ — 美浜町の生成AI向けコンテナ型データセンター発表。原子力由来100％のCO2フリー電力をGPUサーバーへ供給し、2026年度中の運用開始を計画していることに関する一次資料。</li>
              <li>[S15] 福井県 — 小浜市で計画される30ヘクタール規模の新県営産業団地を掲載した産業用地資料。</li>
              <li>[S16] 福井市 — 令和8年度財産有効活用民間提案制度／廃校施設利活用（2026年9月15日更新）。旧下宇坂小学校と旧羽生小学校が現行の民間提案対象であり、校舎、体育館、敷地を含む利活用が検討対象であることを確認する一次資料。</li>
              <li>[S17] 福井市 — 過去の財産有効活用民間提案制度資料。旧すかっとランド九頭竜が低・未利用財産として民間提案対象に掲載された実績を示す。過去の再利用対象実績を示すだけで、現在の事業承認を意味しない。</li>
              <li>[S18] 文部科学省 — 令和6年度「廃校施設活用状況実態調査」（2024年5月1日時点）。施設が現存する廃校7,612校、活用中5,661校、未活用1,951校に関する一次資料。</li>
              <li>[S19] 株式会社ハイレゾ — 綾川町データセンター開所発表（2026年3月3日）。旧綾上中学校をGPUデータセンターへ再利用し、体育館下を計算設備へ改装、校舎を地域コミュニティスペースとして活用する計画に関する一次資料。</li>
              <li>[S20] 株式会社ハイレゾ — 玄海町データセンター開設資料（2025年）および綾川町開所資料。佐賀県玄海町の旧有徳小学校がGPUデータセンターとして再利用され、2025年8月に運用開始したことを確認する一次資料。</li>
              <li>[S21] 経済産業省 — 2026年9月11日「GX戦略地域（第1弾）を認定しました」。福井県（福井市・小浜市）の脱炭素電源活用型での第1弾認定を確認する一次発表。</li>
              <li>[S22] 福井県／福井市 — 福井市稲津町・荒木新保町の県営産業団地整備・都市計画変更。</li>
              <li>[S23] 福井県企業立地ガイド — 福井県成長産業立地促進補助金・AI型データセンター区分。</li>
              <li>[S24] 経済産業省／GX地域共創補助金事務局 — 脱炭素電源地域貢献型投資促進事業・データセンター設備投資型。</li>
            </ol>

            <h2>公開時の確認事項</h2>
            <p>公開版では、プロジェクト自身が決められる構造は明確に記述しつつ、事実境界を維持する。YUMORI.meの公共利益層については日本法上の最終法人形態を未確定とし、各ノードの受電容量・キャリア級光回線は未確認のままとする。プロジェクト構想と行政承認を区別し、現地目視と電力・通信事業者による正式確認を混同しない。</p>
            <p>号数はeSingularity.aiのJHR公開履歴とLinkedIn公開履歴を照合し、今回のWeb版をJHR #003とする。Web版とLinkedIn版は別の公開工程として扱い、Web公開の完了だけをLinkedIn公開とみなさない。</p>
          </div>
        </article>
      </section>

      <section id="jhr-002" style={{ maxWidth: 960, margin: "0 auto", padding: "48px 24px 8px", lineHeight: 1.78, scrollMarginTop: 96 }}>
        <article style={{ border: "1px solid #173b67", borderRadius: 20, overflow: "hidden", background: "#f8fbff", boxShadow: "0 24px 70px rgba(3,18,38,.14)" }}>
          <div style={{ padding: "36px clamp(22px,5vw,52px) 28px", background: "linear-gradient(145deg,#07172d,#0d2c54)", color: "#f6fbff" }}>
            <p style={{ margin: 0, fontWeight: 900, letterSpacing: ".1em", color: "#70ddff" }}>JAPAN HYPERSCALER REPORT / JHR #002 · 2026-09-14</p>
            <p style={{ margin: "10px 0 0", fontSize: ".94rem", opacity: .76 }}>NEWSLETTER ARCHIVE — 最新号を上に、過去号を下に積み重ねる継続記録</p>
            <h1 style={{ fontSize: "clamp(2.15rem,6vw,4.7rem)", lineHeight: 1.04, margin: "28px 0 18px", letterSpacing: "-.035em" }}>なぜ福井に「AI交番」が必要なのか</h1>
            <p style={{ fontSize: "1.12rem", maxWidth: 780, opacity: .9 }}>AI時代のインフラを、ただ誘致するのか。地域自身も持つのか。福井が巨大ハイパースケーラーだけに依存しないための第三の選択肢。</p>
            <p>
              <a href="#jhr-001" style={pill}>JHR #001へ ↓</a>
              <a href={EVIDENCE_03} target="_blank" rel="noreferrer" style={pill}>03｜根拠資料を読む</a>
              <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={pill}>JOIN YUMORI.me</a>
              <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={pill}>eSingularity / 資料</a>
            </p>
          </div>

          <figure style={{ margin: 0, background: "#07172d" }}>
            <img src="/yumori-inzai-fukui-comparison.webp" alt="大型データセンター用地の規模を福井の田園に重ねた概念比較図" style={{ width: "100%", maxHeight: 500, objectFit: "cover" }} />
            <figcaption style={{ padding: "12px 24px 16px", fontSize: ".84rem", color: "#d7e9ff" }}>JHR visual comparison. 大規模集積のスケールを福井で考えるための概念図。福井で確定した建設計画を示すものではありません。</figcaption>
          </figure>

          <div style={{ padding: "34px clamp(22px,5vw,52px) 46px", color: "#06101c" }}>
            <p><span style={tag}>JAPANESE / PRIMARY</span></p>
            <p><strong>最初に、ハイパースケーラーそのものを敵にしません。</strong> 大規模クラウドと大規模データセンターは、日本のAI、産業、研究を支える重要なインフラです。問題は「来るか、来ないか」だけではありません。土地、電力、計算設備、データ、運営権、そしてAI時代に生まれる経済価値を、誰が所有し、誰が長期的に受け取るのかです。</p>
            <p>巨大データセンターは、大きな設備投資、固定資産税、建設需要、雇用を地域にもたらす可能性があります。一方で、施設の所有者、計算資源、主要顧客、利益配分、意思決定が地域外にある場合、地域が土地と電力を提供するだけで、AI経済の生産資本そのものを持てるとは限りません。<strong>「誘致」と「地域がAI資本を持つこと」は同じではありません。</strong></p>
            <p>だからJHRが問うのは、ハイパースケーラーへの賛否ではありません。日本の地域に、もう一つの選択肢をつくれるかです。</p>

            <h2>AI交番 — 地域が持つ小さなAIインフラ</h2>
            <p>YUMORI / eSingularityが提案するのが、<strong>COGDC — Community-Owned Green Data Center</strong>です。その地域モデルを「AI交番」と呼びます。</p>
            <p>交番は巨大な本部ではありません。地域の近くにあり、日常の需要に応え、必要な時には大きなネットワークにつながる小さな拠点です。AI交番も同じ発想です。</p>
            <p>学校、大学、農業、製造業、中小企業、自治体、研究機関が利用できる地域密着型の計算拠点を、小さく始める。地域自身がAIを学び、地域自身が一定の計算資源を持ち、データの扱いを選択できる能力を育てる。大規模な能力が必要な時には、国内外のクラウドにつなぐ。<strong>世界のクラウドを拒否するのではなく、地域が一方的に依存しない構造をつくる。</strong></p>
            <p><strong>AI交番は警察権限や住民監視システムを意味しません。</strong> 「地域の近くにある、小さく分散した、地域に責任を持つネットワーク拠点」という日本の交番の構造を、AIインフラの比喩として使っています。</p>

            <h2>なぜ旧すかっとランド九頭竜なのか</h2>
            <p>AIはソフトウェアだけでは動きません。半導体、建物、電力、通信、冷却、土地、資本が必要です。つまり、AIは物理インフラです。</p>
            <p>旧すかっとランド九頭竜には、すでに建物があります。温浴設備があります。地域があります。そして、再利用できるかどうかをまだ検証できる段階にあります。新しい土地を造成し、新しい巨大建物を建てる前に、既存の公共資産をAI時代の地域インフラへ転換できるかを調べることには、政策上の意味があります。</p>
            <p>構想は、1MW級から検証を始め、需要と成立性が確認できた場合に段階的に拡張するものです。計算資源を教育、大学・研究、農業、製造、起業、行政などへつなぎ、技術的に成立するならサーバー排熱を温泉、給湯、暖房、融雪、農業などに再利用する。<strong>建物を保存すること自体が目的ではなく、既存資産を新しい生産インフラへ変えられるかを検証することが目的です。</strong></p>

            <h2>9月25日の採決後に何を求めるのか</h2>
            <p>9月25日の採決は終了しました。YUMORIが現在求めているのは、COGDCの自動承認でも、市の出資でも、随意契約でもありません。</p>
            <p><strong>解体を前提とする予算判断を先に確定させないことです。</strong></p>
            <p>成立するかどうかは、技術、構造、アスベスト、電力、通信、資金、収益、運営主体、地域便益を検証しなければ分かりません。だからこそ、再利用案を解体案と同じテーブルに載せ、同じ事実と基準で比較する必要があります。</p>
            <p style={{ fontSize: "1.2rem", fontWeight: 900 }}>解体は後からでもできます。解体した後に、この選択肢を検証することはできません。</p>
            <p><strong>現在：PPP/PFIで比較検証。</strong> 不可逆な解体調達・工事へ進む前に、福井市が官民連携の案件形成ルートを指定し、解体案と再利用案を同じ証拠で比較することを求めています。</p>
            <p>数字、政策整合、技術、法務、PPP/PFI再利用案、予算論点は、<a href={EVIDENCE_03} target="_blank" rel="noreferrer"><strong>公式キャンペーン文書03「解体準備予算反対・支援資料」</strong></a>に集約しています。賛成する前に、反対する前に、まず根拠を確認してください。</p>

            <hr style={{ margin: "50px 0" }} />

            <div lang="en">
              <p><span style={tag}>ENGLISH / SECONDARY</span></p>
              <h2>Why Fukui Needs an AI Koban</h2>
              <p>This is not an argument against hyperscalers. Large cloud and data-center infrastructure are important to Japan. The deeper question is ownership: who owns the land-intensive compute infrastructure, who controls it, and where the long-term economic value of the AI economy accumulates.</p>
              <p>A hyperscale campus can bring major capital investment, construction activity, taxes and jobs. But attracting infrastructure is not the same as a community owning productive AI capital. YUMORI / eSingularity therefore proposes a complementary model: <strong>COGDC — Community-Owned Green Data Center</strong>, with the community-scale node described as an <strong>AI Koban</strong>.</p>
              <p>A koban is not national headquarters. It is a small local node close to the community and connected to a much larger network. An AI Koban follows the same architecture: locally accountable compute, learning and data capability that connects outward to Japanese and global cloud infrastructure when larger capacity is needed.</p>
              <p><strong>AI Koban does not mean police authority or resident surveillance.</strong> It is a structural metaphor for small, distributed infrastructure close to the community.</p>
              <h3>Why test the option before demolition?</h3>
              <p>AI is physical infrastructure. It requires chips, buildings, transmission, cooling, electricity, land and capital. The former Sukatto Land Kuzuryu is an existing physical asset. The question is whether it can be repurposed before Fukui eliminates that option.</p>
              <p>The September 25 vote is complete. YUMORI is not asking Fukui City to automatically approve COGDC, fund an AI Koban, or award a non-competitive contract. It is asking the City to designate a PPP/PFI public-private project-formation route and test reuse against demolition using the same evidence and standards.</p>
              <p style={{ fontSize: "1.2rem", fontWeight: 900 }}>Demolition can happen later. Once demolished, this option cannot be tested.</p>
              <p><strong>Current request: PPP/PFI comparison.</strong> Compare demolition and reuse before irreversible demolition procurement or work proceeds. The supporting economic, policy, technical, legal and PPP/PFI record is collected in <a href={EVIDENCE_03} target="_blank" rel="noreferrer">Campaign Document 03</a>.</p>
            </div>
          </div>
        </article>

        <div id="jhr-001" style={{ marginTop: 58, paddingTop: 28, borderTop: "4px solid #0b2d57", scrollMarginTop: 96 }}>
          <p style={{ fontWeight: 900, letterSpacing: ".08em" }}>ARCHIVE CONTINUES ↓ · JHR #001</p>
          <p style={{ opacity: .72 }}>以下は既存の第1号を保持しています。今後も新しい号をこの上に追加し、JHRの履歴を1本のページで追える構造にします。</p>
        </div>
      </section>
      {children}
    </>
  );
}
