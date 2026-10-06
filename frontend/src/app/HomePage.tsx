import { HealthCard } from "@/features/health/components/HealthCard";

/** The status page: is the API up. It needs no session. */
export function HomePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Docket status</h1>
      <HealthCard />
    </div>
  );
}
