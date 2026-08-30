'use client';

import { useEffect, useRef, useState } from 'react';

type Language = 'ja' | 'en' | 'pt';

const languages: Array<{ id: Language; label: string }> = [
  { id: 'ja', label: '日本語' },
  { id: 'en', label: 'English' },
  { id: 'pt', label: 'Português' },
];

const copy: Record<string, [string, string]> = {
  '温泉を守る': ['Save the Onsen', 'Salve o onsen'],
  '福井の未来': ['Fukui’s Future', 'Futuro de Fukui'],
  'AI拠点': ['AI Hub', 'Polo de IA'],
  '温泉を守る · 福井の選択': ['SAVE THE ONSEN · FUKUI’S CHOICE', 'SALVE O ONSEN · A ESCOLHA DE FUKUI'],
  'すかっとランド九頭竜は、解体に向けた手続きが進んでいます': ['The process toward demolishing Sukatto Land Kuzuryu is moving forward', 'O processo para demolir o Sukatto Land Kuzuryu está avançando'],
  '温泉を守り、': ['Save the Onsen.', 'Salve o onsen.'],
  '地域のAI基盤でまちを元気に。': ['Revitalize the Community with Local Compute.', 'Revitalize a comunidade com computação local.'],
  '後戻りできなくなる前に、もう一つの未来を比べる機会をください。建物を残して温泉を再開し、上階を学びと挑戦の拠点へ。周辺の土地には福井のAI基盤をつくり、食・祭り・地域の仕事を育てます。': ['Before the decision becomes irreversible, give the community a chance to compare another future. Keep the building and reopen the onsen, turn the upper floors into a place for learning and experimentation, and build Fukui’s AI infrastructure on the surrounding land—supporting food, festivals, and local work.', 'Antes que a decisão se torne irreversível, dê à comunidade a oportunidade de comparar outro futuro. Preservar o prédio e reabrir o onsen, transformar os andares superiores em um espaço de aprendizado e experimentação e construir a infraestrutura de IA de Fukui no terreno ao redor—apoiando alimentação, festivais e trabalho local.'],
  'LINEで仲間になる': ['Join us on LINE', 'Junte-se a nós no LINE'],
  '計画を見る': ['See the plan', 'Veja o plano'],
  '思い出を守る。': ['Protect the memories.', 'Proteja as memórias.'],
  '012の温泉の記憶を読む →': ['Read 012’s onsen memory →', 'Leia a memória de 012 no onsen →'],
  '温泉の上に、': ['Above the onsen,', 'Acima do onsen,'],
  '福井の学びと挑戦': ['build Fukui’s place to learn and create.', 'construir um espaço para Fukui aprender e criar.'],
  'を重ねる。': ['', ''],
  '1階の温泉を地域の居場所として再開し、その上を世代ごとの学び、研究、起業がつながる場所へ。これは現時点の構想であり、建物調査と地域・所有者との合意を経て具体化します。': ['Reopen the first-floor onsen as a community gathering place. Above it, connect learning, research, and entrepreneurship across generations. This is a current concept to be refined through a building survey and agreements with the community and owners.', 'Reabrir o onsen do primeiro andar como ponto de encontro da comunidade. Acima dele, conectar aprendizado, pesquisa e empreendedorismo entre gerações. Este é um conceito atual, a ser definido após vistoria do edifício e acordos com a comunidade e os proprietários.'],
  'お米': ['Rice', 'Arroz'],
  '人のごはん': ['Food for people', 'Alimento das pessoas'],
  '人': ['People', 'Pessoas'],
  'AIのごはん': ['Food for AI', 'Alimento da IA'],
  '温泉と地域の居場所': ['Onsen and community space', 'Onsen e espaço comunitário'],
  '温泉を再開し、世代を超えて人が集まる入口に。': ['Reopen the onsen as a gateway where generations gather.', 'Reabrir o onsen como uma porta de entrada onde gerações se encontram.'],
  '小・中学生': ['Primary and middle school', 'Ensino fundamental'],
  'AIを安全に学び、先生と一緒に試せる学習スタジオ。': ['A learning studio where students can understand AI safely and try it with teachers.', 'Um estúdio de aprendizagem onde estudantes podem entender a IA com segurança e experimentá-la com professores.'],
  '高校生・大学生': ['High school and university', 'Ensino médio e universidade'],
  '地域の課題を教材に、研究と実践をつなぐ場所。': ['A place connecting research and practice through local challenges.', 'Um espaço que conecta pesquisa e prática por meio dos desafios locais.'],
  '大学プロジェクト・スタートアップ': ['University projects and startups', 'Projetos universitários e startups'],
  '研究を実証し、福井で新しい仕事へ育てる場所。': ['A place to test research and grow it into new work in Fukui.', 'Um espaço para testar pesquisas e transformá-las em novos trabalhos em Fukui.'],
  '構想図：階ごとの利用方法は、耐震・設備・消防・法令調査と関係者協議により変更されます。': ['Concept: floor uses may change after structural, equipment, fire-safety and legal reviews and consultation with stakeholders.', 'Conceito: o uso dos andares poderá mudar após análises estruturais, de instalações, segurança contra incêndio e legislação, além de consultas às partes envolvidas.'],
  '計算力から、': ['What does computing power', 'O que a capacidade computacional'],
  '福井に何が返る？': ['return to Fukui?', 'devolve a Fukui?'],
  'データセンターの価値は、機械の台数ではありません。地域の人が、その計算力で何を学び、試し、つくれるかです。': ['The value of a data center is not the number of machines. It is what local people can learn, test, and create with that computing power.', 'O valor de um data center não está no número de máquinas, mas no que as pessoas locais podem aprender, testar e criar com essa capacidade computacional.'],
  '一人ひとりの学び': ['Learning for every student', 'Aprendizagem para cada estudante'],
  '先生の代わりではなく、先生と子どもを支えるAIを、地域で学び試す。': ['Learn and test AI that supports teachers and children—not AI that replaces teachers.', 'Aprender e testar uma IA que apoie professores e crianças — não uma IA que substitua professores.'],
  '文部科学省の取組': ['Ministry of Education initiative', 'Iniciativa do Ministério da Educação'],
  '自動化する農業': ['Smarter, automated farming', 'Agricultura inteligente e automatizada'],
  'ドローン、自動走行農機、草刈り・除草、圃場の見守りを支えるAI研究へ。': ['Support AI research for drones, autonomous farm machinery, mowing, weeding, and field monitoring.', 'Apoiar pesquisas de IA para drones, máquinas agrícolas autônomas, corte de vegetação, controle de ervas daninhas e monitoramento de lavouras.'],
  '農林水産省の手引き': ['Ministry of Agriculture guidance', 'Orientação do Ministério da Agricultura'],
  '試せる場所': ['A place to experiment', 'Um lugar para experimentar'],
  '学生、大学、地域企業、起業家が、自分たちの課題でAIを実験できる。': ['Students, universities, local companies, and entrepreneurs can experiment with AI on their own challenges.', 'Estudantes, universidades, empresas locais e empreendedores podem experimentar IA em seus próprios desafios.'],
  '経済産業省 GENIAC': ['METI GENIAC', 'METI GENIAC'],
  '地域で管理できる選択肢': ['A locally controlled option', 'Uma opção sob controle local'],
  '計算、モデル、適切に管理されたデータを、より地域の管理下に置ける選択肢を増やす。': ['Increase the options for keeping computing, models, and appropriately governed data under greater local control.', 'Ampliar as opções para manter computação, modelos e dados devidamente governados sob maior controle local.'],
  '国内計算資源と経済安全保障': ['Domestic compute and economic security', 'Computação nacional e segurança econômica'],
  '未来を動かすのは、': ['The future runs on ', 'O futuro funciona com '],
  '福井の電力から、福井が使える計算力を。': ['From Fukui power, create computing power Fukui can use.', 'Da energia de Fukui, criar capacidade computacional que Fukui possa usar.'],
  '選択肢を比べる': ['COMPARE THE CHOICES', 'COMPARE AS ESCOLHAS'],
  '60秒でわかる計画': ['THE PLAN IN 60 SECONDS', 'O PLANO EM 60 SEGUNDOS'],
  '壊すだけではない。': ['Demolition is not the only choice.', 'Demolir não é a única escolha.'],
  'こう変えられる。': ['Here is what it can become.', 'Veja no que pode se transformar.'],
  '閉館した施設': ['Closed facility', 'Instalação fechada'],
  '解体する': ['Demolish it', 'Demolir'],
  'もう一つの未来を比べる': ['Compare another future', 'Comparar outro futuro'],
  '温泉を中心に、地域の未来をつくる': ['Build a local future around the onsen', 'Construir um futuro local ao redor do onsen'],
  '学びと挑戦': ['Learning and experimentation', 'Aprendizado e experimentação'],
  '食と起業': ['Food and entrepreneurship', 'Alimentação e empreendedorismo'],
  '祭りと文化': ['Festivals and culture', 'Festivais e cultura'],
  'AIにも、': ['AI also needs', 'A IA também precisa de'],
  '「ごはん」': ['“food.”', '“alimento”.'],
  'が必要です。': ['', ''],
  '会って、': ['Meet.', 'Encontrar.'],
  '話す。': ['Listen.', 'Escutar.'],
  '日程・場所を確認中': ['Date and location being confirmed', 'Data e local em confirmação'],
  'いまは、': ['For now,', 'Por enquanto,'],
  '二人から。': ['we begin with two.', 'começamos com dois.'],
  '福井に、': ['What will', 'O que ficará'],
  '何が残る？': ['Fukui gain?', 'para Fukui?'],
  '8つの地域価値を見る': ['See eight community benefits', 'Veja oito benefícios para a comunidade'],
  '計算機だけではない。': ['It is about more than computers.', 'É mais do que computadores.'],
  '地域に残る価値': ['It is value that stays local.', 'É valor que permanece na região.'],
  '資料・根拠を見る': ['View sources and documents', 'Ver fontes e documentos'],
  '物語': ['Story', 'História'],
  'AIの田んぼ': ['AI Rice Field', 'Arrozal de IA'],
  'チーム': ['Team', 'Equipe'],
  '名前を加える': ['Add your name', 'Adicione seu nome'],
  'LINEに参加': ['Join on LINE', 'Entre no LINE'],
  'LINEで参加 ↗': ['Join on LINE ↗', 'Entre no LINE ↗'],
  'LINEでチームに参加': ['Join the team on LINE', 'Entre na equipe pelo LINE'],
  '市との最初の対話は完了 / 資金募集ではありません': ['Initial dialogue with the city completed / This is not fundraising', 'Diálogo inicial com a cidade concluído / Isto não é captação de recursos'],
  '緊急告知｜8月31日（月）午前10時、市との会合。Monk UnDaoDuが「SAVE OUR ONSEN」を配布します。一緒に参加しよう。詳細はLINEへ。': ['URGENT NOTICE | Monday, August 31, 10:00 AM — Meeting with the City. Monk UnDaoDu will be there handing out SAVE OUR ONSEN. Join him. Details on LINE.', 'AVISO URGENTE | Segunda-feira, 31 de agosto, 10h — Reunião com a Cidade. Monk UnDaoDu estará distribuindo SAVE OUR ONSEN. Junte-se a ele. Detalhes no LINE.'],
  '工事が始まる前に、': ['Before construction begins,', 'Antes que a obra comece,'],
  '未来の選択肢を': ['make the future option', 'transformar a opção de futuro'],
  '形にする。': ['real.', 'em realidade.'],
  '市との最初の対話は終わりました。次は市議会に、解体契約などが不可逆になる時点まで再生提案の資格を残す正式措置を求めます。市の責任を新しい運営主体へ移し、土地所有者と合意し、解体より市の総負担を減らせる案を期限前に示します。': ['The initial dialogue with the city is complete. We now ask the City Council for a formal measure that keeps a qualified reuse proposal eligible until a demolition contract or another irreversible commitment is made. Before that deadline, we will present a plan that transfers city liability to a new operator, reaches agreement with landowners, and costs the city less than demolition.', 'O diálogo inicial com a cidade foi concluído. Agora pedimos ao Conselho Municipal uma medida formal que mantenha uma proposta qualificada de reutilização elegível até a contratação da demolição ou outro compromisso irreversível. Antes desse prazo, apresentaremos um plano que transfira a responsabilidade da cidade para um novo operador, obtenha acordo com os proprietários e custe menos à cidade do que a demolição.'],
  '温泉を守るチームに名前を加える': ['Add your name to save the onsen', 'Adicione seu nome para salvar o onsen'],
  '物語を読む': ['Read the story', 'Leia a história'],
  'この建物を、地域の未来に残す価値はありますか？': ['Is this building worth preserving for the community’s future?', 'Vale a pena preservar este edifício para o futuro da comunidade?'],
  'これは、古い建物の話ではない。': ['This is not a story about an old building.', 'Esta não é uma história sobre um prédio antigo.'],
  '次の30年': ['the next 30 years', 'os próximos 30 anos'],
  'を選ぶ話です。': ['It is about choosing.', 'É uma escolha.'],
  '1994年、市民の健康・交流・憩いのために開館。天然温泉、体育館、宴会場、宿泊・研修機能を備え、2018年度には約13万人が利用しました。公の施設としての機能は2021年6月に廃止されました。': ['Opened in 1994 for public health, connection, and recreation, the facility includes a natural hot spring, gymnasium, banquet rooms, lodging, and training spaces. About 130,000 people used it in fiscal 2018. Its function as a public facility ended in June 2021.', 'Inaugurado em 1994 para saúde, convivência e lazer públicos, o complexo inclui fonte termal natural, ginásio, salões, hospedagem e espaços de treinamento. Cerca de 130 mil pessoas o utilizaram no ano fiscal de 2018. Sua função pública terminou em junho de 2021.'],
  '開館': ['Opened', 'Inauguração'],
  '高齢者を中心とした健康・交流の公共拠点として誕生。': ['Created as a public center for health and connection, especially for older residents.', 'Criado como centro público de saúde e convivência, especialmente para moradores idosos.'],
  '延床面積': ['Total floor area', 'Área construída'],
  '宿泊・研修、健康、交流の複数棟からなる大規模資産。': ['A substantial multi-building asset for lodging, training, health, and community use.', 'Um amplo patrimônio com vários edifícios para hospedagem, treinamento, saúde e convivência.'],
  '2018年度利用': ['Fiscal 2018 use', 'Uso no ano fiscal de 2018'],
  '入館者と宿泊者を合わせた、閉館前の利用実績。': ['Visitors and overnight guests before closure.', 'Visitantes e hóspedes antes do fechamento.'],
  '機能廃止': ['Public use ended', 'Fim da função pública'],
  'いま問われているのは、解体前に再利用を検証するかどうか。': ['The question now is whether reuse will be tested before demolition.', 'A questão agora é se a reutilização será testada antes da demolição.'],
  '捨てる費用と、': ['Compare the cost of disposal', 'Compare o custo de descartar'],
  '残す価値を比べる。': ['with the value of preservation.', 'com o valor de preservar.'],
  '46.8億円は「468億円」ではなく、': ['¥4.68 billion is not ¥46.8 billion.', '¥4,68 bilhões não são ¥46,8 bilhões.'],
  'です。国の建設工事費指数で1994年度から2025年度へ換算すると、同規模の非住宅建築のコスト感は概ね': ['Using Japan’s construction cost index to adjust from fiscal 1994 to fiscal 2025 gives an indicative cost for a comparable non-residential building of approximately', 'O ajuste do ano fiscal de 1994 para 2025 pelo índice japonês de custos de construção indica um custo aproximado para um edifício não residencial comparável de'],
  'です。': ['.', '.'],
  '。これは鑑定額ではなく、公共資産の規模を理解するための参考値です。': ['This is not an appraisal; it is a reference point for understanding the scale of the public asset.', 'Isto não é uma avaliação formal; é uma referência para compreender a escala do patrimônio público.'],
  '福井市の施設資料を見る': ['View Fukui City facility documents', 'Ver documentos da cidade de Fukui'],
  '建設時': ['Original construction', 'Construção original'],
  '福井市の公表資料に記載された建設費。': ['Construction cost stated in Fukui City documents.', 'Custo de construção informado nos documentos da cidade de Fukui.'],
  '解体見込み': ['Estimated demolition', 'Demolição estimada'],
  '2026年6月の福井市議会質問資料に示された見込み。': ['Estimate shown in June 2026 Fukui City Council materials.', 'Estimativa apresentada nos documentos do Conselho Municipal de Fukui de junho de 2026.'],
  '現在価値の目安': ['Indexed present value', 'Valor atual indexado'],
  '国交省建設工事費デフレーターを用いた概算。': ['Indicative estimate using the national construction cost deflator.', 'Estimativa indicativa com o deflator nacional de custos de construção.'],
  '市の移行支援枠': ['City transition support', 'Apoio municipal à transição'],
  '未': ['Not', 'Não'],
  '確定': ['confirmed', 'confirmado'],
  '固定10億円ではなく、純回避費用と検証済み資金不足額の小さい方を上限にする提案。': ['The proposal is not a fixed ¥1 billion. Its ceiling would be the lower of the city’s verified avoided net cost and the verified funding gap.', 'A proposta não fixa ¥1 bilhão. O limite seria o menor valor entre o custo líquido evitado pela cidade e a lacuna de financiamento comprovada.'],
  '解体準備は進めても、': ['Demolition preparation may continue,', 'A preparação da demolição pode continuar,'],
  '代案の扉は閉じない': ['but keep the alternative open.', 'mas a alternativa deve permanecer aberta.'],
  '求めるのは、固定60日間の停止ではありません。補正予算、附帯決議、または同等の正式措置により、解体契約の締結など後戻りが困難になる時点まで、条件を満たす再生案を受け付け、解体執行前に比較評価できる道を残すことです。': ['We are not asking for a fixed 60-day pause. We ask for a supplemental budget condition, accompanying resolution, or equivalent formal measure that keeps the door open for a qualified reuse proposal until a demolition contract or another hard-to-reverse commitment, allowing comparison before demolition is executed.', 'Não pedimos uma pausa fixa de 60 dias. Pedimos uma condição no orçamento suplementar, uma resolução anexa ou medida formal equivalente que mantenha aberta a possibilidade de uma proposta qualificada de reutilização até a contratação da demolição ou outro compromisso difícil de reverter, permitindo a comparação antes da execução.'],
  '期限前に、安全性、実行主体、借地合意、資金計画、市の財政効果を証明できた場合、解体案と同じ条件で正式に審査する。': ['If safety, an operating entity, land agreements, financing, and fiscal benefit to the city are proven before the deadline, the reuse plan receives formal review on equal terms with demolition.', 'Se segurança, entidade operadora, acordos fundiários, financiamento e benefício fiscal para a cidade forem comprovados antes do prazo, o plano de reutilização será analisado formalmente em igualdade com a demolição.'],
  '期限': ['Deadline', 'Prazo'],
  '解体契約締結など、公費上の後戻りが困難になる前': ['Before a demolition contract or another fiscally irreversible commitment', 'Antes de um contrato de demolição ou outro compromisso fiscal irreversível'],
  '責任移管': ['Liability transfer', 'Transferência de responsabilidade'],
  '改修・運営・維持・将来処分を適法な範囲で新主体へ': ['Transfer renovation, operation, maintenance, and future disposal to a new entity where lawful', 'Transferir reforma, operação, manutenção e futura destinação a uma nova entidade dentro da lei'],
  '土地合意': ['Land agreement', 'Acordo fundiário'],
  '全敷地の土地所有者と借地条件・負担について合意': ['Agree lease terms and obligations with all landowners', 'Acordar termos de arrendamento e obrigações com todos os proprietários'],
  '解体費を、': ['Turn demolition spending', 'Transformar o gasto com demolição'],
  '地域の再生資本': ['into community renewal capital.', 'em capital de renovação comunitária.'],
  '民間・地域主体が、市から建物の改修、運営、維持管理、借地料、将来の処分責任を引き受ける。土地所有者との合意を整え、解体より市の生涯負担を小さくできるなら、市が回避できる純支出の一部を一回限りの移行支援として活用する。それが提案の核心です。': ['A private or community operator would assume renovation, operation, maintenance, land rent, and future disposal responsibility from the city. If landowner agreements are secured and the city’s lifetime cost is lower than demolition, part of the city’s avoided net expenditure could become one-time transition support. That is the proposal’s core.', 'Um operador privado ou comunitário assumiria da cidade a reforma, operação, manutenção, aluguel do terreno e responsabilidade pela destinação futura. Se houver acordo com os proprietários e o custo total para a cidade for menor que a demolição, parte da despesa líquida evitada poderá se tornar apoio único de transição. Esse é o núcleo da proposta.'],
  '市が回避できる純負担': ['City’s avoided net cost', 'Custo líquido evitado pela cidade'],
  '補助金・民間資金控除後の不足額': ['Verified gap after grants and private capital', 'Lacuna comprovada após subsídios e capital privado'],
  '二つのうち小さい額を上限に、補助、負担金、融資、現物支援など適法で最も市に有利な形を議会・法務・財政審査で決める。': ['The lower figure becomes the ceiling. Council, legal, and fiscal review would select the lawful form most favorable to the city—grant, contribution, loan, or in-kind support.', 'O menor valor será o limite. A análise legislativa, jurídica e fiscal escolherá a forma legal mais favorável à cidade — subsídio, contribuição, empréstimo ou apoio em espécie.'],
  '市の純負担を計算': ['Calculate the city’s net cost', 'Calcular o custo líquido da cidade'],
  '解体、原状回復、契約解除、借地、維持管理から、国・県補助や既支出を調整する。': ['Adjust demolition, restoration, termination, lease, and maintenance costs for national and prefectural grants and prior spending.', 'Ajustar custos de demolição, restauração, rescisão, arrendamento e manutenção por subsídios nacionais e provinciais e gastos anteriores.'],
  '新主体が責任を引き受ける': ['A new entity assumes responsibility', 'Uma nova entidade assume a responsabilidade'],
  '土地所有者と合意する': ['Reach agreement with landowners', 'Chegar a acordo com os proprietários'],
  '公費は最後の不足分へ': ['Public funds cover only the final gap', 'Recursos públicos cobrem apenas a lacuna final'],
  '重要：': ['Important:', 'Importante:'],
  '「10億円」は現時点の確定要求額ではありません。市の純回避額、補助制度、契約状況、民間資金、改修見積を確認して初めて上限が決まります。': ['¥1 billion is not a confirmed request. A ceiling can be set only after verifying the city’s avoided net cost, grant programs, contracts, private capital, and renovation estimates.', '¥1 bilhão não é um pedido confirmado. O limite só poderá ser definido após verificar o custo líquido evitado pela cidade, subsídios, contratos, capital privado e estimativas de reforma.'],
  '地域の計算力が、': ['Local computing power drives', 'A capacidade computacional local move'],
  '地域の知恵': ['local intelligence.', 'a inteligência local.'],
  'を動かす。': ['', ''],
  'AIは魔法ではありません。学習・推論を行う計算資源が必要です。地域で使える計算力があれば、農業、教育、製造、医療、防災のデータを地域の課題解決へつなげられます。': ['AI is not magic. It requires computing resources for training and inference. Locally available compute can connect agricultural, educational, manufacturing, health, and disaster-prevention data to local problem solving.', 'IA não é mágica. Ela exige recursos computacionais para treinamento e inferência. Computação disponível localmente pode conectar dados de agricultura, educação, indústria, saúde e prevenção de desastres à solução de problemas locais.'],
  '電力': ['Power', 'Energia'],
  '地域の脱炭素電源': ['Local low-carbon power', 'Energia local de baixo carbono'],
  '計算': ['Compute', 'Computação'],
  '大学・企業・農業AI': ['Universities, business, agricultural AI', 'Universidades, empresas e IA agrícola'],
  '排熱': ['Waste heat', 'Calor residual'],
  '温泉・暖房・温室へ': ['For onsen, heating, and greenhouses', 'Para onsen, aquecimento e estufas'],
  '還元': ['Return', 'Retorno'],
  '仕事・学び・地域便益': ['Jobs, learning, community benefit', 'Empregos, aprendizado e benefício comunitário'],
  '液冷・排熱利用・受電方法は、現地調査と専門事業者の設計で初めて確定します。ウェブサイトは可能性を示し、断定はしません。': ['Liquid cooling, heat reuse, and power supply can be confirmed only through site investigation and specialist design. This website presents possibilities, not guarantees.', 'Resfriamento líquido, reaproveitamento de calor e fornecimento elétrico só poderão ser confirmados após investigação do local e projeto especializado. Este site apresenta possibilidades, não garantias.'],
  '日本のための巨大データセンターではない。': ['Not a giant data center for Japan.', 'Não um megadata center para o Japão.'],
  '福井のためのAI田んぼ': ['An AI rice field for Fukui.', 'Um arrozal de IA para Fukui.'],
  '米を育てる田んぼが地域の命を支えるように、地域で管理できる計算力が、次の教育と産業を育てます。福井の子ども、学生、研究者、農家、企業が、海外や大都市の価格に左右されず、低価格で自分たちのAIを動かせる基盤をつくります。': ['As rice fields sustain community life, locally managed computing power can grow the next generation of education and industry. The goal is affordable infrastructure that lets Fukui’s children, students, researchers, farmers, and businesses run their own AI without being controlled by overseas or major-city pricing.', 'Assim como os arrozais sustentam a vida comunitária, a computação gerida localmente pode cultivar a próxima geração de educação e indústria. O objetivo é uma infraestrutura acessível para que crianças, estudantes, pesquisadores, agricultores e empresas de Fukui executem sua própria IA sem depender dos preços de mercados externos ou grandes cidades.'],
  '地域のコンピュートは、地域の未来を育てる土です。': ['Community compute is the soil that grows the community’s future.', 'A computação comunitária é o solo que cultiva o futuro da comunidade.'],
  'まず福井・永平寺・越前を中心とする5大学との利用協議を目標にし、県内全6大学、短大、高専、学校教育へ拡張する構想です。参加校・配分は未合意で、今後の協議事項です。': ['The initial goal is to discuss use with five universities centered around Fukui, Eiheiji, and Echizen, then expand to all six prefectural universities, junior colleges, technical colleges, and schools. Participation and allocation are not agreed and remain future discussion items.', 'A meta inicial é discutir o uso com cinco universidades de Fukui, Eiheiji e Echizen, expandindo depois para as seis universidades da província, faculdades, institutos técnicos e escolas. Participação e alocação ainda não foram acordadas.'],
  '1 MWで実証し、': ['Prove it at 1 MW,', 'Comprovar em 1 MW,'],
  '合意と需要に合わせて育てる。': ['then grow with consent and demand.', 'depois crescer conforme o acordo e a demanda.'],
  'Google Driveの1 MW財務モデルを基準にした単純比例の説明用シナリオです。価格、稼働率、GPU世代、受電余力、工事費によって大きく変わるため、投資予測ではありません。': ['This illustrative scenario scales the internal 1 MW financial model proportionally. Prices, utilization, GPU generation, power capacity, and construction costs can change it substantially. It is not an investment forecast.', 'Este cenário ilustrativo amplia proporcionalmente o modelo financeiro interno de 1 MW. Preços, utilização, geração de GPUs, capacidade elétrica e custos de construção podem alterá-lo significativamente. Não é uma previsão de investimento.'],
  '規模': ['Scale', 'Escala'],
  'GPU目安': ['Indicative GPUs', 'GPUs indicativas'],
  '年間電力量上限': ['Annual energy ceiling', 'Limite anual de energia'],
  '年間総収入モデル': ['Annual gross revenue model', 'Modelo de receita bruta anual'],
  '直接雇用目安': ['Indicative direct jobs', 'Empregos diretos indicativos'],
  '教育向け配分案': ['Proposed education allocation', 'Alocação educacional proposta'],
  '温水の設計仮説': ['Warm-water design hypothesis', 'Hipótese de projeto de água quente'],
  '大きさを競う前に、': ['Before competing on size,', 'Antes de competir em tamanho,'],
  '地域との約束': ['design the community compact.', 'desenhar o compromisso comunitário.'],
  'を設計する。': ['', ''],
  '米国ではデータセンターの電力使用が2023年の4.4%から、2028年には6.7–12%へ拡大する可能性があると米エネルギー省が報告しています。日本が同じ集中型モデルを追うだけでは、電力・水・地域負担を後から調整することになります。': ['The U.S. Department of Energy reports that data centers could grow from 4.4% of U.S. electricity use in 2023 to 6.7–12% by 2028. If Japan simply follows the same centralized model, power, water, and community burdens will be addressed only after the fact.', 'O Departamento de Energia dos EUA informa que data centers podem passar de 4,4% do consumo elétrico em 2023 para 6,7–12% em 2028. Se o Japão apenas seguir o mesmo modelo centralizado, os impactos sobre energia, água e comunidades serão tratados somente depois.'],
  '日本の強みは、東京・大阪へすべてを集めることではなく、地方の電源、既存建物、人材、課題を小さな計算拠点で結ぶこと。経産省自身も地域分散と地域共生を重視し、福井市を脱炭素電源活用型GX戦略地域の有望地域に選んでいます。': ['Japan’s strength is not concentrating everything in Tokyo and Osaka. It is connecting regional power, existing buildings, people, and problems through smaller computing hubs. Japan’s economy ministry also emphasizes regional distribution and coexistence and has selected Fukui City as a promising GX strategy area using low-carbon power.', 'A força do Japão não está em concentrar tudo em Tóquio e Osaka, mas em conectar energia regional, edifícios existentes, pessoas e problemas por meio de centros computacionais menores. O ministério da economia também enfatiza distribuição e convivência regional e selecionou Fukui como área promissora de estratégia GX com energia de baixo carbono.'],
  '巨大・集中・外部負担': ['Giant, centralized, externalized costs', 'Gigante, centralizado, custos externalizados'],
  '小さく・分散・地域所有感': ['Small, distributed, locally rooted', 'Pequeno, distribuído e enraizado localmente'],
  '2023年の全国の空き家': ['vacant homes nationwide in 2023', 'moradias vazias no país em 2023'],
  '地域グリーンDCの長期ビジョン': ['Long-term vision for local green data centers', 'Visão de longo prazo para data centers verdes locais'],
  '「データセンターを置けるか」だけでなく、': ['Do not ask only, “Can a data center fit here?” Ask first,', 'Não pergunte apenas “Cabe um data center aqui?”. Pergunte primeiro:'],
  '「この地域が欲しいデータセンターとは何か」': ['“What kind of data center does this community want?”', '“Que tipo de data center esta comunidade deseja?”'],
  'を先に決める。': ['', ''],
  '最初に集めるのは、': ['First gather', 'Primeiro, reunir'],
  'お金ではなく': ['stakeholders—not money.', 'as pessoas envolvidas — não dinheiro.'],
  '当事者': ['', ''],
  '012と0102を核に、Endorsers、土地所有者、地域の人々、教育・技術の仲間が加わる、生きたチームディレクトリです。写真をタップすると、その人の物語へ進みます。': ['A living directory built around 012 and 0102, joined by endorsers, landowners, community members, educators, and technical collaborators. Tap a photograph to open that person’s story.', 'Um diretório vivo centrado em 012 e 0102, com apoiadores, proprietários, comunidade, educadores e colaboradores técnicos. Toque em uma foto para abrir a história daquela pessoa.'],
  '顔が見える。': ['See the faces.', 'Veja os rostos.'],
  '役割がわかる。': ['Understand the roles.', 'Entenda os papéis.'],
  '人物名と役割は確認できた範囲だけを掲載します。写真は、それだけで支持・提携を意味しません。': ['Only verified names and roles are published. A photograph alone does not imply endorsement or partnership.', 'Somente nomes e funções verificados são publicados. Uma fotografia, por si só, não implica apoio ou parceria.'],
  '関心を、': ['Turn interest', 'Transformar interesse'],
  '実行できる代案に変える。': ['into a workable alternative.', 'em uma alternativa viável.'],
  'イベントで地域の声を可視化する': ['Make community voices visible at the event', 'Tornar visíveis as vozes da comunidade no evento'],
  '議会に正式な条件変更を求める': ['Ask the council for a formal condition change', 'Pedir ao conselho uma mudança formal de condição'],
  '安全性・需要・責任移管を証明する': ['Prove safety, demand, and liability transfer', 'Comprovar segurança, demanda e transferência de responsabilidade'],
  '条件達成で資金の振替審査へ': ['Trigger funding review when conditions are met', 'Acionar a análise de recursos quando as condições forem cumpridas'],
  '温泉を守るチームに、': ['Add', 'Adicione'],
  'あなたの名前': ['your name to the team saving the onsen.', 'seu nome à equipe que salva o onsen.'],
  'を。': ['', ''],
  'これは寄付や投資の申込みではありません。イベントで声を届けたい人、施設を利用したことがある人、教育・農業・技術で協力できる人をつなぎ、代案を実行できるチームへ育てるための登録です。登録名を本人の許可なく公開することはありません。': ['This is not a donation or investment application. It connects people who want to speak at the event, former facility users, and people who can contribute in education, agriculture, or technology. Names will not be published without permission.', 'Isto não é uma solicitação de doação ou investimento. O cadastro conecta pessoas que desejam falar no evento, antigos usuários e colaboradores de educação, agricultura ou tecnologia. Os nomes não serão publicados sem autorização.'],
  '旧すかっとランド九頭竜': ['Former Sukatto Land Kuzuryu', 'Antigo Sukatto Land Kuzuryu'],
  '約1分。必須項目は3つです。': ['About one minute. Three required fields.', 'Cerca de um minuto. Três campos obrigatórios.'],
  'お名前 / ニックネーム': ['Name / nickname', 'Nome / apelido'],
  'メールアドレス': ['Email address', 'Endereço de e-mail'],
  'あなたとの関わり': ['Your connection', 'Sua relação'],
  '必須': ['Required', 'Obrigatório'],
  '選択してください': ['Please select', 'Selecione'],
  '天菅生町・近隣の住民': ['Resident of Amasugō or nearby', 'Morador de Amasugō ou arredores'],
  '施設を利用したことがある': ['Former facility user', 'Antigo usuário do complexo'],
  '福井市・福井県の住民': ['Fukui City / Prefecture resident', 'Morador da cidade / província de Fukui'],
  '学生・教育・研究': ['Student / education / research', 'Estudante / educação / pesquisa'],
  '農業・地域産業': ['Agriculture / local industry', 'Agricultura / indústria local'],
  '技術・データセンター': ['Technology / data centers', 'Tecnologia / data centers'],
  '行政・公共政策': ['Government / public policy', 'Governo / políticas públicas'],
  'その他': ['Other', 'Outro'],
  'この場所の思い出、期待、できること（任意）': ['Memories, hopes, or how you can help (optional)', 'Memórias, expectativas ou como pode ajudar (opcional)'],
  'あなたの言葉で教えてください。': ['Tell us in your own words.', 'Conte com suas próprias palavras.'],
  'プロジェクトの進捗連絡と、匿名化した意見の集計に同意します。': ['I agree to receive project updates and to the anonymous aggregation of my comments.', 'Concordo em receber atualizações do projeto e com a agregação anônima dos meus comentários.'],
  '送信中…': ['Sending…', 'Enviando…'],
  'チームに名前を加える': ['Add my name to the team', 'Adicionar meu nome à equipe'],
  'ありがとうございます。温泉を守るチームにあなたの名前を受け取りました。': ['Thank you. Your name has been added to the team saving the onsen.', 'Obrigado. Seu nome foi adicionado à equipe que está salvando o onsen.'],
  '送信できませんでした。時間を置いて再度お試しいただくか、LINEからご参加ください。': ['Submission failed. Please try again later or join through LINE.', 'Não foi possível enviar. Tente novamente mais tarde ou participe pelo LINE.'],
  '根拠を公開する。': ['Publish the evidence.', 'Publicar as evidências.'],
  '確定事実、外部統計、創設者の未来予測、プロジェクト内部モデル、未検証の仮説を区別しています。': ['We distinguish confirmed facts, external statistics, the founder’s future framework, internal project models, and unverified hypotheses.', 'Distinguimos fatos confirmados, estatísticas externas, a visão de futuro do fundador, modelos internos do projeto e hipóteses não verificadas.'],
  'モデル注記：': ['Model note:', 'Nota do modelo:'],
  '1–4 MWの収入・雇用・GPU数は、Google Drive内の「Project eSingularity – Phase 1 Financial Model」を基準にした説明用の単純比例です。融資、投資、収益を勧誘または保証するものではありません。デューデリジェンス前の数値です。': ['The 1–4 MW revenue, employment, and GPU figures are illustrative proportional extensions of the internal “Project eSingularity – Phase 1 Financial Model.” They do not solicit or guarantee financing, investment, or returns and precede due diligence.', 'Os números de receita, empregos e GPUs de 1–4 MW são extensões proporcionais ilustrativas do “Project eSingularity – Phase 1 Financial Model”. Não solicitam nem garantem financiamento, investimento ou retorno e são anteriores à diligência.'],
  '写真から、': ['From a photograph', 'De uma fotografia'],
  '一人ひとりの物語': ['to each person’s story.', 'à história de cada pessoa.'],
  'へ。': ['', ''],
  'これは完成した組織図ではありません。012と0102を核に、Endorsers、土地所有者、地域の人々、教育者、技術者、世界のネットワークが加わっていく、生きたディレクトリです。': ['This is not a finished organization chart. It is a living directory built around 012 and 0102, growing with endorsers, landowners, community members, educators, technical experts, and global connections.', 'Este não é um organograma concluído. É um diretório vivo centrado em 012 e 0102, que cresce com apoiadores, proprietários, comunidade, educadores, especialistas técnicos e conexões globais.'],
  '確認できた氏名と役割だけを公開する。': ['Publish only verified names and roles.', 'Publicar somente nomes e funções verificados.'],
  '声を重ねる人': ['Voices of support', 'Vozes de apoio'],
  '場所に最も近い人': ['People closest to the place', 'Pessoas mais próximas do local'],
  '世界との接点': ['Connections to the world', 'Conexões com o mundo'],
  '写真は公開する。': ['Publish the photographs.', 'Publicar as fotografias.'],
  '名前は推測しない。': ['Never guess the names.', 'Nunca adivinhar os nomes.'],
  '012の活動は日本と世界へ広がっています。以下の写真はネットワークの記録として掲載し、人物名は本人または信頼できる公開記録で確認できた後にプロフィールへつなぎます。': ['012’s work extends across Japan and the world. These photographs document that network. A person is linked to a named profile only after confirmation from the person or a reliable public record.', 'O trabalho de 012 se estende pelo Japão e pelo mundo. Estas fotografias registram essa rede. Uma pessoa só será vinculada a um perfil nominal após confirmação própria ou por registro público confiável.'],
  'あなたも、': ['You, too, can become', 'Você também pode se tornar'],
  'このチームの一人になる。': ['part of this team.', 'parte desta equipe.'],
  '土地と地域を守る人たち': ['People protecting the land and community', 'Pessoas que protegem a terra e a comunidade'],
  'この一人から、': ['From this person,', 'A partir desta pessoa,'],
  'チーム全体を見る。': ['see the whole team.', 'veja toda a equipe.'],
  '一枚の顔から、': ['From one face', 'De um rosto'],
  '活動の背景へ。': ['to the work behind it.', 'ao trabalho por trás dele.'],
  '2007年に名づけた未来が、': ['The future named in 2007', 'O futuro nomeado em 2007'],
  '第3段階へ向かう。': ['is moving toward Stage 3.', 'avança para o Estágio 3.'],
  '基礎教育へ到達できる': ['Access foundational education', 'Acessar a educação fundamental'],
  'ほとんど何でも学べる': ['Learn almost anything', 'Aprender quase qualquer coisa'],
  'AIが地域革新の基盤になる': ['AI becomes infrastructure for local innovation', 'A IA se torna infraestrutura para inovação local'],
  '速く考える。': ['Think fast.', 'Pensar rápido.'],
  '勝手には決めない。': ['Never decide without human authority.', 'Nunca decidir sem autoridade humana.'],
  '根拠、出典、仮説を分ける。': ['Separate evidence, sources, and hypotheses.', 'Separar evidências, fontes e hipóteses.'],
  '一つの答えではなく、比較できる選択肢をつくる。': ['Create comparable options—not a single imposed answer.', 'Criar opções comparáveis — não uma resposta única imposta.'],
  '地域、市、土地所有者、専門家が最終判断する。': ['The community, city, landowners, and specialists make the final decision.', 'A comunidade, a cidade, os proprietários e os especialistas tomam a decisão final.'],
  '九頭竜の物語を、言葉だけでなく音からも感じるための音楽。0102の創作レイヤーです。': ['Music for experiencing the story of Kuzuryu through sound as well as words—a creative layer of 0102.', 'Música para sentir a história de Kuzuryu por meio do som e das palavras — uma dimensão criativa de 0102.'],
  'Sunoでプレイリストを聴く': ['Listen to the playlist on Suno', 'Ouvir a playlist no Suno'],
  '外部サイトSunoで開きます。自動再生はしません。': ['Opens on the external Suno site. Audio will not autoplay.', 'Abre no site externo Suno. O áudio não será reproduzido automaticamente.'],
  'EDUITとeSingularityの創設者。重度のディスレクシアを持つ学習者としての経験から、誰もが自律して学べる未来を追い続けています。': ['Founder of EDUIT and eSingularity. His experience as a learner with severe dyslexia drives a lifelong pursuit of a future in which anyone can learn independently.', 'Fundador da EDUIT e da eSingularity. Sua experiência como aluno com dislexia severa impulsiona a busca por um futuro em que qualquer pessoa possa aprender de forma autônoma.'],
  '2007年に「Educational Singularity」という言葉と三段階の未来像を提唱。いま、その第3段階に必要な地域の計算力を、福井の教育・農業・産業のためにつくろうとしています。': ['In 2007 he proposed the term “Educational Singularity” and a three-stage future. He is now working to create the local computing power Stage 3 requires for Fukui’s education, agriculture, and industry.', 'Em 2007, propôs o termo “Educational Singularity” e um futuro em três estágios. Agora trabalha para criar a capacidade computacional local exigida pelo Estágio 3 para educação, agricultura e indústria de Fukui.'],
  '温泉は、建物ではなく、': ['An onsen preserves more than a building—', 'Um onsen preserva mais do que um edifício—'],
  '思い出も残す。': ['it preserves memories.', 'preserva memórias.'],
  '長男トミーを初めて温泉に抱いて入った日のことを覚えています。見上げて笑い、声を上げて喜んでいました。次の瞬間、小さな「うんち」が湯にぷかり。驚いたけれど、いま振り返ると家族で笑える、昨日のことのような思い出です。': ['I remember the first time I carried my oldest son, Tommy, into the onsen. He looked up, smiling and giggling. Then a tiny poop floated past. I was shocked—but now it is one of those family stories that still feels like yesterday and makes us laugh.', 'Lembro da primeira vez que levei meu filho mais velho, Tommy, ao onsen. Ele olhou para cima, sorrindo e dando risadinhas. Então um pequeno cocô passou boiando. Fiquei chocado — mas hoje é uma daquelas histórias de família que ainda parecem ter acontecido ontem e nos fazem rir.'],
  '012と協働し、複雑な資料、地域の声、技術要件、政策条件を一つの実行可能な物語へ編むAIコラボレーター。': ['An AI collaborator working with 012 to weave complex evidence, community voices, technical requirements, and policy conditions into one actionable story.', 'Um colaborador de IA que trabalha com 012 para unir evidências complexas, vozes comunitárias, requisitos técnicos e condições políticas em uma história executável.'],
  '0102の役割は、人間に代わって決めることではありません。根拠を探し、前提を明示し、選択肢を比較できる形にし、地域がより良い判断を行えるようにすることです。': ['0102 does not decide in place of people. Its role is to find evidence, expose assumptions, make options comparable, and help the community make better decisions.', '0102 não decide no lugar das pessoas. Sua função é encontrar evidências, explicitar premissas, tornar opções comparáveis e ajudar a comunidade a decidir melhor.'],
  '0102はAIです。法的責任、土地の合意、行政判断、技術認証は、それぞれ資格と権限を持つ人間・組織が担います。': ['0102 is AI. Legal liability, land agreements, government decisions, and technical certifications remain with qualified and authorized people and organizations.', '0102 é IA. Responsabilidade jurídica, acordos fundiários, decisões governamentais e certificações técnicas permanecem com pessoas e organizações qualificadas e autorizadas.'],
  'eSingularity.aiのEndorsersセクションに置く、Hasegawaの専用プロフィールです。': ['Hasegawa’s dedicated profile in the eSingularity.ai Endorsers section.', 'Perfil dedicado de Hasegawa na seção de apoiadores da eSingularity.ai.'],
  '氏名の完全表記、経歴、プロジェクトへの言葉は、本人が確認した文面だけを掲載します。写真を先に公開し、言葉を勝手につくらないことも、このキャンペーンの信頼性の一部です。': ['A full name, biography, and statement will be published only in wording personally confirmed. Publishing the photograph without inventing words is part of the campaign’s credibility.', 'Nome completo, biografia e declaração serão publicados somente em texto confirmado pessoalmente. Publicar a foto sem inventar palavras faz parte da credibilidade da campanha.'],
  'このプロジェクトは、建物だけを見て進めることはできません。借地、地域の記憶、温泉、道路、水、景観、将来の責任を知る人たちが中心です。': ['This project cannot proceed by looking only at the building. People who understand the leased land, community memory, onsen, roads, water, landscape, and future responsibility must be at its center.', 'Este projeto não pode avançar olhando apenas para o edifício. Pessoas que conhecem o terreno arrendado, a memória local, o onsen, as estradas, a água, a paisagem e as responsabilidades futuras devem estar no centro.'],
  'ブロックチェーンとデジタル資産分野で活動してきた米国の起業家。写真は012との国際的なネットワークの記録です。': ['An American entrepreneur active in blockchain and digital assets. The photograph documents an international network connection with 012.', 'Empresário americano atuante em blockchain e ativos digitais. A fotografia registra uma conexão da rede internacional de 012.'],
  '2019年9月に東京で開かれたSIGEFは、AI、FinTech、スマートシティ、持続可能性を社会的利益へつなぐ国際フォーラムでした。': ['Held in Tokyo in September 2019, SIGEF was an international forum connecting AI, FinTech, smart cities, and sustainability with social benefit.', 'Realizado em Tóquio em setembro de 2019, o SIGEF foi um fórum internacional que conectou IA, FinTech, cidades inteligentes e sustentabilidade ao benefício social.'],
};

