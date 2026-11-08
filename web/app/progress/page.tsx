'use client';
import { useMemo, useState } from 'react';
import Sheet from '@/components/Sheet';
import { Funnel, Types, Weeks } from '@/components/Charts';
import { useStore } from '@/lib/store';
import { ACTIVE, App, BLANK, FUNNEL, PROGS, STAGES, TASK_TYPES, TODAY, Todo, daysTo, fmt, iso, reached, stageIndex, whenLabel } from '@/lib/constants';

export default function ProgressPage() {
  const s = useStore();
  const [q, setQ] = useState('');
  const [editApp, setEditApp] = useState<App | null>(null);
  const [editTask, setEditTask] = useState<Todo | null>(null);
  const A = s.apps, sent = A.filter(a => a.stage !== 'Not started'), active = A.filter(a => ACTIVE.includes(a.stage));
  const interviews = A.filter(a => reached(a, 'Video interview')).length, offers = A.filter(a => a.stage === 'Offer').length;
  const rate = sent.length ? Math.round((sent.filter(a => a.stage !== 'Applied').length / sent.length) * 100) : 0;
  const openTasks = s.todos.filter(t => !t.done);

  const insights = useMemo(() => {
    const out: [string, React.ReactNode][] = [];
    const last14 = sent.filter(a => a.appliedOn && (daysTo(a.appliedOn) as number) >= -14).length;
    out.push(['', <>You sent <b>{last14}</b> application{last14 === 1 ? '' : 's'} in the last 14 days and <b>{sent.length}</b> in total.</>]);
    const soon = s.openings.filter(o => o.status === 'open' && o.deadline && (daysTo(o.deadline) as number) >= 0 && (daysTo(o.deadline) as number) <= 7 && !A.some(a => a.openingId === o.id));
    if (soon.length) out.push(['warn', <><b>{soon.length}</b> role{soon.length === 1 ? '' : 's'} you are not tracking close in the next 7 days: {soon.slice(0, 3).map(o => o.firm).join(', ')}{soon.length > 3 ? '…' : ''}.</>]);
    const notStarted = A.filter(a => a.stage === 'Not started' && a.deadline && (daysTo(a.deadline) as number) >= 0).sort((a, b) => a.deadline.localeCompare(b.deadline));
    if (notStarted.length) out.push(['warn', <><b>{notStarted.length}</b> saved application{notStarted.length === 1 ? ' is' : 's are'} not submitted yet. The nearest closes {fmt(notStarted[0].deadline)}.</>]);
    const quiet = A.filter(a => a.stage === 'Applied' && a.appliedOn && (daysTo(a.appliedOn) as number) <= -21);
    if (quiet.length) out.push(['', <>No reply after 3 weeks from <b>{quiet.length}</b> firm{quiet.length === 1 ? '' : 's'} ({quiet.slice(0, 3).map(a => a.company).join(', ')}). Most banks reply in waves, so check your portal.</>]);
    if (sent.length >= 3) { const p = Math.round((interviews / sent.length) * 100); out.push([p >= 20 ? 'good' : '', <><b>{p}%</b> of your applications reached an interview stage.</>]); }
    const tests = s.todos.filter(t => !t.done && t.type === 'Online test');
    if (tests.length) out.push(['warn', <><b>{tests.length}</b> online test{tests.length === 1 ? '' : 's'} to complete. Most expire 5 to 7 days after the invite.</>]);
    const lv: Record<string, number> = {}; sent.forEach(a => (lv[a.level || 'Other'] = (lv[a.level || 'Other'] || 0) + 1));
    const top = Object.entries(lv).sort((a, b) => b[1] - a[1])[0];
    if (top) out.push(['', <>Most of your applications are for <b>{top[0]}</b> ({top[1]}).</>]);
    return out;
  }, [A, s.openings, s.todos, sent, interviews]);

  const rows = A.filter(a => !q || (a.company + ' ' + a.role).toLowerCase().includes(q.toLowerCase())).sort((a, b) => (b.appliedOn || b.deadline || '').localeCompare(a.appliedOn || a.deadline || ''));
  const tasks = [...s.todos].sort((a, b) => Number(a.done) - Number(b.done) || (a.due || '9999').localeCompare(b.due || '9999'));
  async function setStage(a: App, stage: string) {
    const u = { ...a, stage }; if (stage !== 'Not started' && !u.appliedOn) u.appliedOn = iso(TODAY);
    if (FUNNEL.includes(stage) && (!u.maxStage || stageIndex(stage) > stageIndex(u.maxStage))) u.maxStage = stage;
    if (await s.putApp(u)) s.toast(`${u.company}: ${stage}`);
  }
  const k = (v: any, l: string) => <div className="kpi glass"><b>{v}</b><span>{l}</span></div>;

  return (<>
    {s.mode === 'preview' ? <div className="banner glass row"><p>Showing example data so you can see how this page works. Nothing here is saved.</p><button className="btn small" onClick={() => s.preview(false)}>Back to my data</button></div>
      : s.mode === 'live' && !A.length && !s.todos.length ? <div className="banner glass row"><p style={{ color: 'var(--muted)' }}>Your dashboard fills in as you track roles and add tasks.</p><button className="btn small" onClick={() => s.preview(true)}>Preview with example data</button></div>
      : s.mode === 'demo' ? <div className="banner glass"><p>These are example applications and tasks. {s.configured ? 'Sign in to keep your own.' : 'Saving turns on once the database is connected.'}</p></div> : null}
    <div className="head"><div><h1>My progress</h1><p className="sub">Applications, deadlines and what to prepare next.</p></div>
      <div className="row"><button className="btn" onClick={() => setEditTask({ id: '', title: '', type: 'Online test', firm: '', due: '', done: false })}>Add a task</button>
        <button className="btn primary" onClick={() => setEditApp({ ...BLANK })}>Add an application</button></div></div>
    <div className="kpis">{k(sent.length, 'Applications sent')}{k(active.length, 'In progress')}{k(interviews, 'Reached interviews')}{k(offers, 'Offers')}{k(rate + '%', 'Heard back')}{k(openTasks.length, 'Tasks to do')}</div>
    <div className="grid2">
      <section className="panel glass"><div className="head"><h2>To do</h2><span className="hint">{openTasks.length} open · sorted by deadline</span></div>
        {!tasks.length ? <div className="empty">Nothing to do yet. Add online tests, video interviews and interview prep with their deadlines.</div> :
          <ul className="todo">{tasks.slice(0, 12).map(t => {
            const d = daysTo(t.due) as number; const cls = t.done ? '' : t.due && d < 0 ? 'late' : t.due && d <= 3 ? 'soon' : '';
            const tone = t.type === 'Online test' || t.type === 'Video interview' ? 'warn' : t.type === 'Interview prep' || t.type === 'Assessment centre' ? 'accent' : 'idle';
            return (<li key={t.id} className={t.done ? 'done' : ''}>
              <input type="checkbox" checked={t.done} aria-label={`Mark ${t.title} done`} onChange={e => s.putTodo({ ...t, done: e.target.checked })} />
              <div><div className="what">{t.title}</div><div className="p"><span className={'pill t-' + tone}>{t.type}</span> {t.firm}</div></div>
              <div style={{ textAlign: 'right' }}><div className={'due ' + cls}>{t.due ? fmt(t.due) : 'No deadline'}</div>{t.due && !t.done ? <div className="p">{whenLabel(d)}</div> : null}
                <button className="btn ghost small" onClick={() => setEditTask(t)}>Edit</button></div></li>);
          })}</ul>}
      </section>
      <section className="panel glass"><h2>Key insights</h2><ul className="insights">{insights.map(([c, t], i) => <li key={i} className={c}><span>{t}</span></li>)}</ul></section>
    </div>
    <div className="grid3">
      <section className="panel glass chart"><h2>Pipeline</h2><Funnel apps={A} /></section>
      <section className="panel glass chart"><h2>Applications per week</h2><Weeks apps={A} /></section>
      <section className="panel glass chart"><h2>By programme type</h2><Types apps={A} /></section>
    </div>
    <section className="panel glass"><div className="head"><h2>Applications</h2>
      <input type="search" className="ctl" placeholder="Search firm or role" aria-label="Search applications" value={q} onChange={e => setQ(e.target.value)} style={{ maxWidth: 280 }} /></div>
      <div className="scroll"><table><thead><tr><th>Company</th><th>Role</th><th>Type</th><th>Stage</th><th>Applied</th><th>Next step</th><th></th></tr></thead><tbody>
        {!rows.length ? <tr><td colSpan={7}><div className="empty">No applications yet. Use Track on any role in the Tracker, or Add an application.</div></td></tr> : null}
        {rows.map(a => (<tr key={a.id}><td className="firmname">{a.company}</td><td><button className="t" onClick={() => setEditApp(a)}>{a.role}</button></td><td>{a.level}</td>
          <td><select className="osel tracked" aria-label={`Stage for ${a.company}`} value={a.stage} onChange={e => setStage(a, e.target.value)}>{STAGES.map(x => <option key={x}>{x}</option>)}</select></td>
          <td className="num">{a.appliedOn ? fmt(a.appliedOn) : a.deadline ? <span className="p">closes {fmt(a.deadline)}</span> : '—'}</td>
          <td>{a.nextStep || <span className="p">—</span>}{a.nextDate ? <div className="p num">{fmt(a.nextDate)}</div> : null}</td>
          <td><div className="acts"><button className="btn small" onClick={() => setEditApp(a)}>Edit</button></div></td></tr>))}
      </tbody></table></div>
    </section>
    <AppSheet key={editApp ? 'a' + (editApp.id || 'new') : 'a-none'} app={editApp} onClose={() => setEditApp(null)} />
    <TaskSheet key={editTask ? 't' + (editTask.id || 'new') : 't-none'} task={editTask} onClose={() => setEditTask(null)} />
  </>);
}

