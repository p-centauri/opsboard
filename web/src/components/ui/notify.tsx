"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

type Notify = (message: string) => void;
const NotifyContext = createContext<Notify | null>(null);

/**
 * Short confirmations ("Order confirmed") in a polite live region. Only for success
 * feedback: errors the user must act on are shown inline next to what failed.
 */
export function NotifyProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const notify = useCallback<Notify>((text) => {
    setMessage(text);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setMessage(""), 5000);
  }, []);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  return (
    <NotifyContext.Provider value={notify}>
      {children}
      <div aria-live="polite" role="status" className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
        {message && (
          <p className="pointer-events-auto rounded-md bg-fg px-4 py-2.5 text-sm text-bg shadow-lg">{message}</p>
        )}
      </div>
    </NotifyContext.Provider>
  );
}

export function useNotify(): Notify {
  const notify = useContext(NotifyContext);
  if (!notify) throw new Error("useNotify must be used inside <NotifyProvider>");
  return notify;
}
