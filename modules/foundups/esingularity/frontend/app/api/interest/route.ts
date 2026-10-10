import { saveCommunityInterest } from '@/lib/db';
import { createInterestHandler } from '@/lib/interest';

export const POST = createInterestHandler(saveCommunityInterest);
