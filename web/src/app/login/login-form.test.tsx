import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "./login-form";

const replace = vi.fn();
let next: string | null = null;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => ({ get: () => next }),
}));

function renderForm(demoPassword: string | null = null) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LoginForm demoPassword={demoPassword} />
    </QueryClientProvider>,
  );
}

function apiReturns(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const user = { id: 1, email: "a@b.co", role: "viewer", is_active: true, created_at: "2026-01-01T00:00:00Z" };

beforeEach(() => {
  replace.mockReset();
  next = null;
});

describe("LoginForm", () => {
  it("validates before calling the API", async () => {
    const fetchMock = apiReturns(200, user);
    renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter your email")).toBeInTheDocument();
    expect(screen.getByText("Enter your password")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveFocus();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("explains wrong credentials and keeps what was typed", async () => {
    apiReturns(401, { error: { code: "invalid_credentials", message: "Email or password is incorrect" } });
    renderForm();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("That email and password don't match");
    expect(screen.getByLabelText("Email")).toHaveValue("a@b.co");
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the rate-limit message from the API", async () => {
    apiReturns(429, { error: { code: "too_many_attempts", message: "Too many failed sign-ins. Try again later." } });
    renderForm();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many failed sign-ins");
  });

  it("returns to the page the user came from, but never off-site", async () => {
    apiReturns(200, user);
    next = "//evil.example/phish";
    renderForm();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
  });

  it("signs in with a demo account in one click", async () => {
    const fetchMock = apiReturns(200, user);
    next = "/orders";
    renderForm("demo-pw");
    await userEvent.click(screen.getByRole("button", { name: /Manager/ }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/orders"));
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body as string)).toEqual({ email: "manager@demo.local", password: "demo-pw" });
  });

  it("hides demo buttons outside the demo", () => {
    renderForm(null);
    expect(screen.queryByText("Try the demo")).not.toBeInTheDocument();
  });
});
