'use client';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useStore } from '@/lib/store';

export default function TailorPage() { return <Suspense><Tailor /></Suspense>; }

function Tailor() {
  const s = useStore();
  const params = useSearchParams();
  const [target, setTarget] = useState('');
  const [jd, setJd] = useState('');
  const [p, setP] = useState(s.profile);
  const [status, setStatus] = useState(''); const [pstatus, setPstatus] = useState('');
  const [out, setOut] = useState(''); const [notes, setNotes] = useState(''); const [head, setHead] = useState('Result');
  const [busy, setBusy] = useState(false); const [kind, setKind] = useState<'cv' | 'letter'>('cv');
  useEffect(() => setP(s.profile), [s.profile]);
  useEffect(() => { // arriving from "Tailor" in the tracker
    const o = params.get('o'); if (!o) return;
    const a = s.apps.find(x => x.openingId === o); setTarget(a ? 'a:' + a.id : 'o:' + o);
  }, [params, s.apps]);

  const role = (() => {
    if (target.startsWith('a:')) { const a = s.apps.find(x => x.id === target.slice(2)); if (a) return { company: a.company, role: a.role, location: a.location, category: a.category, app: a }; }
    if (target.startsWith('o:')) { const o = s.openings.find(x => x.id === target.slice(2)); if (o) return { company: o.firm, role: o.title, location: o.location, category: o.category, opening: o }; }
    return null;
  })();
  const canAI = s.mode === 'live' && !!s.profile.cv.trim();

  async function run(k: 'cv' | 'letter') {
    if (!role) return setStatus('Choose a role first.');
    setKind(k); setBusy(true); setNotes(''); setHead((k === 'cv' ? 'Tailored CV' : 'Cover letter') + ': ' + role.company);
    setStatus('Writing… this usually takes 10 to 40 seconds.');
    const r = await s.ai(k, { role: { company: role.company, role: role.role, location: role.location, category: role.category }, jd });
    setBusy(false);
    if (r.error) return setStatus(r.error);
    const parts = (r.text || '').split(/\n\s*###\s*\n/); setOut(parts[0].trim()); setNotes(parts[1] ? 'What to check:\n' + parts[1].trim() : '');
    setStatus('Done. Read it carefully, edit anything, then copy or save it.');
  }
  async function keep() {
    if (!out.trim() || !role) return s.toast('Write something for a role first');
    let a: any = (role as any).app || (role as any).opening && s.apps.find(x => x.openingId === (role as any).opening.id);
    const o = (role as any).opening;
    if (!a && o) a = { id: '', openingId: o.id, company: o.firm, role: o.title, category: o.category, level: o.level, location: o.location, link: o.url, stage: 'Not started', deadline: o.deadline || '', appliedOn: '', nextStep: '', nextDate: '', notes: '', jd: '', cvT: '', letterT: '' };
    const saved = await s.putApp({ ...a, [kind === 'cv' ? 'cvT' : 'letterT']: out, jd });
    if (saved) { setTarget('a:' + saved.id); s.toast(kind === 'cv' ? 'CV saved to the application' : 'Letter saved to the application'); }
  }
  function download() {
    if (!out.trim()) return s.toast('Nothing to download yet');
    const blob = new Blob([out], { type: 'text/plain' }); const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${(role?.company || 'Role').replace(/[^\w\- ]+/g, '')} - ${kind === 'cv' ? 'CV' : 'Cover letter'}.txt`; a.click(); URL.revokeObjectURL(url);
  }

  return (<>
    <div className="head"><div><h1>CV &amp; cover letters</h1><p className="sub">Claude rewrites your CV and drafts a cover letter for one role at a time, using only facts from your CV.</p></div></div>
    <div className="grid2">
      <section className="panel glass"><h2>Your master CV</h2>
        <div className="field"><label htmlFor="p-name">Your name</label><input id="p-name" value={p.name} onChange={e => setP({ ...p, name: e.target.value })} placeholder="As it should appear on letters" /></div>
        <div className="field"><label htmlFor="p-cv">CV text</label><textarea id="p-cv" style={{ minHeight: 260 }} value={p.cv} onChange={e => setP({ ...p, cv: e.target.value })} placeholder="Paste the text of your CV here. From a PDF: open it, select all, copy and paste." /></div>
        <div className="field"><label htmlFor="p-letter">An existing cover letter (optional, so drafts match your voice)</label><textarea id="p-letter" value={p.letter} onChange={e => setP({ ...p, letter: e.target.value })} /></div>
        <div className="row"><button className="btn primary" onClick={async () => { const ok = await s.putProfile(p); setPstatus(ok ? (s.mode === 'live' ? 'Saved.' : 'Updated for this visit only. Sign in to keep it.') : 'Not saved.'); }}>Save</button>
          <label className="btn" htmlFor="p-file">Load a .txt file</label>
          <input type="file" id="p-file" accept=".txt,.md,text/plain" hidden onChange={async e => { const f = e.target.files?.[0]; if (f) { setP({ ...p, cv: await f.text() }); setPstatus('Loaded. Press Save to keep it.'); } }} />
          <span className="status">{pstatus}</span></div>
      </section>
      <section className="panel glass"><h2>Tailor for a role</h2>
        <div className="field"><label htmlFor="ai-target">Role</label>
          <select id="ai-target" className="ctl" value={target} onChange={e => { setTarget(e.target.value); const a = s.apps.find(x => 'a:' + x.id === e.target.value); if (a?.jd && !jd) setJd(a.jd); }}>
            <option value="">Choose a role…</option>
            {s.apps.length ? <optgroup label="My applications">{s.apps.map(a => <option key={a.id} value={'a:' + a.id}>{a.company} · {a.role}</option>)}</optgroup> : null}
            <optgroup label="Open roles">{s.openings.filter(o => o.status === 'open').slice(0, 300).map(o => <option key={o.id} value={'o:' + o.id}>{o.firm} · {o.title}</option>)}</optgroup>
          </select></div>
        <div className="field"><label htmlFor="ai-jd">Job description (paste it from the posting for the best result)</label><textarea id="ai-jd" style={{ minHeight: 200 }} value={jd} onChange={e => setJd(e.target.value)} /></div>
        <div className="row"><button className="btn primary" disabled={!canAI || busy} onClick={() => run('cv')}>Tailor my CV</button>
          <button className="btn primary" disabled={!canAI || busy} onClick={() => run('letter')}>Write a cover letter</button></div>
        <p className="hint">{s.mode !== 'live' ? 'Sign in to use AI tailoring.' : !s.profile.cv.trim() ? 'Paste and save your CV on the left first.' : 'Each run takes 10 to 40 seconds. Always check the result before sending it.'}</p>
      </section>
    </div>
    <section className="panel glass"><div className="head"><h2>{head}</h2><div className="row">
      <button className="btn small" onClick={async () => { try { await navigator.clipboard.writeText(out); s.toast('Copied'); } catch { s.toast('Select the text and copy it'); } }}>Copy</button>
      <button className="btn small" onClick={download}>Download</button><button className="btn small" onClick={keep}>Save to application</button></div></div>
      <p className="status">{status}</p>
      <textarea className="ctl out" aria-label="Result" value={out} onChange={e => setOut(e.target.value)} placeholder="Your tailored CV or cover letter will appear here." />
      <p className="notes">{notes}</p></section>
  </>);
}
