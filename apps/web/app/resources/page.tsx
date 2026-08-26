import { ResourceListContent } from "@/components/resources/resource-list-content";

export default function ResourcesPage() {
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Resource Inventory</h1>
        <p className="text-sm text-muted-foreground">
          Cloud resources with cost and utilization data
        </p>
      </div>
      <ResourceListContent />
    </main>
  );
}
