// Server-only: the Claude API key never reaches the browser.
// Checks who is asking, enforces a monthly limit, builds the instructions, and calls Claude.
import { createClient } from '@supabase/supabase-js';
import { cvPrompt, feedbackPrompt, letterPrompt } from '@/lib/prompts';
import { QB } from '@/lib/constants';

export const runtime = 'nodejs';
const LIMIT = Number(process.env.AI_MONTHLY_LIMIT || 30);
const MODEL = process.env.AI_MODEL || 'claude-sonnet-5-5';
const fail = (error: string, status = 400) => Response.json({ error }, { status });

export async function POST(req: Request) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL, anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, key = process.env.ANTHROPIC_API_KEY;
  if (!url || !anon) return fail('The database is not connected yet.', 503);
  if (!key) return fail('AI is not switched on yet: the Claude API key is missing.', 503);
  const token = (req.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!token) return fail('Sign in to use AI features.', 401);

  // A database connection that acts as this student, so the access rules apply.
  const db = createClient(url, anon, { global: { headers: { Authorization: `Bearer ${token}` } }, auth: { persistSession: false } });
  const { data: u } = await db.auth.getUser(token);
  if (!u?.user) return fail('Your session has expired. Sign in again.', 401);

  const body = await req.json().catch(() => ({}));
  const task = String(body.task || '');
  if (!['cv', 'letter', 'feedback'].includes(task)) return fail('Unknown request.');

  const since = new Date(Date.now() - 30 * 864e5).toISOString();
  const { count } = await db.from('ai_usage').select('id', { count: 'exact', head: true }).gte('created_at', since);
  if ((count || 0) >= LIMIT) return fail(`You have used your ${LIMIT} AI requests for this month.`, 429);

  let prompt = '';
  if (task === 'feedback') {
    const q = QB.find(x => x.id === body.questionId); const answer = String(body.answer || '');
    if (!q || !answer.trim()) return fail('Write an answer first.');
    prompt = feedbackPrompt(q.q, q.g, answer);
  } else {
    const { data: p } = await db.from('profiles').select('name, cv, letter').eq('id', u.user.id).maybeSingle();
    if (!p?.cv?.trim()) return fail('Paste and save your CV first.');
    const role = body.role || {}; if (!role.company || !role.role) return fail('Choose a role first.');
    const jd = String(body.jd || '');
    prompt = task === 'cv' ? cvPrompt(role, jd, p.cv) : letterPrompt(role, jd, p.cv, p.letter || '', p.name || '');
  }

  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: MODEL, max_tokens: task === 'feedback' ? 600 : 2000, messages: [{ role: 'user', content: prompt }] }),
  });
  if (r.status === 429) return fail('Too many requests just now. Wait a minute and try again.', 429);
  if (!r.ok) return fail('Claude could not answer just now. Try again.', 502);
  const j = await r.json();
  const text = (j.content || []).filter((c: any) => c.type === 'text').map((c: any) => c.text).join('');
  await db.from('ai_usage').insert({ kind: task });
  return Response.json({ text });
}
