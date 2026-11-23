'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LivePollingStatus } from '@/components/LivePollingStatus';
import { AnalogyCard, BadgeSnippet, Dossier, EnhancementBacklog, KillKeepInjectMatrix, MermaidDiagram, NyxaScoreCard, PipelineTracePanel, ReScanButton, TrafficLight } from '@/components/DossierParts';
import demoPython from '../../../../../tests/fixtures/fixture-a-python-agent/dossier.json';
import demoTypeScript from '../../../../../tests/fixtures/fixture-b-typescript-app/dossier.json';
import demoRfc from '../../../../../tests/fixtures/fixture-c-markdown-rfc/dossier.json';

const demos: Record<string, Dossier> = {
  'demo-python-agents': demoPython as Dossier,
  'demo-typescript-ai': demoTypeScript as Dossier,
  'demo-rfc': demoRfc as Dossier,
};

export default function DossierPage({ params }: { params: { scanId: string } }) {
  const router = useRouter();
  const scanId = params.scanId;
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [error, setError] = useState('');
  const [rescanId, setRescanId] = useState('');
  const [scoreDelta, setScoreDelta] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'trace'>('overview');
  const api = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

  useEffect(() => {
    let active = true;
    if (demos[scanId]) { setDossier(demos[scanId]); return () => { active = false; }; }
    if (!api) { setError('NEXT_PUBLIC_API_URL is not configured.'); return; }
    fetch(api + '/scans/' + scanId)
      .then(async response => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || 'Could not load scan.');
        if (active) {
          setDossier(body.dossier);
          setScoreDelta(body.score_delta ?? body.dossier?.score_delta ?? null);
          if (!body.dossier && body.status === 'FAILED') setError('Scan failed. Review API and Lambda logs.');
        }
      })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Could not load scan.'); });
    return () => { active = false; };
  }, [api, scanId]);

  const rescanComplete = useCallback(() => router.replace('/dossier/' + rescanId), [router, rescanId]);
  const rescanFailed = useCallback((message: string) => setError(message), []);
  const startRescan = (id: string) => setRescanId(id);

  return <main className="shell" style={{ paddingTop: 34, paddingBottom: 64 }}>
    <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
      <a href="/" style={{ textDecoration: 'none' }}><span className="eyebrow">← NYXA / DOSSIER</span></a>
      <span className="mono muted" style={{ fontSize: 12 }}>{scanId}</span>
    </header>
    {rescanId && <LivePollingStatus scanId={rescanId} onCompleted={rescanComplete} onFailure={rescanFailed} />}
    {!dossier && !error && <div className="panel muted" style={{ padding: 22 }}>Loading dossier…</div>}
    {error && <p role="alert" style={{ color: '#fda4af' }}>{error}</p>}
    {dossier && <>
      <nav aria-label="Dossier views" style={{ display: 'flex', gap: 10, marginBottom: 22 }}>
        <button className={activeTab === 'overview' ? 'button button-primary' : 'button'} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={activeTab === 'trace' ? 'button button-primary' : 'button'} onClick={() => setActiveTab('trace')}>Pipeline Trace</button>
      </nav>
      {activeTab === 'trace' ? <PipelineTracePanel traces={dossier.pipeline_trace ?? []} /> : <>
      <section style={{ marginBottom: 22 }}>
        <div className="eyebrow">Architectural differentiation map</div>
        <h1 style={{ fontSize: 'clamp(32px, 5vw, 54px)', letterSpacing: '-.04em', margin: '8px 0' }}>{dossier.project_profile.project_name}</h1>
        <p className="muted">{demos[scanId] ? 'Precomputed offline demo' : 'Evidence-backed comparison'} · {dossier.verified_citations_count} citations verified</p>
      </section>
      <div className="grid-auto" style={{ alignItems: 'start' }}>
        <TrafficLight value={dossier.name_collision.traffic_light}
          matches={[...dossier.name_collision.exact_matches, ...dossier.name_collision.fuzzy_matches, ...dossier.name_collision.phonetic_matches]}
          alternatives={dossier.name_collision.safe_alternatives} />
        <NyxaScoreCard score={dossier.nyxa_score} verified={dossier.verified_citations_count}
          stripped={dossier.stripped_hallucinations_count} delta={scoreDelta} />
      </div>
      <section style={{ marginTop: 18 }} className="grid-auto">
        {dossier.analogies.length ? dossier.analogies.map(item => <AnalogyCard key={item.pattern_id} analogy={item} disclaimer={dossier.disclaimer} />) :
          <div className="panel" style={{ padding: 20 }}><div className="eyebrow">Cross-domain patterns</div><p className="muted">No corpus match reached the 0.72 similarity threshold.</p></div>}
        <section className="panel" style={{ padding: 20 }}>
          <div className="eyebrow">Landscape scout</div>
          {dossier.landscape.direct_competitors.length ? dossier.landscape.direct_competitors.map(repo => <article key={repo.url} style={{ paddingTop: 12 }}>
            <a href={repo.url} target="_blank" rel="noreferrer">{repo.name} ↗</a><div className="muted" style={{ fontSize: 12 }}>{repo.stars ?? 0} stars · {repo.limitations || 'No limitations section found.'}</div>
          </article>) : <p className="muted">No public competitors returned for this query.</p>}
        </section>
      </section>
      <section style={{ marginTop: 18 }}><KillKeepInjectMatrix items={dossier.kill_keep_inject} /></section>
      <section style={{ marginTop: 18 }}><div className="eyebrow" style={{ marginBottom: 8 }}>Before / after architecture</div><MermaidDiagram source={dossier.mermaid_before_after} /></section>
      <section className="grid-auto" style={{ marginTop: 18, alignItems: 'start' }}>
        <EnhancementBacklog items={dossier.ranked_backlog} />
        <div style={{ display: 'grid', gap: 14 }}>
          {!demos[scanId] && <BadgeSnippet scanId={scanId} />}
          {!demos[scanId] && <section className="panel" style={{ padding: 18 }}>
            <div className="eyebrow">Next iteration</div><p className="muted" style={{ fontSize: 13 }}>Apply backlog items, then compare a fresh scan against this score.</p>
            <ReScanButton scanId={scanId} onStarted={startRescan} />
          </section>}
        </div>
      </section>
      </>}
    </>}
  </main>;
}
