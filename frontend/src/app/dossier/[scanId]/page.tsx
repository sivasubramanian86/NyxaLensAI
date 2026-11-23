'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LivePollingStatus } from '@/components/LivePollingStatus';
import { AppHeader } from '@/components/AppHeader';
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
  const isDemo = !!demos[scanId];

  return <>
    <AppHeader right={<><span className="pill mono" title="Scan id">{scanId}</span><a className="button" href="/" style={{ padding: '7px 14px', textDecoration: 'none', fontSize: 14 }}>+ New scan</a></>} />
    <main className="shell" style={{ paddingTop: 36, paddingBottom: 72 }}>
      {rescanId && <LivePollingStatus scanId={rescanId} onCompleted={rescanComplete} onFailure={rescanFailed} />}
      {!dossier && !error && <div className="stack" aria-busy="true">
        <div className="panel shimmer" style={{ height: 120 }} />
        <div className="grid-2"><div className="panel shimmer" style={{ height: 320 }} /><div className="panel shimmer" style={{ height: 320 }} /></div>
        <span className="muted" style={{ fontSize: 13 }}>Loading dossier…</span>
      </div>}
      {error && <p role="alert" className="panel" style={{ color: '#fda4af', padding: 18 }}>{error}</p>}
      {dossier && <>
        <section style={{ marginBottom: 26 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
            <span className="pill pill-cyan">Architectural differentiation map</span>
            <span className="pill">{isDemo ? 'Precomputed offline demo' : 'Evidence-backed comparison'}</span>
            <span className="pill pill-green">✓ {dossier.verified_citations_count} citations verified</span>
            {dossier.stripped_hallucinations_count > 0 && <span className="pill pill-amber">{dossier.stripped_hallucinations_count} unverified removed</span>}
          </div>
          <h1 className="gradient-text" style={{ fontSize: 'clamp(36px, 5.5vw, 62px)', letterSpacing: '-.045em', lineHeight: 1.04, fontWeight: 800, paddingBottom: 4 }}>{dossier.project_profile.project_name}</h1>
          <div className="seg" role="tablist" aria-label="Dossier views" style={{ marginTop: 22 }}>
            <button className={activeTab === 'overview' ? 'button active' : 'button'} onClick={() => setActiveTab('overview')}>Overview</button>
            <button className={activeTab === 'trace' ? 'button active' : 'button'} onClick={() => setActiveTab('trace')}>Pipeline Trace</button>
          </div>
        </section>

        {activeTab === 'trace' ? <PipelineTracePanel traces={dossier.pipeline_trace ?? []} /> : <div className="stack">
          <div className="grid-2">
            <div className="stack">
              <TrafficLight value={dossier.name_collision.traffic_light}
                matches={[...dossier.name_collision.exact_matches, ...dossier.name_collision.fuzzy_matches, ...dossier.name_collision.phonetic_matches]}
                alternatives={dossier.name_collision.safe_alternatives} />
              <section className="panel" style={{ padding: 22 }}>
                <div className="section-title"><div className="eyebrow">Landscape scout</div><span className="pill mono">{dossier.landscape.direct_competitors.length} found</span></div>
                {dossier.landscape.direct_competitors.length ? dossier.landscape.direct_competitors.map(repo => <article key={repo.url} className="inset" style={{ padding: 14, marginTop: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                    <a href={repo.url} target="_blank" rel="noreferrer" style={{ fontWeight: 700 }}>{repo.name} ↗</a>
                    <span className="pill pill-amber">★ {(repo.stars ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="muted" style={{ fontSize: 13, marginTop: 8, lineHeight: 1.5 }}>{repo.limitations || 'No limitations section found.'}</div>
                </article>) : <p className="muted">No public competitors returned for this query.</p>}
              </section>
            </div>
            <NyxaScoreCard score={dossier.nyxa_score} verified={dossier.verified_citations_count}
              stripped={dossier.stripped_hallucinations_count} delta={scoreDelta} />
          </div>

          <section className="grid-auto" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))' }}>
            {dossier.analogies.length ? dossier.analogies.map(item => <AnalogyCard key={item.pattern_id} analogy={item} disclaimer={dossier.disclaimer} />) :
              <div className="panel" style={{ padding: 22 }}><div className="eyebrow">Cross-domain patterns</div><p className="muted">No corpus match reached the 0.72 similarity threshold.</p></div>}
          </section>

          <KillKeepInjectMatrix items={dossier.kill_keep_inject} />

          <section><div className="section-title"><div className="eyebrow">Before / after architecture</div></div><MermaidDiagram source={dossier.mermaid_before_after} /></section>

          <section className="grid-2">
            <EnhancementBacklog items={dossier.ranked_backlog} />
            <div className="stack">
              {!isDemo && <BadgeSnippet scanId={scanId} />}
              {!isDemo && <section className="panel" style={{ padding: 22 }}>
                <div className="eyebrow">Next iteration</div><p className="muted" style={{ fontSize: 13 }}>Apply backlog items, then compare a fresh scan against this score.</p>
                <ReScanButton scanId={scanId} onStarted={startRescan} />
              </section>}
              {isDemo && <section className="panel" style={{ padding: 22 }}>
                <div className="eyebrow">About this demo</div>
                <p className="muted" style={{ fontSize: 13, lineHeight: 1.6 }}>This dossier is stored sample data. Live scans, badges and re-scan deltas need the AWS backend.</p>
              </section>}
            </div>
          </section>
        </div>}
      </>}
    </main>
  </>;
}
