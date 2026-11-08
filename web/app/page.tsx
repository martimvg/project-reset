'use client';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Sheet from '@/components/Sheet';
import { useStore } from '@/lib/store';
import { App, BLANK, FUNNEL, Opening, PROGS, STAGES, TODAY, daysTo, firmKey, fmt, iso, stageIndex, whenLabel } from '@/lib/constants';

export default function TrackerPage() {
  const s = useStore();
  const router = useRouter();
  const [types, setTypes] = useState<string[]>([]);
  const [cat, setCat] = useState('All');
  const [status, setStatus] = useState('open');
  const [q, setQ] = useState('');
  const [showFirms, setShowFirms] = useState(true);
  const [howto, setHowto] = useState<Opening | null>(null);
  const [adding, setAdding] = useState(false);

  const all = s.openings;
  const open = all.filter(o => o.status === 'open');
  const base = all.filter(o => (status === 'all' || (status === 'open' ? o.status === 'open' : o.status !== 'open')) && (cat === 'All' || o.category === cat));
  const list = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return base.filter(o => (!types.length || types.includes(o.level)) && (!qq || (o.firm + ' ' + o.title + ' ' + (o.area || '')).toLowerCase().includes(qq)))
      .sort((a, b) => Number(a.status !== 'open') - Number(b.status !== 'open') || (a.deadline || '9999').localeCompare(b.deadline || '9999') || a.firm.localeCompare(b.firm));
  }, [base, types, q]);
  const idle = useMemo(() => {
    if (!showFirms || types.length || status === 'closed') return [];
    const withOpen = new Set(open.map(o => firmKey(o.firm)));
    const qq = q.trim().toLowerCase();
    return s.firms.filter(f => !withOpen.has(firmKey(f.name)) && (cat === 'All' || f.category === cat) && (!qq || (f.name + ' ' + f.sector).toLowerCase().includes(qq)));
  }, [s.firms, open, showFirms, types, status, cat, q]);

  const appFor = (id: string) => s.apps.find(a => a.openingId === id);
  const byEmail = (o: Opening) => o.apply && o.apply.method === 'email';
  const toggle = (t: string) => setTypes(t ? (types.includes(t) ? types.filter(x => x !== t) : [...types, t]) : []);
  async function track(o: Opening, stage: string) {
    const a = appFor(o.id);
    const u: App = a ? { ...a, stage } : { ...BLANK, id: '', openingId: o.id, company: o.firm, role: o.title, category: o.category, level: o.level, location: o.location, link: o.url, deadline: o.deadline || '', stage };
    if (u.stage !== 'Not started' && !u.appliedOn) u.appliedOn = iso(TODAY);
    if (FUNNEL.includes(u.stage) && (!u.maxStage || stageIndex(u.stage) > stageIndex(u.maxStage))) u.maxStage = u.stage;
    if (await s.putApp(u)) s.toast(`${o.firm}: ${stage}`);
  }
  const last = s.meta?.generated ? new Date(s.meta.generated).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'not yet';

  return (
    <section className="panel glass">
      <div className="head"><div><h1>Entry-level IB &amp; PE roles in London</h1>
        <div className="stats"><span><b>{all.length}</b> roles listed</span><span><b>{open.length}</b> open now</span><span><b>{s.firms.length || '—'}</b> firms tracked</span>
          <span><b>{s.meta?.firmsReadable ?? '—'}</b> read automatically</span><span>Robot last ran <b>{last}</b></span></div></div>
        {s.profile.isAdmin ? <button className="btn" onClick={() => setAdding(true)}>Add a role</button> : null}</div>
      <div className="chips" role="group" aria-label="Programme types (pick one or more)">
        <button className="chip" aria-pressed={!types.length} onClick={() => toggle('')}>All types</button>
        {PROGS.map(t => <button key={t} className="chip" aria-pressed={types.includes(t)} onClick={() => toggle(t)}>{t}<span>{base.filter(o => o.level === t).length}</span></button>)}
      </div>
      <div className="row">
        <div className="seg" role="group" aria-label="Category">{['All', 'Investment Banking', 'Private Equity'].map(c => <button key={c} aria-pressed={cat === c} onClick={() => setCat(c)}>{c === 'All' ? 'IB and PE' : c}</button>)}</div>
        <div className="seg" role="group" aria-label="Status">{[['open', 'Open'], ['all', 'All'], ['closed', 'Closed']].map(([v, l]) => <button key={v} aria-pressed={status === v} onClick={() => setStatus(v)}>{l}</button>)}</div>
        <input type="search" className="ctl" placeholder="Search firm, programme or team" aria-label="Search roles" value={q} onChange={e => setQ(e.target.value)} />
        <label className="toggle"><input type="checkbox" checked={showFirms} onChange={e => setShowFirms(e.target.checked)} /> Firms with nothing open</label>
      </div>
      <div className="scroll"><table><thead><tr><th>My status</th><th>Company</th><th>Programme</th><th>Type</th><th>Closes</th><th>Location</th><th>Source</th><th></th></tr></thead>
        <tbody>
          {!s.loaded ? <tr><td colSpan={8}><div className="empty">Loading roles…</div></td></tr> : null}
          {s.loaded && !list.length && !idle.length ? <tr><td colSpan={8}><div className="empty">No roles match these filters. Clear a filter or pick another type.</div></td></tr> : null}
          {list.map(o => {
            const a = appFor(o.id); const d = daysTo(o.deadline) as number;
            return (
              <tr key={o.id} className={o.status !== 'open' ? 'closed' : ''}>
                <td><select className={'osel' + (a ? ' tracked' : '')} aria-label={`My status for ${o.firm}`} value={a?.stage || ''} onChange={e => e.target.value && track(o, e.target.value)}>
                  {!a ? <option value="">Track</option> : null}{STAGES.map(x => <option key={x}>{x}</option>)}</select></td>
                <td className="firmname">{o.firm}<div className="p">{o.category === 'Private Equity' ? 'Private equity' : 'Investment banking'}</div></td>
                <td>{byEmail(o) ? <><button className="t" onClick={() => setHowto(o)}>{o.title}</button><span className="tag mail">Apply by email</span></> : <a className="t" href={o.url} target="_blank" rel="noopener">{o.title}</a>}
                  {o.src === 'robot' && o.firstSeen && (daysTo(o.firstSeen) as number) >= -3 && o.firstSeen > (s.meta?.seededOn || '') ? <span className="tag new">New</span> : null}
                  {o.area ? <div className="p">{o.area}</div> : null}{o.note ? <div className="p">{o.note}</div> : null}</td>
                <td>{o.level}</td>
                <td>{o.status !== 'open' ? <><span className="pill t-idle">Closed</span>{o.deadline ? <div className="p">{fmt(o.deadline)}</div> : null}</>
                  : o.unconfirmed ? <><span className="pill t-warn">Check status</span><div className="p">on the careers site</div></>
                  : o.rolling ? <span className="pill t-info">Rolling</span>
                  : o.deadline ? <><span className={'num' + (d <= 7 ? ' due soon' : '')}>{fmt(o.deadline)}</span><div className="p">{whenLabel(d)}</div></> : <span className="p">Not stated</span>}</td>
                <td>{o.location}</td>
                <td>{o.src === 'found' ? <><span className="pill t-info">Found</span><div className="p">on {o.foundOn}</div></>
                  : o.src === 'robot' ? <><span className="pill t-good">Live</span><div className="p">seen {fmt(o.firstSeen)}</div></>
                  : o.src === 'manual' ? <span className="pill t-accent">Added</span>
                  : <><span className="pill t-idle">Checked</span><div className="p">{fmt(o.lastChecked || o.firstSeen)}</div></>}</td>
                <td><div className="acts"><button className="btn small" onClick={() => router.push('/tailor?o=' + encodeURIComponent(o.id))}>Tailor</button>
                  {byEmail(o) ? <button className="btn small primary" onClick={() => setHowto(o)}>How to apply</button> : <a className="btn small primary" href={o.url} target="_blank" rel="noopener">Apply</a>}</div></td>
              </tr>);
          })}
          {idle.length ? <tr><td colSpan={8}><h3 style={{ marginTop: 6 }}>Firms with no open role found right now ({idle.length})</h3></td></tr> : null}
          {idle.map(f => {
            let root = false; try { root = new URL(f.url).pathname.length <= 1; } catch {}
            return (
              <tr key={f.id} className="firm"><td><span className="pill t-idle">Watching</span></td><td className="firmname">{f.name}<div className="p">{f.sector}</div></td>
                <td><span className="p">No open entry-level role found{f.readable ? '. Checked automatically' + (f.lastRead ? ' on ' + fmt(f.lastRead) : '') : '. Not read automatically yet: check the careers page'}</span></td>
                <td>—</td><td>—</td><td>London</td><td>{f.readable ? <span className="pill t-good">Robot</span> : <span className="pill t-warn">Manual</span>}</td>
                <td><div className="acts">{f.url ? <a className="btn small" href={f.url} target="_blank" rel="noopener">{root ? 'Website' : 'Careers page'}</a>
                  : <a className="btn small" href={'https://www.google.com/search?q=' + encodeURIComponent(f.name + ' careers students graduates London')} target="_blank" rel="noopener">Find careers page</a>}</div></td></tr>);
          })}
        </tbody></table></div>
      <p className="hint">Pick one or more types to combine them. &quot;Live&quot; roles come from the robot that reads careers sites. &quot;Checked&quot; roles were verified by hand on the date shown. &quot;Found&quot; roles were spotted on job boards for firms that block the robot; their link goes to the firm&apos;s own careers site.</p>
      <HowTo o={howto} onClose={() => setHowto(null)} />
      <AddRole open={adding} onClose={() => setAdding(false)} />
    </section>
  );
}

