interface PageHeaderProps {
  title: string;
  subtitle: string;
  moduleLabel: string;
}

export function PageHeader({ title, subtitle, moduleLabel }: PageHeaderProps) {
  return (
    <div className="mb-6 border-b border-surface-200 pb-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">
        {moduleLabel}
      </p>
      <h1 className="mt-1 text-2xl font-bold text-surface-900">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
    </div>
  );
}
