'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';

const TABS = [['/', 'Tracker'], ['/progress', 'My progress'], ['/tailor', 'CV & letters'], ['/prep', 'Interview prep']];

export default function Header() {
  const path = usePathname();
  const { mode, session, configured, signOut } = useStore();
  const label = mode === 'live' ? 'Saved to your account' : mode === 'loading' ? 'Connecting' : mode === 'preview' ? 'Preview, not saved' : 'Examples, not saved';
  return (
    <header className="top"><div className="wrap"><div className="bar glass">
      <Link href="/" className="brand"><i aria-hidden="true"></i>Applicant Desk</Link>
      <nav className="seg" aria-label="Sections">
        {TABS.map(([href, name]) => (
          <Link key={href} href={href} role="tab" aria-selected={path === href} style={{ border: 0, borderRadius: 999, padding: '6px 14px', fontSize: 14, fontWeight: 500, whiteSpace: 'nowrap', textDecoration: 'none', color: 'var(--ink)', background: path === href ? 'var(--glass-strong)' : 'transparent', boxShadow: path === href ? '0 1px 3px rgba(0,0,0,.12)' : 'none' }}>{name}</Link>
        ))}
      </nav>
      <div className="account">
        <span className={'mode' + (mode === 'live' ? ' live' : '')}>{label}</span>
        {session ? <button className="btn small" onClick={signOut} title={session.user.email || ''}>Sign out</button>
          : configured ? <Link className="btn small primary" href="/login">Sign in</Link> : null}
      </div>
    </div></div></header>
  );
}
