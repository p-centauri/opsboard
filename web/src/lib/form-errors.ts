import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { isApiError } from "./api";

/**
 * Puts the API's per-field errors (422 validation, 409 conflict on e.g. `sku`) next to the
 * matching inputs. Returns the error message when it couldn't be tied to a field.
 */
export function applyServerErrors<T extends FieldValues>(error: unknown, setError: UseFormSetError<T>, fields: readonly Path<T>[]): string | null {
  if (!isApiError(error)) return "Couldn't save. Check your connection and try again.";
  let placed = false;
  for (const [field, message] of Object.entries(error.fields)) {
    if ((fields as readonly string[]).includes(field)) {
      setError(field as Path<T>, { type: "server", message }, { shouldFocus: !placed });
      placed = true;
    }
  }
  return placed ? null : error.message;
}
