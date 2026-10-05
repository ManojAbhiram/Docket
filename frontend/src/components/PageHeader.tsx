import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string | undefined;
  actions?: ReactNode;
}

/** The title of a screen, its one-line context and its primary actions. */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-1">
        <h1 className="text-[25px]">{title}</h1>
        {description && <p className="text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
