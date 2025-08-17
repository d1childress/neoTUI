import { promisify } from "node:util";
import { exec as _exec } from "node:child_process";
import * as dns from "node:dns/promises";
import net from "node:net";

const exec = promisify(_exec);

export async function ping(host: string, count = 4) {
  const isWin = process.platform === "win32";
  const cmd = isWin ? `ping -n ${count} ${host}` : `ping -c ${count} ${host}`;
  try {
    const { stdout } = await exec(cmd, { timeout: 15_000, maxBuffer: 10_000_000 });
    return stdout.trim();
  } catch (e: any) {
    return `Ping failed: ${e?.stderr || e?.message}`;
  }
}

export async function dnsLookup(name: string) {
  const addrs = await dns.lookup(name, { all: true }).catch(e => ({ error: e.message }));
  const a = await dns.resolve(name).catch(() => []);
  const aaaa = await dns.resolve6(name).catch(() => []);
  const mx = await dns.resolveMx(name).catch(() => []);
  return { lookup: addrs, A: a, AAAA: aaaa, MX: mx };
}

export async function httpCheck(urlOrHost: string) {
  // normalize
  const url = urlOrHost.startsWith("http") ? urlOrHost : `https://${urlOrHost}`;
  const start = performance.now();
  try {
    const res = await fetch(url, { method: "GET" }); // Bun fetch
    const ms = Math.round(performance.now() - start);
    return {
      url,
      status: `${res.status} ${res.statusText}`,
      ok: res.ok,
      timeMs: ms,
      headers: Object.fromEntries(Array.from(res.headers.entries()).slice(0, 20))
    };
  } catch (e: any) {
    const ms = Math.round(performance.now() - start);
    return { url, error: e.message, timeMs: ms };
  }
}

export async function traceroute(host: string, maxHops = 20) {
  const isWin = process.platform === "win32";
  const cmd = isWin ? `tracert -d -h ${maxHops} ${host}` : `traceroute -n -m ${maxHops} ${host}`;
  try {
    const { stdout } = await exec(cmd, { timeout: 60_000, maxBuffer: 10_000_000 });
    return stdout.trim();
  } catch (e: any) {
    return `Traceroute failed: ${e?.stderr || e?.message}`;
  }
}

export async function portScan(host: string, ports: number[], timeoutMs = 500) {
  const results: { port: number; open: boolean }[] = [];
  const check = (port: number) =>
    new Promise<void>((resolve) => {
      const socket = new net.Socket();
      let done = false;
      const finish = (open: boolean) => {
        if (done) return;
        done = true;
        socket.destroy();
        results.push({ port, open });
        resolve();
      };
      socket.setTimeout(timeoutMs);
      socket.once("connect", () => finish(true));
      socket.once("timeout", () => finish(false));
      socket.once("error", () => finish(false));
      socket.connect(port, host);
    });

  // Limit concurrency a bit
  const batch = 100;
  for (let i = 0; i < ports.length; i += batch) {
    await Promise.all(ports.slice(i, i + batch).map(check));
  }
  return results.filter(r => r.open).sort((a, b) => a.port - b.port);
}