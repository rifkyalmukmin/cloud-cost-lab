import { BudgetContent } from "@/components/budget/budget-content";

export default function BudgetPage() {
  return (
    <main className="flex-1 p-4 sm:p-6 max-w-7xl mx-auto w-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Budget</h1>
        <p className="text-sm text-muted-foreground">
          Spend against the monthly limit. Status is a word, not only a color.
        </p>
      </div>
      <BudgetContent />
    </main>
  );
}
