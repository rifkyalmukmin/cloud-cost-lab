import { DashboardContent } from "@/components/dashboard/dashboard-content";

export default function CostPage() {
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Cost Explorer</h1>
        <p className="text-sm text-muted-foreground">
          Analyze cloud costs by service, project, and environment
        </p>
      </div>
      <DashboardContent />
    </main>
  );
}
