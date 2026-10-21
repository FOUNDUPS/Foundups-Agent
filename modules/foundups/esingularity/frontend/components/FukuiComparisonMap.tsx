'use client';

import { useRef } from 'react';

// These outlines follow 012's annotated screenshot, not surveyed parcel boundaries.
// No hectares or MW are inferred from screenshot pixels. The original is unmodified.
function MapDrawing() {
  return (
    <svg className="fukui-map-drawing" viewBox="0 0 792 1176" role="img" aria-label="福井・江上町の原図。黄色は温泉の位置、白枠は比較のために指定された仮の範囲。縮尺未検証。">
      <image href="/maps/egamicho-original.jpeg" width="792" height="1176" />
      <path d="M190 108 L269 54 L397 24 L508 33 L548 58 L592 124 L633 219 L675 308 L690 382 L682 485 L657 534 L513 550 L496 352 L229 356 L204 301 Z" fill="white" fillOpacity=".12" stroke="white" strokeWidth="6" strokeDasharray="18 9" />
      <path d="M343 873 L445 869 L461 891 L451 952 L356 950 L344 927 Z" fill="#ffd731" fillOpacity=".38" stroke="#ffd731" strokeWidth="5" />
      <circle cx="400" cy="905" r="23" fill="#ffd731" stroke="#06142d" strokeWidth="3" />
      <text x="400" y="914" textAnchor="middle" fill="#06142d" fontSize="27" fontWeight="900">1</text>
      <circle cx="425" cy="169" r="23" fill="white" stroke="#06142d" strokeWidth="3" />
      <text x="425" y="178" textAnchor="middle" fill="#06142d" fontSize="27" fontWeight="900">2</text>
    </svg>
  );
}

export default function FukuiComparisonMap() {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const previousOverflow = useRef('');

  function open() {
    previousOverflow.current = document.body.style.overflow;
    dialog.current?.showModal();
    document.body.style.overflow = 'hidden';
  }

  return (
    <figure className="fukui-map-panel">
      <div className="fukui-map-heading">
        <span>福井の土地を、どう使う？</span>
        <h2>もし、印西クラスの<br />巨大データセンターが来たら。</h2>
      </div>
      <button ref={trigger} type="button" className="fukui-map-open" onClick={open} aria-label="地図を全画面で見る">
        <MapDrawing />
        <span className="fukui-map-expand">地図を全画面で見る ⛶</span>
      </button>
      <figcaption>
        <p><b className="map-key-yellow">1</b><strong>温泉・COGDC構想の拠点</strong></p>
        <p><b className="map-key-white">2</b><strong>大型施設を仮に置く比較範囲</strong></p>
        <p className="map-caveat">白枠は指定された仮の範囲です。27haの実測図ではなく、この場所での開発計画を示すものでもありません。</p>
        <a href="/reports/jhr#land-area">比較の根拠：印西27ha・仙台7.18ha →</a>
      </figcaption>
      <dialog ref={dialog} className="fukui-map-dialog" aria-label="福井の土地利用・概念比較" onClose={() => { document.body.style.overflow = previousOverflow.current; trigger.current?.focus(); }}>
        <div className="map-dialog-toolbar"><strong>福井の土地利用・概念比較</strong><button type="button" onClick={() => dialog.current?.close()} autoFocus>閉じる ×</button></div>
        <MapDrawing />
        <p>黄色：温泉・COGDC構想の拠点 ／ 白枠：比較範囲（縮尺未検証）</p>
      </dialog>
    </figure>
  );
}
