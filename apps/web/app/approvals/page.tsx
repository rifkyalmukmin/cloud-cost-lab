import { ApprovalsContent } from "@/components/approvals/approvals-content";

export default function ApprovalsPage() {
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Approvals</h1>
        <p className="text-sm text-muted-foreground">
          Human approval before a recommendation is implemented. The actor is the configured API principal.
        </p>
      </div>
      <ApprovalsContent />
    </main>
  );
}
