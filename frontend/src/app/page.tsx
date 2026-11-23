'use client';

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LivePollingStatus } from '@/components/LivePollingStatus';
import { AppHeader } from '@/components/AppHeader';

const presets = [
  { id: 'demo-python-agents', title: 'Python multi-agent repo', icon: '🐍', blurb: 'Tool-calling agents with unbounded retries.' },
  { id: 'demo-typescript-ai', title: 'TypeScript AI app', icon: '⚛️', blurb: 'Streaming UI with stale concurrent responses.' },
  { id: 'demo-rfc', title: 'Markdown architecture RFC', icon: '📝', blurb: 'Pre-code design review from a written proposal.' },
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
    <>
      <AppHeader right={<><span className="pill pill-cyan">Offline demos ready</span><span className="pill mono">v1</span></>} />
      <main className="shell" style={{ paddingTop: 56, paddingBottom: 64 }}>
        <div className="hero-grid">
          <section>
            <span className="pill pill-cyan">✦ See in the dark. Build in the light.</span>
            <h1 style={{ fontSize: 'clamp(40px, 6.4vw, 72px)', lineHeight: 1.03, letterSpacing: '-.05em', margin: '22px 0', fontWeight: 800 }}>
              Know what exists.<br /><span className="gradient-text">Build what’s different.</span>
            </h1>
            <p className="muted" style={{ maxWidth: 560, fontSize: 18, lineHeight: 1.7, margin: 0 }}>
              NyxaLens maps a repo or architecture idea against public projects and proven systems patterns, then hands you a grounded build-next plan.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 24 }}>
              <span className="pill">🚦 Name collision check</span>
              <span className="pill">🧭 Cross-domain patterns</span>
              <span className="pill">📊 Nyxa score</span>
              <span className="pill">🔗 Citations verified</span>
            </div>
          </section>

          <aside className="hero-preview float" aria-hidden="true">
            <div className="panel" style={{ padding: 22 }}>
              <div className="section-title"><div className="eyebrow">Sample dossier</div><span className="pill pill-green"><span className="dot" /> GREEN</span></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                <svg width="104" height="104" viewBox="0 0 104 104" style={{ transform: 'rotate(-90deg)', flex: 'none' }}>
                  <circle cx="52" cy="52" r="44" fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="9" />
                  <circle cx="52" cy="52" r="44" fill="none" stroke="#38bdf8" strokeWidth="9" strokeLinecap="round" strokeDasharray="216 277" style={{ filter: 'drop-shadow(0 0 7px rgba(56,189,248,.7))' }} />
                </svg>
                <div><div style={{ fontSize: 40, fontWeight: 800, letterSpacing: '-.05em' }}>78<span className="muted" style={{ fontSize: 16 }}>/100</span></div><div className="muted" style={{ fontSize: 13 }}>projected 93 after backlog</div></div>
              </div>
              <div style={{ display: 'grid', gap: 10, marginTop: 18 }}>
                {[['Originality', 74], ['Gap opportunity', 76], ['Enhancement', 84]].map(([label, value]) => <div key={label as string}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 5 }}><span>{label}</span><span className="mono muted">{value}</span></div>
                  <div className="bar"><span style={{ width: value + '%' }} /></div>
                </div>)}
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 18, flexWrap: 'wrap' }}>
                <span className="pill pill-rose">KILL 0</span><span className="pill pill-green">KEEP 1</span><span className="pill pill-cyan">INJECT 1</span>
              </div>
            </div>
          </aside>
        </div>

        <section className="panel" style={{ padding: 26, marginTop: 44 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 14, marginBottom: 20 }}>
            <div className="seg" role="tablist" aria-label="Input type">
              <button className="button" aria-pressed={tab === 'repo'} onClick={() => setTab('repo')}>GitHub Repo URL</button>
              <button className="button" aria-pressed={tab === 'rfc'} onClick={() => setTab('rfc')}>Markdown RFC / Idea</button>
            </div>
            <span className="muted" style={{ fontSize: 13 }}>Public repositories only</span>
          </div>
          {tab === 'repo' ? (
            <label className="muted" style={{ display: 'block', fontSize: 13 }}>Public repository
              <input className="input mono" style={{ marginTop: 8, fontSize: 15 }} placeholder="https://github.com/owner/repo" value={repoUrl} onChange={e => setRepoUrl(e.target.value)} />
            </label>
          ) : (
            <label className="muted" style={{ display: 'block', fontSize: 13 }}>Architecture proposal
              <textarea className="input" style={{ display: 'block', minHeight: 150, marginTop: 8, resize: 'vertical' }} placeholder="Describe problem, users, architecture, and constraints…" value={rfcText} onChange={e => setRfcText(e.target.value)} />
            </label>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 14, marginTop: 20 }}>
            <label className="muted" style={{ fontSize: 13, display: 'flex', gap: 10, alignItems: 'center', cursor: 'pointer' }}>
              <input className="check" type="checkbox" checked={forceRefresh} onChange={e => setForceRefresh(e.target.checked)} /> Force fresh scan
            </label>
            <button className="button button-primary" style={{ padding: '13px 24px', fontSize: 15 }} onClick={submit} disabled={busy || !!scanId}>{busy ? 'Starting…' : 'Scan architecture →'}</button>
          </div>
        </section>

        <section style={{ marginTop: 34 }}>
          <div className="section-title"><div className="eyebrow">Try a precomputed demo</div><span className="muted" style={{ fontSize: 13 }}>Works without AWS</span></div>
          <div className="grid-auto">
            {presets.map(preset => <button key={preset.id} className="panel lift" style={{ textAlign: 'left', padding: 20, cursor: 'pointer', color: 'inherit' }} onClick={() => router.push('/dossier/' + preset.id)}>
              <span className="pill pill-cyan">{preset.icon} Load demo</span>
              <div style={{ marginTop: 14, fontSize: 18, fontWeight: 700, letterSpacing: '-.02em' }}>{preset.title}</div>
              <div className="muted" style={{ fontSize: 13, marginTop: 6 }}>{preset.blurb}</div>
              <div style={{ marginTop: 14, color: '#7dd3fc', fontSize: 13 }}>Open dossier →</div>
            </button>)}
          </div>
        </section>

        {scanId && <LivePollingStatus scanId={scanId} onCompleted={done} onFailure={failed} />}
        {error && <p role="alert" style={{ color: '#fda4af', marginTop: 16 }}>{error}</p>}
        <footer className="muted" style={{ marginTop: 56, fontSize: 12, textAlign: 'center' }}>Every recommendation links back to evidence. Pattern lift remains an estimate until benchmarked.</footer>
      </main>
    </>
  );
}
