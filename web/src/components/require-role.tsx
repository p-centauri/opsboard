"use client";

import type { ReactNode } from "react";

import { ButtonLink } from "@/components/ui/button";
import { Notice } from "@/components/ui/feedback";
import type { Role } from "@/lib/api";
import { useMe } from "@/lib/queries";
import { can } from "@/lib/roles";

/**
 * For pages reached by URL that the user's role can't use: explain instead of showing a form
 * whose submit would fail. UX only; the API enforces the role regardless.
 */
export function RequireRole({ role, back, children }: { role: Role; back: { href: string; label: string }; children: ReactNode }) {
  const me = useMe();
  if (me.data && !can(me.data, role)) {
    return (
      <Notice tone="info" title={`This needs the ${role} role`} action={<ButtonLink href={back.href} size="sm">{back.label}</ButtonLink>}>
        You can view everything, but only a {role} can make changes here.
      </Notice>
    );
  }
  return <>{children}</>;
}
