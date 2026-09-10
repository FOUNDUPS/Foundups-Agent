import { env } from 'cloudflare:workers';
import { getChatGPTUser } from '@/app/chatgpt-auth';
import { readMoshPit, type GatewayConfig } from './mosh-pit-gateway';

export async function currentMoshPit() {
  const user = await getChatGPTUser();
  return readMoshPit(user?.userId ?? null, env as unknown as GatewayConfig);
}
