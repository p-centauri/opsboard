// Portfolio screenshots from the running production stack: `make screenshots`.
// Output: 1600x1200 PNGs (4:3) in docs/screenshots/.
import { chromium } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "http://edge";
const OUT = process.env.OUT_DIR ?? "/out";
const DESKTOP = { viewport: { width: 1280, height: 960 }, deviceScaleFactor: 1.25 }; // -> 1600x1200

async function signIn(page) {
  await page.goto(`${BASE}/login`);
  await page.getByRole("button", { name: /Manager/ }).click();
  await page.getByRole("heading", { name: "Dashboard" }).waitFor();
}

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(400); // fonts and chart layout
}

async function pickFirst(page, label, query) {
  // Exact searchbox: the results list's name ("<label> results") also contains the label.
  await page.getByRole("searchbox", { name: label, exact: true }).fill(query);
  const first = page.getByRole("list", { name: `${label} results` }).getByRole("button").first();
  await first.waitFor();
  await first.click();
}

async function richConfirmedOrderId(page) {
  const list = await (await page.request.get(`${BASE}/api/orders?status=confirmed&page_size=50`)).json();
  for (const order of list.items) {
    const detail = await (await page.request.get(`${BASE}/api/orders/${order.id}`)).json();
    if (detail.items.length >= 3) return order.id;
  }
  return list.items[0].id;
}

async function desktopShots(browser, scheme) {
  const context = await browser.newContext({ ...DESKTOP, colorScheme: scheme });
  const page = await context.newPage();
  await signIn(page);
  const shot = async (name) => {
    await settle(page);
    await page.screenshot({ path: `${OUT}/${name}-${scheme}.png` });
    console.log(`saved ${name}-${scheme}.png`);
  };

  await page.goto(`${BASE}/`);
  await page.locator(".recharts-area-curve").waitFor();
  await shot("dashboard");

  if (scheme === "light") {
    await page.goto(`${BASE}/orders`);
    await page.getByRole("table", { name: "Orders" }).waitFor();
    await shot("orders");

    await page.goto(`${BASE}/orders/${await richConfirmedOrderId(page)}`);
    await page.getByRole("button", { name: "Mark as shipped" }).waitFor();
    await shot("order-detail");

    await page.goto(`${BASE}/orders/new`);
    await pickFirst(page, "Find a customer", "Group");
    const lines = [["Scanner", "4"], ["Office Chair", "2"], ["Packing Tape", "25"]];
    for (const [index, [query, qty]] of lines.entries()) {
      // The picker's label changes once the order has its first line.
      await pickFirst(page, index === 0 ? "Add a product" : "Add another product", query);
      await page.getByLabel(/Quantity of/).last().fill(qty);
    }
    await page.getByRole("heading", { name: "New order" }).click(); // blur the last input
    await shot("order-editor");
  }
  await context.close();
}

async function mobileComposite(browser) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    colorScheme: "light",
  });
  const page = await context.newPage();
  await signIn(page);
  await page.locator(".recharts-area-curve").waitFor();
  await settle(page);
  const dashboard = (await page.screenshot()).toString("base64");
  await page.goto(`${BASE}/orders`);
  await page.getByRole("list", { name: "Orders" }).waitFor();
  await settle(page);
  const orders = (await page.screenshot()).toString("base64");
  await context.close();

  const canvas = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
  await canvas.setContent(`<!doctype html><html><body style="margin:0;height:1200px;display:flex;align-items:center;
    justify-content:center;gap:96px;background:#e9edf1;font-family:system-ui">
    ${[dashboard, orders]
      .map((png) => `<img src="data:image/png;base64,${png}" style="height:1040px;border-radius:44px;
        border:10px solid #131820;box-shadow:0 30px 60px rgba(19,24,32,.25)">`)
      .join("")}
  </body></html>`);
  await canvas.waitForTimeout(200);
  await canvas.screenshot({ path: `${OUT}/mobile-light.png` });
  console.log("saved mobile-light.png");
}

const browser = await chromium.launch();
try {
  await desktopShots(browser, "light");
  await desktopShots(browser, "dark");
  await mobileComposite(browser);
} finally {
  await browser.close();
}
