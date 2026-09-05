import { Badge } from "@/components/ui/badge";
import type { Environment } from "@/lib/api";

const ENV_STYLES: Record<Environment, string> = {
  production: "border-sky-500/40 text-sky-600 dark:text-sky-400",
  staging: "border-amber-500/40 text-amber-600 dark:text-amber-400",
  development: "border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
};

export function EnvironmentBadge({ environment }: { environment: Environment }) {
  return (
    <Badge variant="outline" className={ENV_STYLES[environment]}>
      {environment}
    </Badge>
  );
}
