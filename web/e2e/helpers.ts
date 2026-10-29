import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export async function signInAs(page: Page, account: "Viewer" | "Manager") {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(account) }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

/** WCAG 2.2 A/AA rules via axe-core; fails the test on any violation. */
export async function expectAccessible(page: Page) {
  // Next streams <title> in after client-side navigations; require it, then audit.
  await expect(page).toHaveTitle(/OpsBoard/);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const summary = results.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
  expect(summary).toEqual([]);
}