function HowTo({ o, onClose }: { o: Opening | null; onClose: () => void }) {
  const s = useStore();
  const ap = o?.apply || {};
  const name = s.profile.name.trim();
  const subject = o ? ap.subject || `Application: ${o.title}${name ? ' – ' + name : ''}` : '';
  const a = o ? s.apps.find(x => x.openingId === o.id) : null;
  return (
    <Sheet open={!!o} onClose={onClose} title={o ? `How to apply: ${o.firm}` : ''}>
      {o ? <>
        <p className="sub">{o.title} · {o.location} · {o.status !== 'open' ? 'This role is closed.' : o.deadline ? `Closes ${fmt(o.deadline)}.` : 'No closing date published.'}</p>
        <ol className="steps">
          <li><b>Prepare your documents</b>Your CV{ap.coverLetter === false ? '' : ` and a cover letter addressed to ${o.firm}`}, saved as PDFs named with your full name.</li>
          <li><b>Send the email</b>To <span className="mail">{ap.email || 'address not recorded'}</span> with the subject <span className="mail">{subject}</span>
            <div className="row" style={{ marginTop: 8 }}><button className="btn small" onClick={async () => { try { await navigator.clipboard.writeText(ap.email || ''); s.toast('Address copied'); } catch { s.toast(ap.email || ''); } }}>Copy address</button></div></li>
          {ap.instructions ? <li><b>What {o.firm} asks for</b><span className="p">{ap.instructions}</span></li> : null}
          <li><b>Track it</b>Once sent, mark it as applied.<div className="row" style={{ marginTop: 8 }}>
            <button className="btn small" disabled={!!a && a.stage !== 'Not started'} onClick={async () => {
              const u: App = a ? { ...a, stage: 'Applied' } : { ...BLANK, id: '', openingId: o.id, company: o.firm, role: o.title, category: o.category, level: o.level, location: o.location, link: o.url, stage: 'Applied' };
              u.appliedOn = u.appliedOn || iso(TODAY); if (await s.putApp(u)) s.toast(`${o.firm}: Applied`);
            }}>{a && a.stage !== 'Not started' ? 'Already in my applications' : 'I have sent it'}</button></div></li>
        </ol>
        <div className="actions"><button className="btn" onClick={onClose}>Close</button></div>
      </> : null}
    </Sheet>
  );
}

