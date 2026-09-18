'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { RedDogPublicClient, safeSources } from '../lib/reddog-public-client.js';
import './red-dog-chat.css';

type Language = 'ja' | 'en' | 'pt';
type Message = { role: 'user' | 'bot'; text: string; sources?: Array<{ title: string; url: string }> };
const JOIN_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform';
const words = {
  ja: {
    title: 'Red Dog · 0102', subtitle: '温泉と地域の未来を、一緒に考える',
    intro: '旧すかっとランド九頭竜の再生構想、COG DC、YUMORI.meの活動について質問できます。',
    consent: '質問はOpenRouterを通じてAIサービスに送信されます。個人情報や非公開の情報は入力しないでください。1回のチャットは最大10問、無操作2分・合計10分まで。1日の利用上限もあります。',
    start: '同意してチャットを始める', close: 'チャットを閉じる', end: '終了して会話を消す', check: '接続状況を確認',
    label: 'Red Dogへの質問', placeholder: '温泉の再生計画について質問する…', send: '送信',
    thinking: 'Red Dogが考えています…', connecting: '接続しています…',
    ready: 'あと{n}問。無操作2分・合計10分で終了します。',
    join: '温泉を守る準備委員会に参加する ↗', plan: 'YUMORI.meを見る ↗',
    ended: '終了しました。このページの会話を消去しました。',
    pending: '前の質問を処理中です。少し待ってから接続状況を確認してください。',
    withdrawal: 'このページの会話は消去しました。サーバーでの終了を確認できなかったため、接続は時間切れで終了します。',
    errors: {
      expired: 'チャットは終了しました。再開するには、もう一度開始ボタンを押してください。',
      limited: '利用上限に達しました。時間をおいてお試しいただくか、関連資料をご覧ください。',
      uncertain: '回答を受信できませんでした。質問は再送していません。必要に応じて接続状況を確認し、新しい質問を送信してください。',
      connection: '接続できませんでした。時間をおいて、もう一度お試しください。',
      unavailable: 'チャットを利用できません。関連資料や参加フォームはご覧いただけます。',
      busy: '処理が終わるまでお待ちいただくか、接続状況をご確認ください。',
      input: '2,000文字以内で質問を入力してください。',
    },
  },
  en: {
    title: 'Red Dog · 0102', subtitle: 'A conversation about the onsen’s future',
    intro: 'Ask about the Sukatto Land Kuzuryu renewal proposal, COG DC, and the YUMORI.me working plan.',
    consent: 'Your questions are sent to AI providers through OpenRouter. Avoid private information. Up to 10 questions; 2 minutes idle and 10 minutes total. Daily limits also apply.',
    start: 'Agree and start chat', close: 'Close chat', end: 'End chat & clear', check: 'Check session',
    label: 'Question for Red Dog', placeholder: 'Ask about the onsen renewal plan…', send: 'Send',
    thinking: 'Red Dog is thinking…', connecting: 'Connecting…',
    ready: '{n} questions remaining. Ends after 2 minutes idle or 10 minutes total.',
    join: 'Join the Save Onsen Preparatory Committee ↗', plan: 'Visit YUMORI.me ↗',
    ended: 'Chat ended. Messages cleared from this page.',
    pending: 'The previous question is still processing. Check the session again shortly.',
    withdrawal: 'Messages cleared from this page. The server could not confirm the end; the session will expire automatically.',
    errors: {
      expired: 'This session ended. Start a new chat when you are ready.',
      limited: 'The chat limit has been reached. Please return later or read the project links.',
      uncertain: 'The reply was not received. Your question was not resent. Check the session if needed, then send a new question.',
      connection: 'Could not connect. Please try again when you are ready.',
      unavailable: 'Chat is temporarily unavailable. The project links and committee form remain available.',
      busy: 'Please wait for the current question, or check the session.',
      input: 'Please enter a question of up to 2,000 characters.',
    },
  },
  pt: {
    title: 'Red Dog · 0102', subtitle: 'Uma conversa sobre o futuro do onsen',
    intro: 'Pergunte sobre a proposta de renovação de Sukatto Land Kuzuryu, o COG DC e o plano de trabalho YUMORI.me.',
    consent: 'Suas perguntas são enviadas a serviços de IA pelo OpenRouter. Evite informações privadas. Até 10 perguntas, 2 minutos sem atividade e 10 minutos no total. Há limites diários.',
    start: 'Concordar e iniciar', close: 'Fechar conversa', end: 'Encerrar e limpar', check: 'Verificar sessão',
    label: 'Pergunta para Red Dog', placeholder: 'Pergunte sobre a renovação do onsen…', send: 'Enviar',
    thinking: 'Red Dog está pensando…', connecting: 'Conectando…',
    ready: 'Restam {n} perguntas. Encerra após 2 minutos sem atividade ou 10 minutos no total.',
    join: 'Participar do Comitê Preparatório Save Onsen ↗', plan: 'Visitar YUMORI.me ↗',
    ended: 'Conversa encerrada. Mensagens apagadas desta página.',
    pending: 'A pergunta anterior ainda está sendo processada. Verifique a sessão em instantes.',
    withdrawal: 'Mensagens apagadas desta página. O servidor não confirmou o encerramento; a sessão expirará automaticamente.',
    errors: {
      expired: 'Esta sessão terminou. Inicie uma nova conversa quando quiser.',
      limited: 'O limite de uso foi atingido. Volte mais tarde ou consulte os links do projeto.',
      uncertain: 'A resposta não foi recebida. A pergunta não foi reenviada. Verifique a sessão, se necessário, e envie uma nova pergunta.',
      connection: 'Não foi possível conectar. Tente novamente mais tarde.',
      unavailable: 'Conversa indisponível no momento. Os links e o formulário de participação continuam disponíveis.',
      busy: 'Aguarde a pergunta atual ou verifique a sessão.',
      input: 'Digite uma pergunta de até 2.000 caracteres.',
    },
  },
};