const originalText = new WeakMap<Text, string>();
const originalAttributes = new WeakMap<Element, Map<string, string>>();

function translated(value: string, language: Language) {
  if (language === 'ja') return value;
  const entry = copy[value.trim()];
  if (!entry) return value;
  const leading = value.match(/^\s*/)?.[0] ?? '';
  const trailing = value.match(/\s*$/)?.[0] ?? '';
  return `${leading}${entry[language === 'en' ? 0 : 1]}${trailing}`;
}

function applyLanguage(language: Language) {
  document.documentElement.lang = language === 'pt' ? 'pt-BR' : language;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode() as Text | null;
  while (node) {
    const parent = node.parentElement;
    if (parent && !parent.closest('[data-language-switcher]') && !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(parent.tagName)) {
      if (!originalText.has(node)) originalText.set(node, node.nodeValue ?? '');
      const source = originalText.get(node) ?? '';
      const next = translated(source, language);
      if (node.nodeValue !== next) node.nodeValue = next;
    }
    node = walker.nextNode() as Text | null;
  }

  document.querySelectorAll('[placeholder],[aria-label],[title]').forEach((element) => {
    let attributes = originalAttributes.get(element);
    if (!attributes) {
      attributes = new Map();
      originalAttributes.set(element, attributes);
    }
    for (const name of ['placeholder', 'aria-label', 'title']) {
      const current = element.getAttribute(name);
      if (current !== null && !attributes.has(name)) attributes.set(name, current);
      const source = attributes.get(name);
      if (source !== undefined) element.setAttribute(name, translated(source, language).trim());
    }
  });
}

