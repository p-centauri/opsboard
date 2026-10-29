import { expect, test, type Page } from "@playwright/test";

import { expectAccessible, signInAs } from "./helpers";

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

for (const width of [320, 412]) {
  test(`phone at ${width}px: no sideways scrolling, menu works`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await signInAs(page, "Manager");
    await expectNoHorizontalScroll(page);

    await page.getByRole("button", { name: "Menu" }).click();
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Orders" }).click();
    await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByRole("list", { name: "Orders" })).toBeVisible(); // card layout
    await expectNoHorizontalScroll(page);
    await expectAccessible(page);

    await page.getByRole("list", { name: "Orders" }).getByRole("link").first().click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText("ORD-");
    await expectNoHorizontalScroll(page);
  });
}
