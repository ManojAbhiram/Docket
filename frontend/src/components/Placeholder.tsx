import { Notice } from "@/components/Notice";

/** A page whose data wiring is the next task. It names itself so a route test can find it. */
export function Placeholder({ title }: { title: string }) {
  return (
    <div className="space-y-4">
      <h1 className="text-[25px]">{title}</h1>
      <Notice tone="info" title="This screen is not connected to the API yet." />
    </div>
  );
}
