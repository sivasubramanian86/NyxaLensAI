import { DossierView } from '@/components/DossierView';
import { DEMO_IDS } from '@/lib/demo-ids';

// Static export pre-renders only the stored demo dossiers.
export const dynamicParams = false;

export function generateStaticParams() {
  return DEMO_IDS.map(scanId => ({ scanId }));
}

export default function DossierPage({ params }: { params: { scanId: string } }) {
  return <DossierView scanId={params.scanId} />;
}
