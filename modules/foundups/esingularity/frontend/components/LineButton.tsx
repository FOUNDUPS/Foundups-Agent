import Image from 'next/image';

const LINE_URL = 'https://line.me/ti/p/baXEozL_Q6';

export default function LineButton() {
  return (
    <a className="header-cta" href={LINE_URL} target="_blank" rel="noreferrer" aria-label="LINEに参加" title="LINEに参加">
      <Image src="/line-brand-icon.png" alt="" width={40} height={40} priority />
    </a>
  );
}
