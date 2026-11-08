'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase, useStore } from '@/lib/store';

export default function LoginPage() {
  const s = useStore(); const router = useRouter();
  const [email, setEmail] = useState(''); const [msg, setMsg] = useState(''); const [busy, setBusy] = useState(false);
  if (!supabase) return <section className="auth glass"><h1>Sign in</h1><p className="hint">Sign-in turns on once the database is connected (see the setup guide).</p></section>;
  if (s.session) { router.replace('/progress'); return null; }
  const redirectTo = typeof window !== 'undefined' ? window.location.origin + '/progress' : undefined;
  return (
    <section className="auth glass">
      <h1>Sign in</h1>
      <p className="sub">Your tracker, CV and interview answers are saved to your account and only you can see them.</p>
      <button className="btn" onClick={() => supabase!.auth.signInWithOAuth({ provider: 'google', options: { redirectTo } })}>Continue with Google</button>
      <div className="field"><label htmlFor="email">Or get a sign-in link by email</label><input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@university.ac.uk" /></div>
      <button className="btn primary" disabled={busy} onClick={async () => {
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return setMsg('Enter a valid email address.');
        setBusy(true); const { error } = await supabase!.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo } }); setBusy(false);
        setMsg(error ? 'Could not send the link. Try again in a minute.' : 'Check your inbox for a sign-in link.');
      }}>Email me a link</button>
      <p className="status">{msg}</p>
    </section>
  );
}
