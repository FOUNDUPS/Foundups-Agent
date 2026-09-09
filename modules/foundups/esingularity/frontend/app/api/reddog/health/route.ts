import { env } from 'cloudflare:workers';
import { health, type RedDogEnv } from '@/lib/reddog-http';
export const dynamic = 'force-dynamic';
export function GET() { return health(env as unknown as RedDogEnv); }