function AddRole({ open, onClose }: { open: boolean; onClose: () => void }) {
  const s = useStore();
  const [f, setF] = useState<any>({ firm: '', title: '', level: PROGS[0], category: 'Investment Banking', deadline: '', how: 'web', url: '', email: '', subject: '', instructions: '' });
  const [err, setErr] = useState('');
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  async function save() {
    if (!f.firm.trim() || !f.title.trim()) return setErr('Add the firm and the programme name.');
    if (f.how === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email)) return setErr('Add the email address candidates should write to.');
    if (f.how === 'web' && !/^https?:\/\//.test(f.url)) return setErr('Add the application link, starting with https://.');
    const e = await s.addRole({ firm: f.firm.trim(), title: f.title.trim(), level: f.level, category: f.category, location: 'London', deadline: f.deadline, status: 'open', url: f.url.trim(),
      first_seen: iso(TODAY), apply: f.how === 'email' ? { method: 'email', email: f.email.trim(), subject: f.subject.trim(), instructions: f.instructions.trim() } : { method: 'web' } });
    if (e) return setErr(e);
    s.toast(f.firm + ' added to the tracker'); onClose();
  }
  return (
    <Sheet open={open} onClose={onClose} title="Add a role">
      <p className="sub">For roles the robot cannot see, such as ones you apply to by email.</p>
      <div className="form">
        <div className="field"><label htmlFor="ar-firm">Firm</label><input id="ar-firm" value={f.firm} onChange={set('firm')} /></div>
        <div className="field"><label htmlFor="ar-level">Programme type</label><select id="ar-level" value={f.level} onChange={set('level')}>{PROGS.map(p => <option key={p}>{p}</option>)}</select></div>
        <div className="field w2"><label htmlFor="ar-title">Programme name</label><input id="ar-title" value={f.title} onChange={set('title')} placeholder="2027 Summer Analyst Programme" /></div>
        <div className="field"><label htmlFor="ar-cat">Category</label><select id="ar-cat" value={f.category} onChange={set('category')}><option>Investment Banking</option><option>Private Equity</option></select></div>
        <div className="field"><label htmlFor="ar-dl">Closing date</label><input id="ar-dl" type="date" value={f.deadline} onChange={set('deadline')} /></div>
        <div className="field w2"><label htmlFor="ar-how">How do candidates apply?</label><select id="ar-how" value={f.how} onChange={set('how')}><option value="web">On a website</option><option value="email">By email</option></select></div>
        <div className="field w2"><label htmlFor="ar-url">{f.how === 'email' ? 'Page where they publish the instructions (optional)' : 'Application link'}</label><input id="ar-url" type="url" value={f.url} onChange={set('url')} placeholder="https://" /></div>
        {f.how === 'email' ? <>
          <div className="field w2"><label htmlFor="ar-email">Email address to send to</label><input id="ar-email" type="email" value={f.email} onChange={set('email')} /></div>
          <div className="field w2"><label htmlFor="ar-subj">Subject line they ask for (optional)</label><input id="ar-subj" value={f.subject} onChange={set('subject')} /></div>
          <div className="field w2"><label htmlFor="ar-ins">Their instructions, in their words (optional)</label><textarea id="ar-ins" value={f.instructions} onChange={set('instructions')} /></div>
        </> : null}
        <p className="err w2" role="alert">{err}</p>
      </div>
      <div className="actions"><button className="btn" onClick={onClose}>Cancel</button><button className="btn primary" onClick={save}>Add role</button></div>
    </Sheet>
  );
}
