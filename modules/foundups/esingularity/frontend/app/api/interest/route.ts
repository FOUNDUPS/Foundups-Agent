import { saveCommunityInterest } from '@/lib/db';

const allowedRelationships = new Set([
  '天菅生町・近隣の住民',
  '施設を利用したことがある',
  '福井市・福井県の住民',
  '学生・教育・研究',
  '農業・地域産業',
  '技術・データセンター',
  '行政・公共政策',
  'その他',
]);

export async function POST(request: Request) {
  try {
    const body = await request.json() as Record<string, unknown>;
    if (typeof body.website === 'string' && body.website.trim()) {
      return Response.json({ ok: true });
    }

    const name = typeof body.name === 'string' ? body.name.trim() : '';
    const email = typeof body.email === 'string' ? body.email.trim().toLowerCase() : '';
    const relationship = typeof body.relationship === 'string' ? body.relationship.trim() : '';
    const story = typeof body.story === 'string' ? body.story.trim() : '';
    const consent = body.consent === 'yes';

    if (!name || name.length > 80 || !email || email.length > 160 || !/^\S+@\S+\.\S+$/.test(email) || !allowedRelationships.has(relationship) || story.length > 1500 || !consent) {
      return Response.json({ ok: false, error: 'invalid_submission' }, { status: 400 });
    }

    await saveCommunityInterest({ name, email, relationship, story: story || null });
    return Response.json({ ok: true }, { status: 201 });
  } catch {
    return Response.json({ ok: false, error: 'submission_failed' }, { status: 500 });
  }
}