function AppSheet({ app, onClose }: { app: App | null; onClose: () => void }) {
  const s = useStore();
  const [cur, setF] = useState<App | null>(app); // fresh copy each time the window opens (see key= below)
  const [err, setErr] = useState(''); const [confirm, setConfirm] = useState(false);
  const set = (k: keyof App) => (e: any) => setF({ ...(cur as App), [k]: e.target.value });
  const isNew = !!app && !app.id;
  async function save() {
    const a = { ...(cur as App) };
    if (!a.company.trim() || !a.role.trim()) return setErr('Add the company and the role.');
    if (a.stage !== 'Not started' && !a.appliedOn) a.appliedOn = iso(TODAY);
    if (FUNNEL.includes(a.stage) && (!a.maxStage || stageIndex(a.stage) > stageIndex(a.maxStage))) a.maxStage = a.stage;
    const saved = await s.putApp(a); if (!saved) return;
    if (saved.nextStep && saved.nextDate) { // a next step with a date becomes a to-do
      const type = /test|numerical|verbal|logical/i.test(saved.nextStep) ? 'Online test' : /video|hirevue/i.test(saved.nextStep) ? 'Video interview' : /assessment/i.test(saved.nextStep) ? 'Assessment centre' : /interview/i.test(saved.nextStep) ? 'Interview prep' : 'Other';
      const prev = s.todos.find(t => t.appId === saved.id);
      if (!prev || prev.title !== saved.nextStep || prev.due !== saved.nextDate) await s.putTodo({ id: prev?.id || '', title: saved.nextStep, type, firm: saved.company, due: saved.nextDate, done: prev?.done || false, appId: saved.id.startsWith('ex-') || saved.id.startsWith('new') ? null : saved.id });
    }
    s.toast('Saved'); onClose();
  }
  const sel = (k: keyof App, list: string[]) => <select id={'e-' + k} value={(cur as any)?.[k] || ''} onChange={set(k)}>{list.map(v => <option key={v}>{v}</option>)}</select>;
  const inp = (k: keyof App, label: string, type = 'text', ph = '') => <div className="field"><label htmlFor={'e-' + k}>{label}</label><input id={'e-' + k} type={type} value={(cur as any)?.[k] || ''} placeholder={ph} onChange={set(k)} /></div>;
  return (
    <Sheet open={!!app} onClose={onClose} title={isNew ? 'Add an application' : app ? `${app.company}: ${app.role}` : ''}>
      {cur ? <>
        <div className="form">
          {inp('company', 'Company')}{inp('role', 'Role')}
          <div className="field"><label htmlFor="e-level">Programme type</label>{sel('level', PROGS)}</div>
          <div className="field"><label htmlFor="e-category">Category</label>{sel('category', ['Investment Banking', 'Private Equity'])}</div>
          <div className="field"><label htmlFor="e-stage">Stage</label>{sel('stage', STAGES)}</div>
          {inp('location', 'Location')}{inp('deadline', 'Closing date', 'date')}{inp('appliedOn', 'Applied on', 'date')}
          {inp('nextStep', 'Next step', 'text', 'e.g. HireVue video interview')}{inp('nextDate', 'Next step deadline', 'date')}
          <div className="field w2"><label htmlFor="e-link">Link</label><input id="e-link" value={cur.link} onChange={set('link')} placeholder="https://" /></div>
          <div className="field w2"><label htmlFor="e-notes">Notes</label><textarea id="e-notes" value={cur.notes} onChange={set('notes')} /></div>
          <p className="err w2" role="alert">{err}</p>
        </div>
        <div className="actions">
          {!isNew ? <button className="btn danger" style={{ marginRight: 'auto' }} onClick={async () => { if (!confirm) return setConfirm(true); await s.dropApp(cur.id); s.toast('Application deleted'); onClose(); }}>{confirm ? 'Delete for good?' : 'Delete'}</button> : null}
          <button className="btn" onClick={onClose}>Cancel</button><button className="btn primary" onClick={save}>{isNew ? 'Add' : 'Save'}</button></div>
        <p className="hint">Setting a next step with a deadline adds it to your to-do list.</p>
      </> : null}
    </Sheet>
  );
}

