/** Save a file from the API the way a click on a link would, with feedback:
 * the bytes are fetched first, so a missing run or a server error is reported
 * instead of opening a page of JSON, or doing nothing at all. Resolves with
 * the name the server gave the file and its size. */
export async function download(url: string, fallbackName: string): Promise<{ name: string; bytes: number }> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await reason(r));
  const blob = await r.blob();
  const name = /filename="?([^";]+)"?/.exec(r.headers.get("content-disposition") ?? "")?.[1] ?? fallbackName;
  const href = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href, download: name, rel: "noopener" });
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(href), 10_000);
  return { name, bytes: blob.size };
}

async function reason(r: Response): Promise<string> {
  const text = await r.text();
  try { return `${r.status}: ${JSON.parse(text).detail ?? text}`; } catch { return `${r.status}: ${text.slice(0, 200) || r.statusText}`; }
}

export function fmtBytes(n: number): string {
  return n < 1024 ? `${n} B` : n < 1024 * 1024 ? `${Math.round(n / 1024)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}
