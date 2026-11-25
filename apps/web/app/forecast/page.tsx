import { ForecastContent } from "@/components/forecast/forecast-content";

export default function ForecastPage() {
  return (
    <main className="flex-1 p-4 sm:p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Forecast</h1>
        <p className="text-sm text-muted-foreground">
          A range for the next 30 days. This is a projection, not an exact future cost.
        </p>
      </div>
      <ForecastContent />
    </main>
  );
}
