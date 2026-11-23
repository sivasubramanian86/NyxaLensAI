'use client';

import { useEffect, useState } from 'react';

type ScanStatus = { status: string; progress?: number; completed_subagents?: Record<string, boolean> };
type Props = { scanId: string; onCompleted: () => void; onFailure: (message: string) => void };

const stages = [
  ['repo_scan', 'Repo AST'],
  ['name_collision', 'Name Collision'],
  ['landscape', 'Ecosystem Scout'],
  ['analogy', 'Systems Ontology'],
  ['enhancement', 'Grounded Synthesis'],
];

export function LivePollingStatus({ scanId, onCompleted, onFailure }: Props) {
  const [scan, setScan] = useState<ScanStatus>({ status: 'INITIALIZED', progress: 5 });

  useEffect(() => {
    const api = process.env.NEXT_PUBLIC_API_URL;
    let active = true;
    let checking = false;
    const poll = async () => {
      if (checking || !active || !api) return;
      checking = true;
      try {
        const response = await fetch(api + '/scans/' + scanId);
        if (!response.ok) throw new Error('Scan status returned ' + response.status);
        const status = await response.json() as ScanStatus;
        if (!active) return;
        setScan(status);
        if (status.status === 'COMPLETED') {
          active = false;
          onCompleted();
        } else if (status.status === 'FAILED') {
          active = false;
          onFailure('Scan failed. Check API and Lambda logs, then retry.');
        }
      } catch (error) {
        if (active) onFailure(error instanceof Error ? error.message : 'Could not read scan status.');
      } finally {
        checking = false;
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, [scanId, onCompleted, onFailure]);

  return (
    <section aria-live="polite" className="panel" style={{ padding: 22, marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div><div className="eyebrow">Live scan</div><div className="mono" style={{ marginTop: 6 }}>{scan.status}</div></div>
        <div className="mono gradient-text" style={{ fontSize: 28, fontWeight: 800 }}>{scan.progress ?? 0}%</div>
      </div>
      <div className="bar" style={{ margin: '14px 0 18px' }}><span style={{ width: (scan.progress ?? 0) + '%', transition: 'width .4s ease' }} /></div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
        {stages.map(([key, label], index) => {
          const done = scan.completed_subagents?.[key];
          const working = !done && index === 4 && scan.status === 'SYNTHESIZING';
          return <span key={key} className={'pill ' + (done ? 'pill-green' : working ? 'pill-cyan' : '')}>
            <span aria-hidden="true">{done ? '✓' : working ? '⚡' : '·'}</span> {label}
          </span>;
        })}
      </div>
    </section>
  );
}
