'use client';

import { useState } from 'react';

const SHARE_URL = 'https://yumori.info';

export default function CampaignShareButton() {
  const [status, setStatus] = useState('');

  async function shareCampaign() {
    try {
      if (navigator.share) {
        await navigator.share({
          title: '九頭竜を守ろう | YUMORI',
          text: '旧すかっとランド九頭竜を壊す前に、再生案を比べる機会を残してください。',
          url: SHARE_URL,
        });
        setStatus('共有画面を開きました');
      } else {
        await navigator.clipboard.writeText(SHARE_URL);
        setStatus('共有リンクをコピーしました');
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setStatus('共有できませんでした。yumori.infoをコピーしてください。');
    }
  }

  return (
    <div className="campaign-share">
      <button type="button" onClick={shareCampaign}>yumori.infoを共有 <b aria-hidden="true">↗</b></button>
      <span role="status" aria-live="polite">{status}</span>
    </div>
  );
}
