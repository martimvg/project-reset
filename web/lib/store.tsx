'use client';
// The app's memory: job data, the signed-in student's data, and functions to save changes.
// Without Supabase settings it runs in "demo" mode with example data, so the site can be previewed before setup.
import { createClient, SupabaseClient, Session } from '@supabase/supabase-js';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { App, BLANK, Firm, OLD_LEVEL, Opening, Prep, Todo, daysTo, exampleApps, exampleTodos, firmKey, norm } from './constants';

const URL_ = process.env.NEXT_PUBLIC_SUPABASE_URL;
const KEY_ = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
export const supabase: SupabaseClient | null = URL_ && KEY_ ? createClient(URL_, KEY_) : null;

type Mode = 'loading' | 'demo' | 'live' | 'preview';
type Profile = { name: string; cv: string; letter: string; isAdmin?: boolean; plan?: string };

type Store = {
  mode: Mode; session: Session | null; configured: boolean;
  openings: Opening[]; firms: Firm[]; meta: any; loaded: boolean;
  apps: App[]; todos: Todo[]; prep: Record<string, Prep>; profile: Profile;
  putApp(a: App): Promise<App | null>; dropApp(id: string): Promise<void>;
  putTodo(t: Todo): Promise<void>; dropTodo(id: string): Promise<void>;
  putPrep(qid: string, p: Prep): Promise<void>; putProfile(p: Partial<Profile>): Promise<boolean>;
  addRole(o: any): Promise<string | null>;
  ai(task: string, body: any): Promise<{ text?: string; error?: string }>;
  preview(on: boolean): void; signOut(): Promise<void>;
  toast(msg: string): void;
};
const Ctx = createContext<Store | null>(null);
export const useStore = () => useContext(Ctx)!;

/* database rows <-> app objects */
const fromOpening = (r: any): Opening => ({
  id: r.id, firm: r.firm, title: r.title, url: r.url || '', location: r.location || 'London', category: r.category || 'Investment Banking',
  area: r.area || '', level: OLD_LEVEL[r.level] || r.level || 'Summer Internship', posted: r.posted || '', firstSeen: r.first_seen ?? r.firstSeen ?? '',
  lastChecked: r.last_checked ?? r.lastChecked ?? '', deadline: r.deadline || '', rolling: !!r.rolling, status: r.status || 'open',
  src: r.source || r.src || (r.manual ? 'found' : 'robot'), foundOn: r.found_on ?? r.foundOn ?? '', note: r.note || '', unconfirmed: !!r.unconfirmed, apply: r.apply,
});
const fromApp = (r: any): App => ({
  ...BLANK, id: r.id, openingId: r.opening_id || undefined, company: r.company, role: r.role, category: r.category, level: OLD_LEVEL[r.level] || r.level,
  location: r.location, stage: r.stage, maxStage: r.max_stage, deadline: r.deadline, appliedOn: r.applied_on, nextStep: r.next_step, nextDate: r.next_date,
  link: r.link, notes: r.notes, jd: r.jd, cvT: r.cv_t, letterT: r.letter_t,
});
const toApp = (a: App) => ({
  id: a.id, opening_id: a.openingId || null, company: a.company, role: a.role, category: a.category, level: a.level, location: a.location, stage: a.stage,
  max_stage: a.maxStage || '', deadline: a.deadline || '', applied_on: a.appliedOn || '', next_step: a.nextStep || '', next_date: a.nextDate || '',
  link: a.link || '', notes: a.notes || '', jd: a.jd || '', cv_t: a.cvT || '', letter_t: a.letterT || '', updated_at: new Date().toISOString(),
});
const fromTodo = (r: any): Todo => ({ id: r.id, title: r.title, type: r.type, firm: r.firm || '', due: r.due || '', done: !!r.done, appId: r.app_id });
const toTodo = (t: Todo) => ({ id: t.id, title: t.title, type: t.type, firm: t.firm || '', due: t.due || '', done: !!t.done, app_id: t.appId || null });
export const uuid = () => (globalThis.crypto && 'randomUUID' in crypto ? crypto.randomUUID() : 'x' + Math.random().toString(36).slice(2) + Date.now().toString(36));

