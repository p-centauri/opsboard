import { expect, test } from "@playwright/test";

import { expectAccessible, signInAs } from "./helpers";

test("login page is accessible and rejects a wrong password", async ({ page }) => {
  await page.goto("/login");
  await expectAccessible(page);
  // A fresh, non-existent email each run: failed sign-ins count toward the per email+IP rate
  // limit, and using a demo account here would lock it for the tests that follow. Unknown
  // emails and wrong passwords get the identical response, so this covers both.
  await page.getByLabel("Email").fill(`nobody-${Date.now()}@test.local`);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  // Scoped by text: Next's route announcer is also role="alert".
  await expect(page.getByRole("alert").filter({ hasText: "don't match" })).toBeVisible();
});

test("signed-out visitors are sent to sign in, then back", async ({ page }) => {
  await page.goto("/orders?status=draft");
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByRole("button", { name: /Viewer/ }).click();
  await expect(page).toHaveURL(/\/orders\?status=draft$/);
});

test("dashboard shows figures, chart and breakdowns", async ({ page }) => {
  await signInAs(page, "Viewer");
  await expect(page.getByText("Revenue", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("img", { name: /Revenue over time/ })).toBeVisible();
  await expect(page.getByRole("list", { name: "Orders by status" })).toBeVisible();
  await page.getByLabel("Date range").selectOption("90");
  await expect(page).toHaveURL(/range=90/);
  await expectAccessible(page);
});

test("orders: filters live in the URL", async ({ page }) => {
  await signInAs(page, "Viewer");
  await page.getByRole("link", { name: "Orders" }).first().click();
  await page.getByRole("checkbox", { name: "Shipped" }).check();
  await expect(page).toHaveURL(/status=shipped/);
  const rows = page.getByRole("table", { name: "Orders" }).getByRole("row");
  await expect(rows.nth(1)).toContainText("Shipped");
  await page.getByLabel("Search").fill("ord-0000001");
  await expect(page).toHaveURL(/q=ord-0000001/);
  await expectAccessible(page);
});

test("viewer can't see write actions", async ({ page }) => {
  await signInAs(page, "Viewer");
  await page.goto("/orders");
  await expect(page.getByRole("heading", { name: "Orders" })).toBeVisible();
  await expect(page.getByRole("link", { name: "New order" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0);
});

test("manager creates, confirms and cancels an order; stock follows", async ({ page }) => {
  await signInAs(page, "Manager");
  await page.goto("/orders/new");
  await expectAccessible(page);

  await page.getByLabel("Find a customer").fill("inc");
  await page.getByRole("list", { name: "Find a customer results" }).getByRole("button").first().click();
  await page.getByLabel("Add a product").fill("SKU-00001");
  await page.getByRole("list", { name: "Add a product results" }).getByRole("button").first().click();
  await page.getByLabel(/Quantity of/).fill("2");
  await page.getByRole("button", { name: "Create draft" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toContainText("ORD-");
  await expect(page.getByText("Draft", { exact: true })).toBeVisible();
  const orderUrl = page.url();
  const stockBefore = (await (await page.request.get("/api/products/1")).json()).stock_qty as number;

  await page.getByRole("button", { name: "Confirm order" }).click();
  await expect(page.getByText("Confirmed", { exact: true })).toBeVisible();
  expect((await (await page.request.get("/api/products/1")).json()).stock_qty).toBe(stockBefore - 2);

  await page.getByRole("button", { name: "Cancel order" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expectAccessible(page);
  await dialog.getByRole("button", { name: "Cancel order" }).click();
  await expect(page.getByText("Cancelled", { exact: true })).toBeVisible();
  expect((await (await page.request.get("/api/products/1")).json()).stock_qty).toBe(stockBefore);
  expect(page.url()).toBe(orderUrl);
});
