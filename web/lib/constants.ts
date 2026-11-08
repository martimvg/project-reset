import QUESTIONS from './questions.json';

export const PROGS = ['Summer Internship', 'Graduate Programme', 'Off-Cycle Internship', 'Industrial Placement', 'Spring Insight', 'Pre-Uni', 'Events'];
export const OLD_LEVEL: Record<string, string> = { 'Off Cycle Internship': 'Off-Cycle Internship', 'Graduate / Entry Level': 'Graduate Programme' };
export const STAGES = ['Not started', 'Applied', 'Online test', 'Video interview', 'Interview', 'Assessment centre', 'Offer', 'Rejected', 'Withdrawn'];
export const FUNNEL = ['Applied', 'Online test', 'Video interview', 'Interview', 'Assessment centre', 'Offer'];
export const ACTIVE = ['Applied', 'Online test', 'Video interview', 'Interview', 'Assessment centre'];
export const TONE: Record<string, string> = { 'Not started': 'idle', Applied: 'info', 'Online test': 'warn', 'Video interview': 'warn', Interview: 'accent', 'Assessment centre': 'accent', Offer: 'good', Rejected: 'bad', Withdrawn: 'idle' };
export const TASK_TYPES = ['Online test', 'Video interview', 'Interview prep', 'Assessment centre', 'Application', 'Follow-up', 'Other'];
export const QCATS = ['Motivation & fit', 'Behavioural', 'Accounting', 'Valuation', 'M&A and LBO', 'Markets & deals', 'Private equity'];
export const QB: { id: string; cat: string; q: string; g: string }[] = QUESTIONS as any;

/* ---------- types (shapes of the data) ---------- */
export type Opening = {
  id: string; firm: string; title: string; url: string; location: string; category: string; area?: string; level: string;
  posted?: string; firstSeen?: string; lastChecked?: string; deadline?: string; rolling?: boolean; status: string;
  src: 'robot' | 'hand' | 'found' | 'manual'; foundOn?: string; note?: string; unconfirmed?: boolean; apply?: any;
};
export type Firm = { id: string; name: string; sector: string; category: string; url: string; readable: boolean; lastRead: string };
export type App = {
  id: string; openingId?: string; company: string; role: string; category: string; level: string; location: string; stage: string;
  maxStage?: string; deadline: string; appliedOn: string; nextStep: string; nextDate: string; link: string; notes: string; jd: string; cvT: string; letterT: string;
};
export type Todo = { id: string; title: string; type: string; firm: string; due: string; done: boolean; appId?: string | null };
export type Prep = { answer?: string; feedback?: string; done?: boolean };

/* ---------- dates and text ---------- */
export const TODAY = (() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; })();
const pad = (n: number) => String(n).padStart(2, '0');
export const iso = (d: Date) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
export const addDays = (n: number) => iso(new Date(TODAY.getTime() + n * 864e5));
const parse = (s?: string) => (s ? new Date(String(s).slice(0, 10) + 'T00:00:00') : null);
export const daysTo = (s?: string) => (s ? Math.round((parse(s)!.getTime() - TODAY.getTime()) / 864e5) : null);
export const fmt = (s?: string) => (s ? parse(s)!.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '');
export const whenLabel = (d: number) => (d < 0 ? Math.abs(d) + 'd overdue' : d === 0 ? 'today' : d === 1 ? 'tomorrow' : 'in ' + d + 'd');
export const norm = (s: string) => String(s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, ' ').trim();
export const firmKey = (s: string) => norm(s).replace(/\b(the|and|co|company|cib|group|securities|plc|llp|ltd|capital markets)\b/g, '').trim().split(' ')[0] || norm(s);
export const stageIndex = (s: string) => FUNNEL.indexOf(s);
export function reached(a: App, s: string) {
  if (a.stage === 'Offer') return true;
  if (a.stage === 'Rejected' || a.stage === 'Withdrawn') return s === 'Applied' ? !!a.appliedOn : a.maxStage ? stageIndex(a.maxStage) >= stageIndex(s) : false;
  return stageIndex(a.stage) >= stageIndex(s);
}
export const BLANK: App = { id: '', company: '', role: '', category: 'Investment Banking', level: 'Summer Internship', location: 'London', stage: 'Not started', deadline: '', appliedOn: '', nextStep: '', nextDate: '', link: '', notes: '', jd: '', cvT: '', letterT: '' };

/* ---------- examples (shown before signing in, or on request) ---------- */
export function exampleApps(): App[] {
  return [
    { company: 'Goldman Sachs', role: '2027 Summer Analyst, Investment Banking', stage: 'Video interview', appliedOn: addDays(-21) },
    { company: 'BNP Paribas', role: '2027 Summer Internship, M&A', stage: 'Online test', appliedOn: addDays(-9) },
    { company: 'Rothschild & Co', role: '2027 Global Advisory Summer Analyst', stage: 'Not started', deadline: addDays(4) },
    { company: 'Evercore', role: 'Off-Cycle Internship, Advisory', level: 'Off-Cycle Internship', stage: 'Applied', appliedOn: addDays(-5) },
    { company: 'Lazard', role: '2027 Spring Insight Programme', level: 'Spring Insight', stage: 'Interview', appliedOn: addDays(-25) },
    { company: 'Jefferies', role: '2027 IB Summer Internship', stage: 'Rejected', appliedOn: addDays(-30) },
    { company: 'Nomura', role: '2027 Coverage & Advisory Summer Internship', stage: 'Applied', appliedOn: addDays(-12) },
    { company: 'EQT', role: '2027 Summer Analyst Programme', category: 'Private Equity', stage: 'Assessment centre', appliedOn: addDays(-40) },
  ].map((a, i) => ({ ...BLANK, ...a, id: 'ex-' + i }));
}
export function exampleTodos(): Todo[] {
  return [
    { title: 'BNP Paribas online test', type: 'Online test', firm: 'BNP Paribas', due: addDays(2) },
    { title: 'Goldman Sachs video interview', type: 'Video interview', firm: 'Goldman Sachs', due: addDays(3) },
    { title: 'Prepare M&A technicals for Lazard interview', type: 'Interview prep', firm: 'Lazard', due: addDays(6) },
    { title: 'Submit Rothschild application', type: 'Application', firm: 'Rothschild & Co', due: addDays(4) },
  ].map((t, i) => ({ ...t, id: 'ext-' + i, done: false }));
}
