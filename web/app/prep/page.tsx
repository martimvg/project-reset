'use client';
import { useState } from 'react';
import { useStore } from '@/lib/store';
import { QB, QCATS } from '@/lib/constants';

export default function PrepPage() {
  const s = useStore();
  const [cat, setCat] = useState('All'); const [q, setQ] = useState('');
  const list = QB.filter(x => (cat === 'All' || x.cat === cat) && (!q || (x.q + ' ' + x.g).toLowerCase().includes(q.toLowerCase())));
  const done = QB.filter(x => s.prep[x.id]?.done).length;
  return (<>
    <div className="head"><div><h1>Interview prep</h1><p className="sub">A starter question bank for IB and PE interviews. Write your answer, then ask Claude for feedback.</p>
      <div className="stats"><span><b>{done}</b> of {QB.length} practised</span></div></div></div>
    <section className="panel glass">
      <div className="chips" role="group" aria-label="Question topics">{['All', ...QCATS].map(c => <button key={c} className="chip" aria-pressed={cat === c} onClick={() => setCat(c)}>{c}<span>{c === 'All' ? QB.length : QB.filter(x => x.cat === c).length}</span></button>)}</div>
      <input type="search" className="ctl" placeholder="Search questions" aria-label="Search questions" value={q} onChange={e => setQ(e.target.value)} />
      <ul className="qlist">{list.map(x => <Question key={x.id} x={x} />)}{!list.length ? <li className="empty">No questions match.</li> : null}</ul>
      <p className="hint">This is a first set of {QB.length} questions. Which topics and firms the bank should cover is still to be decided.</p>
    </section>
  </>);
}

function Question({ x }: { x: { id: string; cat: string; q: string; g: string } }) {
  const s = useStore();
  const p = s.prep[x.id] || {};
  const [ans, setAns] = useState(p.answer || ''); const [st, setSt] = useState(''); const [busy, setBusy] = useState(false);
  async function feedback() {
    if (!ans.trim()) return setSt('Write an answer first.');
    setBusy(true); setSt('Reading your answer…');
    const r = await s.ai('feedback', { questionId: x.id, answer: ans });
    setBusy(false);
    if (r.error) return setSt(r.error);
    setSt(''); await s.putPrep(x.id, { answer: ans, feedback: (r.text || '').trim() });
  }
  return (
    <li><details className="q"><summary><span>{x.q}</span><span className={'pill ' + (p.done ? 't-good' : 't-idle')}>{p.done ? 'Practised' : x.cat}</span></summary>
      <p className="guide"><b>What a good answer covers</b>{x.g}</p>
      <div className="field"><label htmlFor={'ans-' + x.id}>Your answer</label><textarea id={'ans-' + x.id} value={ans} onChange={e => setAns(e.target.value)} placeholder="Write it as you would say it." /></div>
      <div className="row"><button className="btn small primary" disabled={s.mode !== 'live' || busy} onClick={feedback}>Get feedback</button>
        <button className="btn small" onClick={async () => { await s.putPrep(x.id, { answer: ans }); setSt(s.mode === 'live' ? 'Saved.' : 'Sign in to keep your answers.'); }}>Save answer</button>
        <label className="toggle"><input type="checkbox" checked={!!p.done} onChange={e => s.putPrep(x.id, { done: e.target.checked })} /> Practised</label>
        <span className="status">{s.mode !== 'live' && !st ? 'Sign in for AI feedback.' : st}</span></div>
      {p.feedback ? <p className="fb">{p.feedback}</p> : null}
    </details></li>
  );
}
