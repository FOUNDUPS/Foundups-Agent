'use client';

import { useEffect, useState } from 'react';
import { cityMeeting } from '../lib/event';

const message = '緊急告知｜8月31日（月）午前10時、市との会合。Monk UnDaoDuが「SAVE OUR ONSEN」を配布します。一緒に参加しよう。詳細はLINEへ。';

export default function EventAlert() {
  const [isActive, setIsActive] = useState(cityMeeting.status === 'scheduled');

  useEffect(() => {
    const remaining = Date.parse(cityMeeting.alertExpiresAt) - Date.now();
    const timer = window.setTimeout(() => setIsActive(false), Math.max(0, remaining));
    return () => window.clearTimeout(timer);
  }, []);

  if (!isActive) return null;

  return (
    <a className="event-alert" href={cityMeeting.lineUrl} target="_blank" rel="noreferrer" aria-label={message}>
      <div className="event-alert-window" aria-hidden="true">
        <div className="event-alert-track">
          <span>{message}</span>
          <span>{message}</span>
        </div>
      </div>
    </a>
  );
}
