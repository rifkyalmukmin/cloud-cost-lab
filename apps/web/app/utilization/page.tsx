import { UtilizationContent } from "@/components/utilization/utilization-content";

export default function UtilizationPage() {
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Utilization Analysis</h1>
        <p className="text-sm text-muted-foreground">
          Resource utilization patterns with cost correlation
        </p>
      </div>
      <UtilizationContent />
    </main>
  );
}
