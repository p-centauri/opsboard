import type { Metadata } from "next";
import { Suspense } from "react";

import { UsersAdmin } from "./users-admin";

export const metadata: Metadata = { title: "Users" };

export default function Page() {
  return (
    <Suspense>
      <UsersAdmin />
    </Suspense>
  );
}
