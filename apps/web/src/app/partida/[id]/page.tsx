import Interrogation from "@/components/Interrogation";

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <Interrogation matchId={id} />;
}