export default function RedDogChat() {
  const [client] = useState(() => new RedDogPublicClient('esingularity', '/api/reddog/public'));
  const [language, setLanguage] = useState<Language>('ja');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [notice, setNotice] = useState('');
  const [state, setState] = useState({ active: false, busy: false, needsStatus: false, remaining: 0 });
  const trigger = useRef<HTMLButtonElement>(null);
  const startButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const copy = words[language];

  useEffect(() => {
    const update = () => {
      const lang = document.documentElement.lang;
      setLanguage(lang.startsWith('en') ? 'en' : lang.startsWith('pt') ? 'pt' : 'ja');
    };
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (open) {
      const target = input.current && !input.current.disabled ? input.current : startButton.current;
      (target && !target.disabled ? target : closeButton.current)?.focus();
    }
  }, [open]);

  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [messages]);

  function sync() {
    setState({ active: !!client.session, busy: client.busy, needsStatus: client.needsStatus, remaining: client.session?.remaining_turns ?? 0 });
  }
  function errorText(error: unknown) {
    const code = error && typeof error === 'object' && 'code' in error ? String(error.code) : 'unavailable';
    return copy.errors[code as keyof typeof copy.errors] || copy.errors.unavailable;
  }
  function ready() { setNotice(copy.ready.replace('{n}', String(client.session?.remaining_turns ?? 0))); }
  function close() { setOpen(false); trigger.current?.focus(); }
  async function start() {
    const pending = client.start(); sync(); setNotice(copy.connecting);
    try { await pending; setMessages([]); ready(); }
    catch (error) { setNotice(errorText(error)); }
    finally { sync(); }
    requestAnimationFrame(() => { if (client.session) input.current?.focus(); });
  }
  async function send(event: FormEvent) {
    event.preventDefault();
    if (!message.trim() || state.busy || !state.active || state.needsStatus || !state.remaining) return;
    const question = message.trim();
    setMessages((previous) => [...previous, { role: 'user', text: question }]); setMessage('');
    const pending = client.send(question); sync(); setNotice(copy.thinking);
    try {
      const data = await pending;
      setMessages((previous) => [...previous, { role: 'bot', text: data.reply, sources: safeSources(data.sources) }]);
      ready();
    } catch (error) {
      if (!(error && typeof error === 'object' && 'code' in error && error.code === 'ended')) setNotice(errorText(error));
    } finally { sync(); }
  }
  async function check() {
    const pending = client.check(); sync();
    try { await pending; if (client.needsStatus) setNotice(copy.pending); else ready(); }
    catch (error) { setNotice(errorText(error)); }
    finally { sync(); }
  }
  async function end() {
    const pending = client.end(); setMessages([]); setMessage(''); sync(); setNotice(copy.ended);
    try { await pending; } catch { setNotice(copy.withdrawal); }
    finally { sync(); }
    requestAnimationFrame(() => startButton.current?.focus());
  }

  const disabled = !state.active || state.busy || state.needsStatus || state.remaining <= 0;
  return <div className="red-dog-chat" data-yumori-localized>
    {open && <section id="red-dog-panel" className="red-dog-panel" role="dialog" aria-labelledby="red-dog-title" onKeyDown={(event) => { if (event.key === 'Escape') { event.preventDefault(); close(); } }}>
      <header className="red-dog-header"><div><h2 id="red-dog-title">{copy.title}</h2><p>{copy.subtitle}</p></div><button type="button" ref={closeButton} onClick={close} aria-label={copy.close}>×</button></header>
      <div className="red-dog-conversation" ref={log} role="log" aria-live="polite" aria-label={copy.title}>
        <p className="red-dog-intro">{copy.intro}</p>
        {messages.map((item, index) => <div key={index} className={`red-dog-message ${item.role}`}><p>{item.text}</p>{item.sources?.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">{source.title} ↗</a>)}</div>)}
      </div>
      <div className="red-dog-controls">
        {!state.active && <div className="red-dog-consent"><p>{copy.consent}</p><button type="button" ref={startButton} onClick={start} disabled={state.busy}>{copy.start}</button></div>}
        <p className="red-dog-notice" role="status">{notice}</p>
        {state.active && <div className="red-dog-session-actions">{state.needsStatus && <button type="button" onClick={check} disabled={state.busy}>{copy.check}</button>}<button type="button" onClick={end}>{copy.end}</button></div>}
        <form onSubmit={send} aria-busy={state.busy}><label htmlFor="red-dog-input">{copy.label}</label><div className="red-dog-input-row"><input id="red-dog-input" ref={input} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={copy.placeholder} maxLength={2000} autoComplete="off" disabled={disabled} /><button type="submit" disabled={disabled || !message.trim()}>{copy.send}</button></div></form>
      </div>
      <footer className="red-dog-links"><a href={JOIN_URL} target="_blank" rel="noopener noreferrer">{copy.join}</a><a href="https://yumori.me" target="_blank" rel="noopener noreferrer">{copy.plan}</a></footer>
    </section>}
    <button type="button" className="red-dog-trigger" ref={trigger} aria-controls="red-dog-panel" aria-expanded={open} onClick={() => { if (open) close(); else setOpen(true); }}><span aria-hidden="true">●</span> Red Dog</button>
  </div>;
}
