'use client';

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LivePollingStatus } from '@/components/LivePollingStatus';

const presets = [
  { id: 'demo-python-agents', title: 'Python multi-agent repo' },
  { id: 'demo-typescript-ai', title: 'TypeScript AI app' },
  { id: 'demo-rfc', title: 'Markdown architecture RFC' },
];

export default function HomePage() {
  const router = useRouter();
  const [tab, setTab] = useState<'repo' | 'rfc'>('repo');
  const [repoUrl, setRepoUrl] = useState('');
  const [rfcText, setRfcText] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);
  const [scanId, setScanId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const api = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  const done = useCallback(() => router.push('/dossier/' + scanId), [router, scanId]);
  const failed = useCallback((message: string) => setError(message), []);

  const submit = async () => {
    setError('');
    if (!api) { setError('Set NEXT_PUBLIC_API_URL to your deployed API Gateway URL.'); return; }
    const input = tab === 'repo' ? { repo_url: repoUrl.trim() } : { rfc_text: rfcText.trim() };
    if (!Object.values(input)[0]) { setError(tab === 'repo' ? 'Enter a public GitHub repository URL.' : 'Write a short RFC or idea first.'); return; }
    setBusy(true);
    try {
      let sessionId = localStorage.getItem('nyxa:session');
      if (!sessionId) { sessionId = crypto.randomUUID(); localStorage.setItem('nyxa:session', sessionId); }
      const response = await fetch(api + '/scans', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...input, session_id: sessionId, force_refresh: forceRefresh }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Scan could not start.');
      const id = result.scan_id as string;
      localStorage.setItem('nyxa:input:' + id, JSON.stringify(input));
      localStorage.setItem('nyxa:session:' + id, sessionId);
      if (result.status === 'COMPLETED') router.push('/dossier/' + id);
      else setScanId(id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Scan could not start.');
    } finally { setBusy(false); }
  };

  return (
    <main className="shell" style={{ paddingTop: 52, paddingBottom: 64 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 64 }}>
        <div className="eyebrow">NYXA / ARCHITECTURE INTELLIGENCE</div>
        <span className="mono muted" style={{ fontSize: 12 }}>REPO + RFC SCOUT</span>
      </header>
      <section style={{ maxWidth: 820 }}>
        <div className="eyebrow">Build with context</div>
        <h1 style={{ fontSize: 'clamp(40px, 7vw, 72px)', lineHeight: 1.02, letterSpacing: '-.05em', margin: '18px 0' }}>
          Know what exists.<br /><span style={{ color: '#38BDF8' }}>Build what’s different.</span>
        </h1>
        <p className="muted" style={{ maxWidth: 650, fontSize: 18, lineHeight: 1.7 }}>
          NyxaLens maps a repo or architecture idea against public projects and proven systems patterns, then gives you a grounded build-next plan.
        </p>
      </section>

      <section className="panel" style={{ padding: 22, marginTop: 34 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
          <button className="button" aria-pressed={tab === 'repo'} onClick={() => setTab('repo')}>GitHub Repo URL</button>
          <button className="button" aria-pressed={tab === 'rfc'} onClick={() => setTab('rfc')}>Markdown RFC / Idea</button>
        </div>
        {tab === 'repo' ? (
          <label className="muted" style={{ display: 'block' }}>Public repository
            <input className="input mono" style={{ marginTop: 8 }} placeholder="https://github.com/owner/repo" value={repoUrl} onChange={e => setRepoUrl(e.target.value)} />
          </label>
        ) : (
          <label className="muted" style={{ display: 'block' }}>Architecture proposal
            <textarea className="input" style={{ display: 'block', minHeight: 150, marginTop: 8, resize: 'vertical' }} placeholder="Describe problem, users, architecture, and constraints…" value={rfcText} onChange={e => setRfcText(e.target.value)} />
          </label>
        )}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 14, marginTop: 18 }}>
          <label className="muted" style={{ fontSize: 13, display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={forceRefresh} onChange={e => setForceRefresh(e.target.checked)} /> Force fresh scan
          </label>
          <button className="button button-primary" onClick={submit} disabled={busy || !!scanId}>{busy ? 'Starting…' : 'Scan architecture →'}</button>
        </div>
        <div style={{ marginTop: 22 }}>
          <div className="muted" style={{ fontSize: 13, marginBottom: 10 }}>Try a precomputed demo (works without AWS)</div>
          <div className="grid-auto">
            {presets.map(preset => <button key={preset.id} className="button" style={{ textAlign: 'left' }} onClick={() => router.push('/dossier/' + preset.id)}>
              <span className="eyebrow" style={{ fontSize: 10 }}>LOAD DEMO</span><div style={{ marginTop: 6 }}>{preset.title}</div>
            </button>)}
          </div>
        </div>
      </section>
      {scanId && <LivePollingStatus scanId={scanId} onCompleted={done} onFailure={failed} />}
      {error && <p role="alert" style={{ color: '#fda4af', marginTop: 16 }}>{error}</p>}
      <footer className="muted" style={{ marginTop: 48, fontSize: 12 }}>Every recommendation links back to evidence. Pattern lift remains an estimate until benchmarked.</footer>
    </main>
  );
}
