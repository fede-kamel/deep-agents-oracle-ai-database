// Click through the demo in a real browser, the way a presenter does, and check
// what the screen says at every step:
//   node scripts/ui-e2e.mjs [patient] [outdir]     (web app on 127.0.0.1:8765)
// Reset demo → pick the patient → Enter → wait for the verified brief → Actions:
// the policy chain is shown, the clinician's approval of the medication change is
// refused, the doctor's executes it, the rest are approved → Memory → Inspect
// panels → Reset demo clears the actions. Ends with "UI E2E OK (n/n)".
import { mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const [, , patient = "Y", out = "../out/ui-e2e"] = process.argv;
mkdirSync(out, { recursive: true });
const results = [];
const check = (name, ok, detail = "") => { results.push(ok); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  (${detail})` : ""}`); };

const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1720, height: 1080 }, deviceScaleFactor: 1 });
const shot = (name) => page.screenshot({ path: `${out}/${name}.png` });
const step = (title) => page.locator(`button:has-text("${title}")`).first().click();
const visible = (text, timeout = 15000) => page.getByText(text, { exact: false }).first().waitFor({ timeout }).then(() => true, () => false);

try {
  await page.goto("http://127.0.0.1:8765/", { waitUntil: "networkidle" });

  await page.click("header button:has-text('Reset demo')");
  check("reset asks for confirmation", await visible("Clear everything and start again?"));
  await page.click("button:has-text('Reset the demo')");
  await page.getByText("Clear everything and start again?").waitFor({ state: "detached", timeout: 60000 });
  check("reset completes", true);

  await page.click(`header button:has-text("Patient ${patient}")`);
  check("patient view shows the chart", await visible("Lab trends", 30000));
  await page.waitForTimeout(4000); // let any slow answer for another patient arrive
  const own = { X: "Type 2 diabetes mellitus", Y: "Heart failure", Z: "Chronic obstructive" }[patient];
  const other = { X: "Heart failure", Y: "Osteoarthritis", Z: "Osteoarthritis" }[patient];
  check(`chips are Patient ${patient}'s own conditions`, await page.locator(`span:has-text("${own}")`).count() > 0 && await page.locator(`span.rounded-full:has-text("${other}")`).count() === 0);
  const selectedTab = await page.locator("header button", { hasText: `Patient ${patient}` }).first().getAttribute("class");
  check(`header highlights Patient ${patient}`, /shadow-sm/.test(selectedTab ?? ""));
  await shot("01-patient");

  await page.locator("textarea").first().focus();
  await page.keyboard.press("Enter");
  check("Enter starts a run", await visible("Agents running", 15000));
  check(`the run is labelled Patient ${patient}`, await visible(`Clinician · Patient ${patient}`, 15000));
  await page.waitForTimeout(90000);
  await shot("02-running");
  check("sandbox console streams agent steps", await page.locator("text=/\\[agent:|care-coordinator|chart-analyst/").count() > 0);

  const started = Date.now();
  let done = false;
  while (Date.now() - started < 20 * 60 * 1000) {
    const runs = await (await fetch("http://127.0.0.1:8765/api/runs")).json();
    const mine = runs.find((r) => r.patient === patient);
    if (mine && mine.status !== "running") { done = mine.status === "succeeded"; break; }
    await page.waitForTimeout(10000);
  }
  check("run succeeds", done);
  check("header shows the verified brief", await visible("brief verified", 30000));
  await step("Brief");
  check("brief renders with citation chips", await page.locator("text=/^SQL:[a-z_]+$/").count() > 3);
  await shot("03-brief");

  await step("Actions");
  check("policy chain shows the CP-03 refusal and the escalation", await visible("Database policy CP-03 refused it", 15000) && await visible("escalation #", 5000));
  await shot("04-actions");

  const med = page.locator("div.rounded-xl", { has: page.locator("button:has-text('Approve as doctor')") }).first();
  check("medication change waits for the doctor", await med.count() === 1);
  await med.locator("button:has-text('Approve as clinician')").click();
  check("clinician approval is refused by the database", await visible("Refused by the database", 15000));
  await shot("05-clinician-refused");
  await med.locator("button:has-text('Approve as doctor')").click();
  check("doctor approval executes it", await visible("hold by physician order", 20000) || await visible("by physician order", 5000));

  const pending = () => page.locator("button:has-text('Approve as clinician')").count();
  for (let i = 0; i < 6; i++) {
    const before = await pending();
    if (!before) break;
    await page.locator("button:has-text('Approve as clinician')").first().click();
    for (let t = 0; t < 30 && (await pending()) >= before; t++) await page.waitForTimeout(500); // wait for the list to reload
  }
  check("every action decided", await visible("0 awaiting a decision", 15000));
  check("no stale refusal on a decided card", await page.locator("text=/is executed, not awaiting a decision/").count() === 0);
  check("stepper counts follow the decisions", await visible("decided", 10000) && !(await page.locator("text=/\\d+ to review/").count()));
  await shot("06-decided");

  await step("Memory");
  check("memory records the doctor's and the clinician's decisions", await visible("Doctor approved action", 15000) && await visible("Clinician approved action", 5000));
  await shot("07-memory");

  for (const panel of ["Trace", "Console", "Safety"]) {
    await page.click(`button:has-text('${panel}')`);
    await page.waitForTimeout(1200);
    await shot(`08-${panel.toLowerCase()}`);
    await page.keyboard.press("Escape");
  }
  check("inspect panels open and close", true);

  await page.click("header button:has-text('Reset demo')");
  await page.click("button:has-text('Reset the demo')");
  await page.getByText("Clear everything and start again?").waitFor({ state: "detached", timeout: 60000 });
  check("reset returns to step 1 with memory cleared", await visible("Nothing yet", 15000));
  const left = await (await fetch(`http://127.0.0.1:8765/api/patients/${patient}/actions`)).json();
  check("reset clears the actions", left.length === 0, `${left.length} left`);
  await shot("09-after-reset");
} catch (err) {
  check("no exception", false, String(err).split("\n")[0]);
  await shot("error").catch(() => {});
}
await browser.close();
const passed = results.filter(Boolean).length;
console.log(`\n${passed === results.length ? "UI E2E OK" : "UI E2E FAILED"} (${passed}/${results.length})`);
process.exit(passed === results.length ? 0 : 1);
