interface StatusBannerProps {
  type: "success" | "error" | "info";
  message: string;
}

const STYLES = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  error: "border-rose-200 bg-rose-50 text-rose-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
};

export function StatusBanner({ type, message }: StatusBannerProps) {
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${STYLES[type]}`}>
      {message}
    </div>
  );
}
