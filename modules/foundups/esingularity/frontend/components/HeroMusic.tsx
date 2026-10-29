'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const DEFAULT_VOLUME = 0.78;

export default function HeroMusic() {
  const audioRef = useRef<HTMLAudioElement>(null);
  const fadeTimerRef = useRef<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const clearFade = useCallback(() => {
    if (fadeTimerRef.current !== null) {
      window.clearInterval(fadeTimerRef.current);
      fadeTimerRef.current = null;
    }
  }, []);

  const fadePause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || audio.paused) return;
    clearFade();
    fadeTimerRef.current = window.setInterval(() => {
      audio.volume = Math.max(0, audio.volume - 0.1);
      if (audio.volume <= 0.02) {
        clearFade();
        audio.pause();
        audio.volume = DEFAULT_VOLUME;
        setIsPlaying(false);
      }
    }, 45);
  }, [clearFade]);

  useEffect(() => {
    const hero = document.getElementById('hero');
    if (!hero) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.12) fadePause();
      },
      { threshold: [0, 0.12] },
    );
    observer.observe(hero);
    return () => {
      observer.disconnect();
      clearFade();
    };
  }, [clearFade, fadePause]);

  async function toggleMusic() {
    const audio = audioRef.current;
    if (!audio) return;
    clearFade();
    if (!audio.paused) {
      audio.pause();
      setIsPlaying(false);
      return;
    }
    audio.volume = DEFAULT_VOLUME;
    try {
      await audio.play();
      setIsPlaying(true);
    } catch {
      setIsPlaying(false);
    }
  }

  return (
    <div className="hero-music">
      <button
        type="button"
        onClick={toggleMusic}
        aria-pressed={isPlaying}
        aria-label={isPlaying ? '0102 MUSICを一時停止 / Pause 0102 MUSIC' : '0102 MUSICを再生 / Play 0102 MUSIC'}
      >
        <span aria-hidden="true">{isPlaying ? 'Ⅱ' : '▶'}</span>
        <strong>0102 MUSIC</strong>
        <small>{isPlaying ? 'PLAYING' : 'PLAY'}</small>
      </button>
      <audio ref={audioRef} src="/audio/9dragonheads.mp3" preload="metadata" onEnded={() => setIsPlaying(false)} />
    </div>
  );
}
