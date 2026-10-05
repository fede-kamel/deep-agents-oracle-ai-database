// Capture the guided flow, replaying a patient's latest finished run:
//   node scripts/demo-shots.mjs <patient> <outdir>
import { chromium } from "playwright-core";
const [, , patient = "Y", out = "../docs/screenshots"] = process.argv;
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1720, height: 1080 }, deviceScaleFactor: 2 });
const shot = async (name, wait = 1500) => { await page.waitForTimeout(wait); await page.screenshot({ path: `${out}/${name}.png` }); };
await page.goto("http://127.0.0.1:8765/", { waitUntil: "networkidle" });
await page.click(`header button:has-text("Patient ${patient}")`);
await page.waitForSelector("text=Lab trends", { timeout: 30000 });
await shot("01-patient", 6000);
const step = (title) => page.locator(`button:has-text("${title}")`).first().click();
await step("Agents at work"); await shot("02-agents-at-work", 2500);
await step("Brief"); await shot("03-brief", 2500);
await step("Actions"); await shot("04-actions", 2500);
await step("Memory"); await shot("05-memory", 2000);
await page.click("button:has-text('Trace')"); await page.waitForTimeout(800);
await page.click("button:has-text('expand all')"); await shot("06-inspect-trace", 1200);
await page.keyboard.press("Escape");
await page.click("button:has-text('Console')"); await shot("07-inspect-console", 1200);
await page.keyboard.press("Escape");
await page.click("button:has-text('Safety')"); await shot("08-inspect-safety", 1200);
await browser.close();
console.log("shots done");
