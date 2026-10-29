import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 text-center">
      <p className="text-sm font-medium text-muted">404</p>
      <h1 className="mt-1 text-2xl font-semibold">This page doesn’t exist</h1>
      <Link href="/" className="mt-4 text-accent hover:underline">
        Go to the dashboard
      </Link>
    </main>
  );
}
