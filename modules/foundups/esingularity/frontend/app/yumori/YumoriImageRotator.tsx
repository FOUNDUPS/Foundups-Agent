'use client';

import { useEffect, useState } from 'react';

export type YumoriSlide = {
  src: string;
  alt: string;
  caption?: string;
  href?: string;
};

type Props = {
  slides: readonly YumoriSlide[];
  intervalMs?: number;
  aspectRatio?: string;
  maxHeight?: number;
  objectFit?: 'cover' | 'contain';
  background?: string;
};

export default function YumoriImageRotator({
  slides,
  intervalMs = 5500,
  aspectRatio = '16 / 9',
  maxHeight = 620,
  objectFit = 'cover',
  background = '#111511',
}: Props) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (slides.length < 2) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const timer = window.setInterval(() => {
      setActive((current) => (current + 1) % slides.length);
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [intervalMs, slides.length]);

  if (!slides.length) return null;

  return (
    <figure style={{ margin: 0 }} aria-label="YUMORI image rotation">
      <div
        style={{
          position: 'relative',
          width: '100%',
          aspectRatio,
          maxHeight,
          overflow: 'hidden',
          borderRadius: 22,
          background,
        }}
      >
        {slides.map((slide, index) => {
          const image = (
            <img
              src={slide.src}
              alt={slide.alt}
              loading={index === 0 ? 'eager' : 'lazy'}
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit,
                opacity: index === active ? 1 : 0,
                transition: 'opacity 900ms ease',
              }}
            />
          );

          return slide.href ? (
            <a
              key={`${slide.src}-${index}`}
              href={slide.href}
              aria-label={slide.alt}
              style={{
                position: 'absolute',
                inset: 0,
                opacity: index === active ? 1 : 0,
                pointerEvents: index === active ? 'auto' : 'none',
                transition: 'opacity 900ms ease',
              }}
            >
              {image}
            </a>
          ) : (
            <span
              key={`${slide.src}-${index}`}
              style={{
                position: 'absolute',
                inset: 0,
                opacity: index === active ? 1 : 0,
                pointerEvents: 'none',
                transition: 'opacity 900ms ease',
              }}
            >
              {image}
            </span>
          );
        })}
      </div>

      {slides[active]?.caption ? (
        <figcaption style={{ fontSize: 12, opacity: 0.7, marginTop: 8, minHeight: '2.8em', lineHeight: 1.4 }}>
          {slides[active].caption}
        </figcaption>
      ) : null}

      {slides.length > 1 ? (
        <div style={{ display: 'flex', gap: 7, marginTop: 8 }} aria-label="画像を選択">
          {slides.map((slide, index) => (
            <button
              key={`${slide.src}-dot-${index}`}
              type="button"
              onClick={() => setActive(index)}
              aria-label={`画像 ${index + 1} を表示`}
              aria-pressed={active === index}
              style={{
                width: 28,
                height: 5,
                padding: 0,
                border: 0,
                borderRadius: 999,
                cursor: 'pointer',
                background: 'currentColor',
                opacity: active === index ? 0.9 : 0.28,
              }}
            />
          ))}
        </div>
      ) : null}
    </figure>
  );
}
