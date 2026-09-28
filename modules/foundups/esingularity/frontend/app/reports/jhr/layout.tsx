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
    images: [{ url: "/yumori-compute-field.webp", width: 1672, height: 941, alt: "福井の田園と地域AI計算基盤を組み合わせたAI田んぼの構想図" }],
  },
  twitter: { card: "summary_large_image", images: ["/yumori-compute-field.webp"] },
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
            <p style={{ fontSize: "1.2rem", maxWidth: 820, opacity: .94 }}>ハイパースケーラー、チャンピオン、AI交番。福井が土地と電力を供給するなら、計算資源とAI時代の価値を誰が持つのか。</p>
            <p>
              <a href="#jhr-002" style={pill}>JHR #002へ ↓</a>
              <a href={EVIDENCE_03} target="_blank" rel="noreferrer" style={pill}>03｜根拠資料</a>
              <a href={YUMORI_ME} target="_blank" rel="noreferrer" style={pill}>YUMORI.me｜参加</a>
              <a href={YUMORI_INFO} target="_blank" rel="noreferrer" style={pill}>YUMORI.info｜資料</a>
            </p>
          </div>

          <figure style={{ margin: 0, background: "#07172d" }}>
            <img src="/yumori-compute-field.webp" alt="福井の田園と地域AI計算基盤を組み合わせたAI田んぼの構想図" style={{ width: "100%", maxHeight: 560, objectFit: "cover" }} />
            <figcaption style={{ padding: "12px 24px 16px", fontSize: ".86rem", color: "#d7e9ff" }}>構想図。AI田んぼは、計算資源を地域の生産基盤として捉える比喩です。実在する建設計画や確定した設備配置を示す画像ではありません。</figcaption>
          </figure>

          <div style={{ padding: "34px clamp(22px,5vw,52px) 46px", color: "#06101c" }}>
            <p><span style={tag}>分析</span>福井のAIインフラ問題は、単に「大きなデータセンターに賛成か反対か」ではありません。福井が土地、電力、地域の合意を提供するとき、計算資源そのものを誰が所有し、誰が使え、そこで生まれる能力と経済価値をどこに残すのかという問題です。</p>

            <h2>ハイパースケーラーは「巨大なAI田んぼ」</h2>
            <p><span style={tag}>公式</span>大和ハウス工業が開発するDPDC印西パークは、8万坪を超える敷地に14棟を計画し、最大1,000MWの電力供給能力を掲げています。これはAI時代の計算資源が、土地・変電・通信を伴う巨大な物理インフラであることを示す一例です。</p>
            <p><span style={tag}>公式</span>福井県は2026年9月2日の知事会見で、大型データセンター誘致を工程表に位置付け、原子力発電所から専用線で直接給電する仕組みについて国に検討を求めたと説明しました。県の公式資料では、2026年3月末時点で県内15基の原子炉のうち7基が再稼働し、県内発電所の総発電量の約84％が原子力由来とされています。</p>
            <p><span style={tag}>公式</span>オプテージも福井県美浜町で、原子力由来100％のCO2フリー電力を使う生成AI向けコンテナ型データセンターを2026年度中に開設する計画を公表しています。</p>
            <p><span style={tag}>分析</span>福井にとって、これは遠い東京や千葉だけの話ではなくなりました。ハイパースケーラーは必要なインフラです。しかし、巨大なAI田んぼを地域に置くことと、その収穫である計算能力を地域が持つことは同じではありません。</p>

            <figure style={{ margin: "34px 0" }}>
              <img src="/yumori-inzai-fukui-comparison.webp" alt="大型データセンター集積の規模を福井の田園で考えるための概念比較図" style={{ width: "100%", height: "auto", borderRadius: 14 }} />
              <figcaption style={{ fontSize: ".86rem", opacity: .76 }}>概念比較図。福井で同規模の計画が決定していることを示すものではありません。土地利用と規模を考えるための視覚資料です。</figcaption>
            </figure>

            <h2>チャンピオン — 地域がAIの「最後の一里」を持つ考え方</h2>
            <p><span style={tag}>一次資料</span>Intelligent Internet（II）は2026年9月、地域の人々が過半を所有する「チャンピオン」という地域AI企業の構想を示しました。IIの設立論文では、地域の購読者・設立メンバー等が過半を保有し、設立時に地域の若者向け信託へ10％、IIへ10％を割り当てる案が示されています。</p>
            <p><span style={tag}>分析</span>チャンピオンが答えようとしているのは、学校、病院、企業、行政、市民へAIを届ける「地域の制度」を誰が持つかという問いです。世界のモデルやクラウドを排除するのではなく、顧客関係、運用知識、統合能力、経済参加を地域側にも残す発想です。</p>

            <h2>AI交番 — 計算資源を地域の近くへ置く物理層</h2>
            <p>AI交番は、小さなハイパースケーラーではありません。学校、大学、行政、農業、製造、起業、地域企業などを、必要な計算資源とエージェントへつなぐ分散ノードです。大規模能力が必要なときは外部クラウドへ接続しながら、地域自身も一定の計算能力を持つことを目指します。</p>
            <p><strong>AI交番は警察権限や住民監視を意味しません。</strong> 日本の交番のように、地域の近くに小さな拠点を分散配置し、大きなネットワークへ接続する構造の比喩です。</p>

            <h2>日本では「廃校 → GPUデータセンター」がすでに始まっている</h2>
            <p><span style={tag}>公式</span>文部科学省の令和6年度調査では、2004年度から2023年度に発生し施設が現存する廃校7,612校のうち、5,661校が活用され、1,951校は未活用でした。</p>
            <p><span style={tag}>事業者一次資料</span>ハイレゾは、佐賀県玄海町の旧有徳小学校を活用した「玄海町データセンター」を2025年8月に運用開始し、香川県綾川町では旧綾上中学校の体育館下を改装したGPUデータセンターを2026年3月3日に開所しました。綾川では校舎部分を地域コミュニティスペースとして活用する計画も公表しています。</p>
            <p><span style={tag}>分析</span>つまり「廃校を計算基盤へ転換できるか」は、日本ではもう純粋な仮説ではありません。福井で問うべきなのは、そこへ教育、地域アクセス、熱利用、事業創出、地域ガバナンスをどう重ねるかです。</p>

            <h2>福井には、すでに調べるべき三つの場所がある</h2>
            <p><span style={tag}>公式</span>福井市は2026年9月15日から、旧下宇坂小学校と旧羽生小学校を令和8年度の財産有効活用民間提案制度の対象として募集しています。</p>
            <p><strong>旧下宇坂小学校：</strong> 広い敷地を生かし、教育、地域利用、防災、研究と計算基盤を組み合わせる候補。電力と業務用光回線の実容量は未確認です。</p>
            <p><strong>旧羽生小学校：</strong> 系統を先に調べる候補。現地では送電・変電設備が近接して見えることを確認しましたが、近いことは受電容量の証明ではありません。接続可能容量、電圧、工期、費用、冗長通信は事業者確認が必要です。</p>
            <p><strong>旧すかっとランド九頭竜：</strong> 人が集まる地域ハブ候補。温泉、教育、起業、研究、飲食・観光と、別系統の計算設備を組み合わせ、工学的に成立する範囲で排熱を浴場、給湯、暖房、融雪、農業へ戻す構想です。福井市による採用や事業承認は決まっていません。</p>

            <h2>容量は「MWありき」で決めない</h2>
            <p>現在のYUMORI / eSingularityモデルは、1MWから20MWへ機械的に拡張する計画ではありません。顧客と地域の需要、サービス単価、必要なGPU・ストレージ・通信量を先に確認し、そこからIT負荷と施設負荷を逆算します。最後に、電力会社、通信事業者、建物条件が実際に許容する規模を確認します。</p>
            <p><span style={tag}>公式</span>国のワット・ビット連携も、電力インフラ上望ましい場所へデータセンターを誘導し、光通信で需要地へつなぐ考え方を示しています。NTTドコモビジネスと東京電力パワーグリッドも2026年8月、液冷式コンテナ型データセンターを複数設置する「コンテナDCパーク」による分散配置の取り組みを公表しました。</p>

            <h2>上は地域ガバナンス、下は事業リスクを分離する</h2>
            <p>YUMORIの現在のPPP/PFI案では、最上位に<strong>「第三セクター型を含む官民連携・地域共創法人候補」</strong>を置く構造を福井市と共同検討します。ただし、市の参加、出資・出捐、議決権、役員、法的形態はYUMORI側が決めるものではなく、市長、市議会、担当部局その他の権限ある機関が正式手続で判断する事項です。</p>
            <p>その下では、計算基盤、温浴、飲食・観光など性質の異なる商業リスクをSPC／SPV・運営会社へ分離します。地域の公共ミッションと、GPU設備の事業融資・技術陳腐化リスクを同じ財布へ無理に入れないためです。</p>

            <h2>福井が選ぶべき問い</h2>
            <p>ハイパースケーラーは日本のAI基盤の一部になります。問題は、それだけでよいかです。福井がAI時代を支える電力と土地を提供するなら、そのメガワットが地域にどれだけの学習能力、研究能力、新しい企業、計算アクセス、運用技術を残すのかまで考える必要があります。</p>
            <p style={{ fontSize: "1.24rem", fontWeight: 900 }}>地域はAI田んぼを「置く場所」になるだけなのか。それとも、その収穫を使い、学び、事業を生み出す側にもなるのか。</p>

            <h2>一次資料</h2>
            <ol>
              <li><a href="https://www.daiwahouse.co.jp/innovation/soh/vol28/index.html" target="_blank" rel="noreferrer">大和ハウス工業｜DPDC印西パーク</a></li>
              <li><a href="https://www.pref.fukui.lg.jp/doc/kouho/kaiken/kaiken20260902.html" target="_blank" rel="noreferrer">福井県｜知事記者会見（2026年9月2日）</a></li>
              <li><a href="https://www.pref.fukui.lg.jp/doc/dengen/gensiryokumieruka01.html" target="_blank" rel="noreferrer">福井県｜原子力発電所立地による効用</a></li>
              <li><a href="https://optage.co.jp/press/2025/press_7.html" target="_blank" rel="noreferrer">オプテージ｜美浜町 生成AI向けコンテナ型データセンター</a></li>
              <li><a href="https://ii.inc/blog/post/champions" target="_blank" rel="noreferrer">Intelligent Internet｜チャンピオン構想</a></li>
              <li><a href="https://thesis.ii.inc/" target="_blank" rel="noreferrer">Intelligent Internet｜AI企業設立論文</a></li>
              <li><a href="https://www.mext.go.jp/a_menu/shotou/zyosei/yoyuu_00002.htm" target="_blank" rel="noreferrer">文部科学省｜廃校施設活用状況実態調査</a></li>
              <li><a href="https://highreso.jp/press/40442/" target="_blank" rel="noreferrer">ハイレゾ｜綾川町GPUデータセンター</a></li>
              <li><a href="https://www.city.fukui.lg.jp/sisei/plan/reform/p073300.html" target="_blank" rel="noreferrer">福井市｜令和8年度 財産有効活用民間提案制度</a></li>
              <li><a href="https://www.enecho.meti.go.jp/about/whitepaper/2025/html/1-2-2.html" target="_blank" rel="noreferrer">資源エネルギー庁｜エネルギー白書2025・ワット・ビット連携</a></li>
              <li><a href="https://www.ntt.com/about-us/press-releases/news/article/2026/0827.html" target="_blank" rel="noreferrer">NTTドコモビジネス／東京電力パワーグリッド｜コンテナDCパーク</a></li>
            </ol>

            <p style={{ marginTop: 34, padding: 18, border: "1px solid #9db6d0", borderRadius: 12 }}><strong>事実境界：</strong> JHRは公開一次資料、事業者資料、現地確認と分析を区別します。旧羽生小周辺の設備が目視できることは受電容量を証明せず、YUMORIの三地点構想は福井市による採用、資金提供、許認可、系統接続を意味しません。</p>
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
