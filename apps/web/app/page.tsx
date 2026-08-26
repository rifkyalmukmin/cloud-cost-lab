import { DashboardContent } from "@/components/dashboard/dashboard-content";

export default function Home() {
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Cloud Cost Lab</h1>
        <p className="text-sm text-muted-foreground">
          GCP FinOps &amp; Cloud Cost Optimization Dashboard
        </p>
      </div>
      <DashboardContent />
    </main>
  );
}
