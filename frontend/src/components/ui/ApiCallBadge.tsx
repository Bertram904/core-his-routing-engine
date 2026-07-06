/** Hiển thị rõ API endpoint mà section/màn hình đang gọi. */
interface ApiCallBadgeProps {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  description?: string;
}

const METHOD_COLORS: Record<ApiCallBadgeProps["method"], string> = {
  GET: "bg-emerald-100 text-emerald-800",
  POST: "bg-blue-100 text-blue-800",
  PUT: "bg-amber-100 text-amber-800",
  PATCH: "bg-orange-100 text-orange-800",
  DELETE: "bg-rose-100 text-rose-800",
};

export function ApiCallBadge({
  method,
  path,
  description,
}: ApiCallBadgeProps) {
  return (
    <div className="mb-4 rounded-lg border border-dashed border-surface-200 bg-surface-50 px-3 py-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className={`rounded px-2 py-0.5 font-mono font-bold ${METHOD_COLORS[method]}`}
        >
          {method}
        </span>
        <code className="font-mono text-surface-800">{path}</code>
      </div>
      {description ? (
        <p className="mt-1 text-xs text-slate-500">{description}</p>
      ) : null}
    </div>
  );
}