/* combine the job lists, remove duplicates, close past-deadline roles */
export function mergeOpenings(rows: Opening[]) {
  const order = { manual: 0, robot: 1, found: 2, hand: 3 } as any;
  const out: Opening[] = [], seen = new Map<string, Opening>();
  for (const r0 of [...rows].sort((a, b) => order[a.src] - order[b.src])) {
    const r = { ...r0 };
    if (r.status === 'open' && r.deadline && (daysTo(r.deadline) as number) < 0) r.status = 'closed';
    const k = firmKey(r.firm) + '|' + norm(r.title);
    const prev = seen.get(k);
    if (prev) { if (!prev.deadline && r.deadline && (daysTo(r.deadline) as number) >= 0) prev.deadline = r.deadline; continue; }
    seen.set(k, r); out.push(r);
  }
  return out;
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<Mode>('loading');
  const [session, setSession] = useState<Session | null>(null);
  const [openings, setOpenings] = useState<Opening[]>([]);
  const [firms, setFirms] = useState<Firm[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [loaded, setLoaded] = useState(false);
  const [apps, setApps] = useState<App[]>(exampleApps());
  const [todos, setTodos] = useState<Todo[]>(exampleTodos());
  const [prep, setPrep] = useState<Record<string, Prep>>({});
  const [profile, setProfile] = useState<Profile>({ name: '', cv: '', letter: '' });
  const real = useRef<{ apps: App[]; todos: Todo[] }>({ apps: [], todos: [] });
  const [toastMsg, setToastMsg] = useState(''); const toastTimer = useRef<any>(null);
  const toast = useCallback((m: string) => { setToastMsg(m); clearTimeout(toastTimer.current); toastTimer.current = setTimeout(() => setToastMsg(''), 2800); }, []);
  const live = mode === 'live';

  /* job data: database first, robot file as fallback */
  useEffect(() => {
    (async () => {
      let rows: Opening[] = [], fs: Firm[] = [], m: any = null;
      if (supabase) {
        const [o, f, mm] = await Promise.all([
          supabase.from('openings').select('*').limit(5000),
          supabase.from('firms').select('*').order('name').limit(1000),
          supabase.from('meta').select('*').eq('key', 'robot').maybeSingle(),
        ]);
        rows = (o.data || []).map(fromOpening);
        fs = (f.data || []).map((r: any) => ({ id: r.id, name: r.name, sector: r.sector, category: r.category, url: r.url, readable: r.readable, lastRead: r.last_read }));
        m = mm.data?.value || null;
      }
      if (!rows.length) {
        try {
          const j = await (await fetch('/openings.json', { cache: 'no-store' })).json();
          rows = (j.openings || []).map((r: any) => fromOpening({ ...r, source: r.manual ? 'found' : 'robot' }));
          fs = j.firms || []; m = j.meta || null;
        } catch {}
      }
      setOpenings(mergeOpenings(rows)); setFirms(fs); setMeta(m); setLoaded(true);
    })();
  }, []);

  /* sign-in state */
  useEffect(() => {
    if (!supabase) { setMode('demo'); return; }
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); if (!data.session) setMode('demo'); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => { setSession(s); if (!s) { setMode('demo'); setApps(exampleApps()); setTodos(exampleTodos()); setPrep({}); } });
    return () => sub.subscription.unsubscribe();
  }, []);

  /* the student's own data */
  useEffect(() => {
    if (!supabase || !session) return;
    (async () => {
      const [p, a, t, q] = await Promise.all([
        supabase.from('profiles').select('*').eq('id', session.user.id).maybeSingle(),
        supabase.from('applications').select('*').order('created_at', { ascending: false }),
        supabase.from('todos').select('*'),
        supabase.from('prep_answers').select('*'),
      ]);
      if (a.error) { toast('Could not load your tracker. Try refreshing.'); return; }
      if (p.data) setProfile({ name: p.data.name || '', cv: p.data.cv || '', letter: p.data.letter || '', isAdmin: p.data.is_admin, plan: p.data.plan });
      real.current = { apps: (a.data || []).map(fromApp), todos: (t.data || []).map(fromTodo) };
      setApps(real.current.apps); setTodos(real.current.todos);
      const m: Record<string, Prep> = {}; (q.data || []).forEach((r: any) => (m[r.question_id] = { answer: r.answer, feedback: r.feedback, done: r.done })); setPrep(m);
      setMode('live');
    })();
  }, [session, toast]);

  const putApp = useCallback(async (a: App) => {
    const obj = { ...a, id: a.id && !a.id.startsWith('ex-') && !a.id.startsWith('new') ? a.id : live ? uuid() : a.id || 'new-' + Date.now() };
    if (live) { const { error } = await supabase!.from('applications').upsert(toApp(obj)); if (error) { toast('Could not save. Try again.'); return null; } }
    setApps(l => { const i = l.findIndex(x => x.id === obj.id || x.id === a.id); const n = [...l]; if (i >= 0) n[i] = obj; else n.unshift(obj); if (live) real.current.apps = n; return n; });
    return obj;
  }, [live, toast]);
  const dropApp = useCallback(async (id: string) => {
    if (live) { const { error } = await supabase!.from('applications').delete().eq('id', id); if (error) return toast('Could not delete. Try again.'); }
    setApps(l => l.filter(x => x.id !== id)); setTodos(l => l.filter(x => x.appId !== id));
  }, [live, toast]);
  const putTodo = useCallback(async (t: Todo) => {
    const obj = { ...t, id: t.id && !t.id.startsWith('ext-') && !t.id.startsWith('new') ? t.id : live ? uuid() : t.id || 'new-' + Date.now() };
    if (live) { const { error } = await supabase!.from('todos').upsert(toTodo(obj)); if (error) return toast('Could not save the task. Try again.'); }
    setTodos(l => { const i = l.findIndex(x => x.id === obj.id || x.id === t.id); const n = [...l]; if (i >= 0) n[i] = obj; else n.push(obj); return n; });
  }, [live, toast]);
  const dropTodo = useCallback(async (id: string) => {
    if (live) { const { error } = await supabase!.from('todos').delete().eq('id', id); if (error) return toast('Could not delete. Try again.'); }
    setTodos(l => l.filter(x => x.id !== id));
  }, [live, toast]);
  const putPrep = useCallback(async (qid: string, p: Prep) => {
    const next = { ...(prep[qid] || {}), ...p };
    setPrep(m => ({ ...m, [qid]: next }));
    if (live) { const { error } = await supabase!.from('prep_answers').upsert({ question_id: qid, answer: next.answer || '', feedback: next.feedback || '', done: !!next.done, updated_at: new Date().toISOString() }); if (error) toast('Could not save. Try again.'); }
  }, [live, prep, toast]);
  const putProfile = useCallback(async (p: Partial<Profile>) => {
    const next = { ...profile, ...p }; setProfile(next);
    if (live) { const { error } = await supabase!.from('profiles').update({ name: next.name, cv: next.cv, letter: next.letter }).eq('id', session!.user.id); if (error) { toast('Could not save. Try again.'); return false; } }
    return true;
  }, [live, profile, session, toast]);
  const addRole = useCallback(async (o: any) => {
    if (!live) return 'Sign in to add roles.';
    const row = { id: 'm-' + uuid().slice(0, 12), source: 'manual', ...o };
    const { error } = await supabase!.from('openings').insert(row);
    if (error) return 'Only admins can add roles.';
    setOpenings(l => mergeOpenings([fromOpening(row), ...l])); return null;
  }, [live]);
  const ai = useCallback(async (task: string, body: any) => {
    if (!supabase || !session) return { error: 'Sign in to use AI features.' };
    try {
      const r = await fetch('/api/ai', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + session.access_token }, body: JSON.stringify({ task, ...body }) });
      const j = await r.json(); return r.ok ? { text: j.text } : { error: j.error || 'Something went wrong. Try again.' };
    } catch { return { error: 'Could not reach the server. Check your connection.' }; }
  }, [session]);
  const preview = useCallback((on: boolean) => {
    if (on) { setMode('preview'); setApps(exampleApps()); setTodos(exampleTodos()); }
    else { setMode(session ? 'live' : 'demo'); setApps(real.current.apps); setTodos(real.current.todos); }
  }, [session]);
  const signOut = useCallback(async () => { await supabase?.auth.signOut(); }, []);

  const value = useMemo<Store>(() => ({ mode, session, configured: !!supabase, openings, firms, meta, loaded, apps, todos, prep, profile,
    putApp, dropApp, putTodo, dropTodo, putPrep, putProfile, addRole, ai, preview, signOut, toast }),
    [mode, session, openings, firms, meta, loaded, apps, todos, prep, profile, putApp, dropApp, putTodo, dropTodo, putPrep, putProfile, addRole, ai, preview, signOut, toast]);
  return <Ctx.Provider value={value}>{children}<div id="toast" role="status" aria-live="polite" className={toastMsg ? 'show' : ''}>{toastMsg}</div></Ctx.Provider>;
}