function TaskSheet({ task, onClose }: { task: Todo | null; onClose: () => void }) {
  const s = useStore();
  const [cur, setF] = useState<Todo | null>(task); const [err, setErr] = useState('');
  const set = (k: keyof Todo) => (e: any) => setF({ ...(cur as Todo), [k]: e.target.value });
  return (
    <Sheet open={!!task} onClose={onClose} title={task && task.id ? 'Edit task' : 'Add a task'}>
      {cur ? <>
        <div className="form">
          <div className="field w2"><label htmlFor="t-title">What to do</label><input id="t-title" value={cur.title} onChange={set('title')} placeholder="e.g. Complete the SHL numerical test" /></div>
          <div className="field"><label htmlFor="t-type">Type</label><select id="t-type" value={cur.type} onChange={set('type')}>{TASK_TYPES.map(v => <option key={v}>{v}</option>)}</select></div>
          <div className="field"><label htmlFor="t-due">Deadline</label><input id="t-due" type="date" value={cur.due} onChange={set('due')} /></div>
          <div className="field w2"><label htmlFor="t-firm">Firm (optional)</label><input id="t-firm" value={cur.firm} onChange={set('firm')} list="firmlist" /></div>
          <datalist id="firmlist">{[...new Set(s.apps.map(a => a.company))].map(x => <option key={x} value={x} />)}</datalist>
          <p className="err w2" role="alert">{err}</p>
        </div>
        <div className="actions">
          {task?.id ? <button className="btn danger" style={{ marginRight: 'auto' }} onClick={async () => { await s.dropTodo(task.id); s.toast('Task deleted'); onClose(); }}>Delete</button> : null}
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={async () => { if (!cur.title.trim()) return setErr('Say what needs doing.'); await s.putTodo(cur); s.toast('Task saved'); onClose(); }}>{task?.id ? 'Save' : 'Add task'}</button></div>
      </> : null}
    </Sheet>
  );
}
