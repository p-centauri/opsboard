import type { Role, User } from "./api";

const RANK: Record<Role, number> = { viewer: 0, manager: 1, admin: 2 };

/** UI gating only (hide what the user can't do); the API enforces every permission. */
export function can(user: Pick<User, "role"> | undefined, minimum: Role): boolean {
  return user !== undefined && RANK[user.role] >= RANK[minimum];
}

/** Only same-site paths: never redirect to another origin after sign-in. */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return "/";
  return next;
}
