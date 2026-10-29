import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type Ref } from "react";

export const controlClass =
  "block w-full min-h-11 rounded-md border border-line-strong bg-surface px-3 text-sm text-fg " +
  "placeholder:text-muted disabled:bg-surface-muted disabled:text-muted " +
  "aria-[invalid=true]:border-danger";

interface FieldProps {
  label: string;
  /** Error from client validation or the API's `fields`; shown under the control and announced. */
  error?: string;
  hint?: string;
  className?: string;
  /** Visually hide the label (it stays available to screen readers). */
  hideLabel?: boolean;
  children: (control: { id: string; "aria-invalid": boolean; "aria-describedby"?: string }) => ReactNode;
}

/** Label + control + hint + error, wired together for assistive tech. */
export function Field({ label, error, hint, className = "", hideLabel = false, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : "mb-1.5 block text-sm font-medium"}>
        {label}
      </label>
      {children({ id, "aria-invalid": Boolean(error), "aria-describedby": describedBy })}
      {hint && !error && (
        <p id={hintId} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1.5 text-sm text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function Input({ className = "", ref, ...props }: InputHTMLAttributes<HTMLInputElement> & { ref?: Ref<HTMLInputElement> }) {
  return <input ref={ref} className={`${controlClass} ${className}`} {...props} />;
}

export function Select({ className = "", ref, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { ref?: Ref<HTMLSelectElement> }) {
  return <select ref={ref} className={`${controlClass} pr-8 ${className}`} {...props} />;
}
