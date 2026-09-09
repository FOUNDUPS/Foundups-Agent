import { env } from 'cloudflare:workers';
import { handlePublicRequest, type RedDogEnv } from '@/lib/reddog-http';
export const dynamic = 'force-dynamic';
type RouteContext = { params: Promise<{surface:string;operation:string}> };
export async function POST(request: Request, context: RouteContext) {
  const { surface, operation } = await context.params;
  return handlePublicRequest(request,surface,operation,env as unknown as RedDogEnv);
}
export const OPTIONS = POST;
