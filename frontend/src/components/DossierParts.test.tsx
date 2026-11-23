import { act, render, screen } from '@testing-library/react';
import { LivePollingStatus } from './LivePollingStatus';
import { MermaidDiagram, NyxaScoreCard, PipelineTracePanel, TrafficLight } from './DossierParts';

jest.mock('mermaid', () => ({
  __esModule: true,
  default: { initialize: jest.fn(), render: jest.fn(() => Promise.reject(new Error('parse error'))) },
}));

const score = {
  composite: 64, clarity: 70, landscape_coverage: 60, originality: 65, gap_opportunity: 75,
  enhancement_potential: 80, evidence_quality: 55, deterministic_points: 26, rubric_points: 38,
  projected_post_enhancement: 79, verdict: 'Opportunity to differentiate',
};

describe('Dossier components', () => {
  afterEach(() => { jest.useRealTimers(); jest.restoreAllMocks(); delete (global as unknown as { fetch?: unknown }).fetch; });

  it('renders collision status and available matches', () => {
    render(<TrafficLight value="RED" matches={['https://github.com/acme/tool']} alternatives={['ToolAtlas']} />);
    expect(screen.getByText('RED')).toBeInTheDocument();
    expect(screen.getByText(/acme\/tool/)).toBeInTheDocument();
  });

  it('shows Mermaid source when renderer rejects invalid syntax', async () => {
    render(<MermaidDiagram source="graph TD; broken[" />);
    expect(await screen.findByText('graph TD; broken[')).toBeInTheDocument();
  });

  it('shows re-scan score delta', () => {
    render(<NyxaScoreCard score={score} verified={4} stripped={1} delta={15} />);
    expect(screen.getByText('+15 vs parent scan')).toBeInTheDocument();
  });

  it('renders pipeline latency, model, and token trace', () => {
    render(<PipelineTracePanel traces={[{ subagent: 'Landscape Scout', duration_ms: 240, model_id: 'amazon.nova-lite-v1:0', input_tokens: 30, output_tokens: 12, estimated_usd: 0.0001, citations_verified: 2, citations_stripped: 1 }]} />);
    expect(screen.getByText('Landscape Scout')).toBeInTheDocument();
    expect(screen.getByText(/amazon\.nova-lite-v1:0/)).toBeInTheDocument();
    expect(screen.getByText(/30 in \/ 12 out/)).toBeInTheDocument();
  });

  it('polls until scan completes and reports progress', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.example.test';
    jest.useFakeTimers();
    const response = (status: string, progress: number) => Promise.resolve({ ok: true, json: () => Promise.resolve({ status, progress }) });
    const fetchMock = jest.fn().mockReturnValueOnce(response('DISCOVERING', 20) as Promise<Response>)
      .mockReturnValue(response('COMPLETED', 100) as Promise<Response>);
    global.fetch = fetchMock as unknown as typeof fetch;
    const onCompleted = jest.fn();
    render(<LivePollingStatus scanId="scan-1" onCompleted={onCompleted} onFailure={jest.fn()} />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(screen.getByText('20%')).toBeInTheDocument();
    await act(async () => { jest.advanceTimersByTime(1500); await Promise.resolve(); await Promise.resolve(); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(onCompleted).toHaveBeenCalledTimes(1);
  });
});
