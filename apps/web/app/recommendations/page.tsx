import { RecommendationsContent } from "@/components/recommendations/recommendations-content";

export default function RecommendationsPage() {
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Cost Recommendations</h1>
        <p className="text-sm text-muted-foreground">
          Evidence-based optimization opportunities
        </p>
      </div>
      <RecommendationsContent />
    </main>
  );
}
