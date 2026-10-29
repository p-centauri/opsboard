import type { Metadata } from "next";
import { Suspense } from "react";

import { AuditLog } from "./audit-log";

export const metadata: Metadata = { title: "Audit log" };

export default function Page() {
  return (
    <Suspense>
      <AuditLog />
    </Suspense>
  );
}