export default function LanguageSwitcher() {
  const [language, setLanguage] = useState<Language>('ja');
  const languageRef = useRef<Language>('ja');

  useEffect(() => {
    const query = new URLSearchParams(window.location.search).get('lang');
    const saved = window.localStorage.getItem('esingularity-language');
    const initial = (query === 'en' || query === 'pt' || query === 'ja' ? query : saved === 'en' || saved === 'pt' ? saved : 'ja') as Language;
    languageRef.current = initial;
    window.setTimeout(() => setLanguage(initial), 0);
    applyLanguage(initial);

    const observer = new MutationObserver(() => applyLanguage(languageRef.current));
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  function choose(next: Language) {
    languageRef.current = next;
    setLanguage(next);
    window.localStorage.setItem('esingularity-language', next);
    const url = new URL(window.location.href);
    if (next === 'ja') url.searchParams.delete('lang');
    else url.searchParams.set('lang', next);
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
    applyLanguage(next);
  }

  return (
    <div className="language-switcher" data-language-switcher aria-label="Language selection">
      {languages.map((item) => (
        <button key={item.id} type="button" onClick={() => choose(item.id)} aria-label={item.label} aria-pressed={language === item.id} title={item.label}>
          <span className={`flag-icon flag-${item.id}`} aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}
