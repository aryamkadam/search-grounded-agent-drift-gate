import { CompareWorkspace } from "@/components/compare/compare-workspace";

interface ComparePageProps {
  searchParams: Promise<{
    old?: string;
    new?: string;
  }>;
}

export default async function ComparePage({
  searchParams,
}: ComparePageProps) {
  const params = await searchParams;

  return (
    <CompareWorkspace
      initialOldId={params.old ?? "cap_001"}
      initialNewId={params.new ?? "cap_009"}
    />
  );
}