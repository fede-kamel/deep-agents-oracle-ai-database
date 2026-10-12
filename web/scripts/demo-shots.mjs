// Capture the five tabs, the timeline, the console and the safety panel,
// replaying a patient's latest finished run:
//   node scripts/demo-shots.mjs <patient> <outdir>        (web app on 127.0.0.1:8765)
import { chromium } from "playwright-core";
const [, , patient = "Y", out = "../docs/screenshots"] = process.argv;
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1720, height: 1080 }, deviceScaleFactor: 2 });
const shot = async (name, wait = 1500) => { await page.waitForTimeout(wait); await page.screenshot({ path: `${out}/${name}.png` }); };
const tab = (label) => page.locator(`nav[role=tablist] button:has-text("${label}")`).first().click();
await page.goto("http://127.0.0.1:8765/", { waitUntil: "networkidle" });
await page.click(`header button:has-text("Patient ${patient}")`);
await page.waitForSelector("text=Lab trends", { timeout: 30000 });
await shot("01-patient", 6000);
await tab("Agents"); await shot("02-agents-at-work", 2500);
await page.click("[role=tab]:has-text('Timeline')"); await shot("06-timeline", 1200);
await page.click("button:has-text('All')"); await page.click("section button[title='Full screen']"); await shot("07-console", 1200);
await page.keyboard.press("Escape"); await page.waitForTimeout(500);
await tab("Brief"); await shot("03-brief", 2500);
await tab("Actions"); await shot("04-actions", 2500);
await tab("Memory"); await shot("05-memory", 2000);
await page.click("header button:has-text('Safety')"); await shot("08-safety", 1200);
await browser.close();
console.log("shots done");
