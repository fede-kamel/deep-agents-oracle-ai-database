import { chromium } from "playwright-core";
const [,, mode = "idle", out = "../out/shots/idle.png", patient = "X"] = process.argv;
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1680, height: 1050 }, deviceScaleFactor: 2 });
await page.goto("http://127.0.0.1:8765/", { waitUntil: "networkidle" });
await page.waitForSelector("text=Patient X");
if (patient !== "X") await page.click(`button:has-text("Patient ${patient}")`);
if (mode === "idle") await page.waitForSelector("text=Lab trends", { timeout: 30000 }).catch(() => {});
if (mode === "run") {
  await page.click("text=Run in sandbox");
  const shots = [25, 55];
  let t = 0;
  for (const s of shots) { await page.waitForTimeout((s - t) * 1000); t = s; await page.screenshot({ path: out.replace(".png", `-${s}s.png`) }); }
  await page.waitForSelector("article.brief", { timeout: 600000 });
  await page.waitForTimeout(2500);
}
await page.screenshot({ path: out });
await browser.close();
