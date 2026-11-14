import Image from 'next/image';
import Link from 'next/link';

export default function Brand({ href = '/' }: { href?: string }) {
  return (
    <Link className="brand" href={href} aria-label="eSingularity.ai home">
      <Image className="brand-logo" src="/eduit-globe-logo.svg" alt="" width={44} height={44} priority />
      <span className="brand-name">eSingularity<small>.ai</small></span>
    </Link>
  );
}
