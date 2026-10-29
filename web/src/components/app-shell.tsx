"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useId, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Role, User } from "@/lib/api";
import { titleCase } from "@/lib/format";
import { useLogout } from "@/lib/queries";
import { can } from "@/lib/roles";

const NAV: { href: string; label: string; role: Role }[] = [
  { href: "/", label: "Dashboard", role: "viewer" },
  { href: "/orders", label: "Orders", role: "viewer" },
  { href: "/customers", label: "Customers", role: "viewer" },
  { href: "/products", label: "Products", role: "viewer" },
  { href: "/admin/users", label: "Users", role: "admin" },
  { href: "/admin/audit", label: "Audit log", role: "admin" },
];

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function NavLinks({ user, pathname, onNavigate }: { user: User; pathname: string; onNavigate?: () => void }) {
  return (
    <ul className="space-y-0.5">
      {NAV.filter((item) => can(user, item.role)).map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
              className={`flex min-h-10 items-center rounded-md px-3 text-sm ${
                active ? "bg-accent-soft font-semibold text-fg" : "text-muted hover:bg-surface-muted hover:text-fg"
              }`}
            >
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex min-h-10 items-center gap-2 font-semibold">
      <svg viewBox="0 0 32 32" className="size-7" aria-hidden="true">
        <rect width="32" height="32" rx="7" className="fill-accent" />
        <path d="M8 22V12m8 10V8m8 14v-6" className="stroke-on-accent" strokeWidth="3" strokeLinecap="round" />
      </svg>
      OpsBoard
    </Link>
  );
}

function Account({ user }: { user: User }) {
  const router = useRouter();
  const logout = useLogout();
  return (
    <div className="border-t border-line pt-4 text-sm">
      <p className="truncate font-medium" title={user.email}>
        {user.email}
      </p>
      <p className="text-muted">{titleCase(user.role)}</p>
      <Button
        size="sm"
        className="mt-3 w-full"
        pending={logout.isPending}
        onClick={() => logout.mutate(undefined, { onSettled: () => router.replace("/login") })}
      >
        Sign out
      </Button>
    </div>
  );
}

export function AppShell({ user, children }: { user: User; children: ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15rem_1fr]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 border-b border-line bg-surface md:hidden">
        <div className="flex items-center justify-between px-4 py-2">
          <Brand />
          <Button
            size="sm"
            variant="ghost"
            aria-expanded={menuOpen}
            aria-controls={menuId}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? "Close" : "Menu"}
          </Button>
        </div>
        {menuOpen && (
          <nav id={menuId} aria-label="Main" className="space-y-4 border-t border-line px-4 py-3">
            <NavLinks user={user} pathname={pathname} onNavigate={() => setMenuOpen(false)} />
            <Account user={user} />
          </nav>
        )}
      </header>

      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh flex-col gap-6 border-r border-line bg-surface px-3 py-4 md:flex">
        <div className="px-2">
          <Brand />
        </div>
        <nav aria-label="Main" className="flex-1">
          <NavLinks user={user} pathname={pathname} />
        </nav>
        <div className="px-2">
          <Account user={user} />
        </div>
      </aside>

      <main id="main" tabIndex={-1} className="min-w-0 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
