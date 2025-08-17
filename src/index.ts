import { createCliRenderer, TextRenderable } from "@opentui/core";
import * as readline from "node:readline";
import { dnsLookup, httpCheck, ping, traceroute, portScan } from "./tasks";

// ---- config ----
const SIDEBAR_WIDTH = 35;        // increased for better spacing
const MAX_CONTENT_LINES = 2000;  // safety when rendering huge outputs

// ---- Terminal capability detection ----
const hasColorSupport = () => {
  return process.stdout.isTTY && (
    process.env.COLORTERM ||
    process.env.TERM?.includes('color') ||
    process.env.TERM === 'xterm-256color' ||
    process.env.FORCE_COLOR
  );
};

const hasUnicodeSupport = () => {
  const term = process.env.TERM || '';
  const lang = process.env.LANG || process.env.LC_ALL || '';
  return term.includes('xterm') || lang.includes('UTF-8') || process.env.FORCE_UNICODE;
};

// ---- Modern styling ----
const colors = hasColorSupport() ? {
  primary: '\x1b[36m',      // cyan
  secondary: '\x1b[35m',    // magenta  
  success: '\x1b[32m',      // green
  warning: '\x1b[33m',      // yellow
  error: '\x1b[31m',        // red
  muted: '\x1b[90m',        // gray
  bright: '\x1b[97m',       // bright white
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  underline: '\x1b[4m'
} : {
  primary: '', secondary: '', success: '', warning: '', error: '',
  muted: '', bright: '', reset: '', bold: '', dim: '', underline: ''
};

const icons = hasUnicodeSupport() ? {
  network: '🌐', ping: '📡', dns: '🔍', http: '🌍',
  scan: '🔍', trace: '🛤️', success: '✅', error: '❌',
  loading: '⏳', arrow: '→', bullet: '•', home: '🏠',
  clear: '🧹', help: '❓', active: '▶', inactive: ' '
} : {
  network: 'N', ping: 'P', dns: 'D', http: 'H',
  scan: 'S', trace: 'T', success: 'OK', error: 'X',
  loading: '...', arrow: '->', bullet: '*', home: 'H',
  clear: 'C', help: '?', active: '>', inactive: ' '
};

const CHARS = hasUnicodeSupport() ? {
  topLeft: '╭', topRight: '╮', bottomLeft: '╰', bottomRight: '╯',
  horizontal: '─', vertical: '│', cross: '┼',
  tee: { down: '┬', up: '┴', left: '┤', right: '├' }
} : {
  topLeft: '+', topRight: '+', bottomLeft: '+', bottomRight: '+',
  horizontal: '-', vertical: '|', cross: '+',
  tee: { down: '+', up: '+', left: '+', right: '+' }
};

// Animated spinner for long operations
const spinners = hasUnicodeSupport() ? 
  ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'] :
  ['|', '/', '-', '\\'];
let spinnerIndex = 0;

function getSpinner(): string {
  return `${colors.primary}${spinners[spinnerIndex++ % spinners.length]}${colors.reset}`;
}

type Cmd =
  | { t: "help" }
  | { t: "clear" }
  | { t: "ping"; host: string }
  | { t: "dns"; host: string }
  | { t: "http"; target: string }
  | { t: "trace"; host: string }
  | { t: "scan"; host: string; range: string };

function parse(line: string): Cmd {
  const [cmd, ...rest] = line.trim().split(/\s+/);
  switch ((cmd || "").toLowerCase()) {
    case "help": return { t: "help" };
    case "clear": return { t: "clear" };
    case "debug": return { t: "help" }; // Show debug info via help
    case "ping": return { t: "ping", host: rest[0] || "" };
    case "dns": return { t: "dns", host: rest[0] || "" };
    case "http": return { t: "http", target: rest[0] || "" };
    case "trace": return { t: "trace", host: rest[0] || "" };
    case "scan": return { t: "scan", host: rest[0] || "", range: rest[1] || "" };
    default: return { t: "help" };
  }
}

function parseRange(r: string): number[] {
  const m = r.match(/^(\d+)-(\d+)$/);
  if (!m) return [];
  const [a, b] = [parseInt(m[1], 10), parseInt(m[2], 10)].sort((x, y) => x - y);
  const out: number[] = [];
  for (let p = a; p <= b && out.length < 5000; p++) out.push(p);
  return out;
}

// ---- UI state & helpers ----
type PanelState = {
  active: "home" | "ping" | "dns" | "http" | "trace" | "scan" | "clear" | "help";
  mainText: string;   // right side content
  status: string;     // footer status line
};

type InputState = {
  active: boolean;
  prompt: string;
  value: string;
  hint: string;
  submit: (val: string) => void | Promise<void>;
  cancel?: () => void;
};

const MENU: { key: PanelState["active"]; label: string; hint: string; icon: string }[] = [
  { key: "home",  label: "Home",  hint: "help", icon: icons.home },
  { key: "ping",  label: "Ping",  hint: "ping <host>", icon: icons.ping },
  { key: "dns",   label: "DNS",   hint: "dns <host>", icon: icons.dns },
  { key: "http",  label: "HTTP",  hint: "http <url|host>", icon: icons.http },
  { key: "trace", label: "Trace", hint: "trace <host>", icon: icons.trace },
  { key: "scan",  label: "Scan",  hint: "scan <host> 1-1024", icon: icons.scan },
  { key: "clear", label: "Clear", hint: "clear", icon: icons.clear },
  { key: "help",  label: "Help",  hint: "help", icon: icons.help },
];

// ---- Helper functions ----
function colorizeStatus(status: string): string {
  switch (status) {
    case 'running': return `${colors.warning}${getSpinner()} ${status}${colors.reset}`;
    case 'done': return `${colors.success}${icons.success} ${status}${colors.reset}`;
    case 'error': return `${colors.error}${icons.error} ${status}${colors.reset}`;
    case 'input': return `${colors.primary}${icons.loading} input${colors.reset}`;
    case 'nav': return `${colors.muted}${icons.arrow} navigation${colors.reset}`;
    default: return `${colors.muted}${status}${colors.reset}`;
  }
}

function getLayout(cols: number) {
  if (cols < 80) {
    return { sideW: Math.min(25, cols - 10), mainW: cols - 30, narrow: true };
  } else if (cols < 120) {
    return { sideW: SIDEBAR_WIDTH, mainW: cols - SIDEBAR_WIDTH - 5, narrow: false };
  } else {
    return { sideW: SIDEBAR_WIDTH + 5, mainW: cols - SIDEBAR_WIDTH - 10, narrow: false };
  }
}

function renderProgressBar(percent: number, width: number = 20): string {
  const filled = Math.floor(percent * width / 100);
  const bar = `${colors.success}${'█'.repeat(filled)}${colors.muted}${'░'.repeat(width - filled)}${colors.reset}`;
  return `${bar} ${colors.bold}${percent}%${colors.reset}`;
}

function padRight(s: string, w: number) {
  if (s.length >= w) return s.slice(0, w);
  return s + " ".repeat(w - s.length);
}

function wrap(text: string, width: number): string[] {
  const lines: string[] = [];
  for (const raw of text.split("\n")) {
    if (raw.length <= width) { lines.push(raw); continue; }
    let i = 0;
    while (i < raw.length) {
      lines.push(raw.slice(i, i + width));
      i += width;
      if (lines.length > MAX_CONTENT_LINES) break;
    }
  }
  return lines;
}

function buildSidebar(width: number, active: PanelState["active"]): string[] {
  const title = `${colors.bold}${colors.primary} COMMANDS ${colors.reset}`;
  const titlePlain = " COMMANDS ";
  const top = `${CHARS.topLeft}${titlePlain}${CHARS.horizontal.repeat(Math.max(0, width - titlePlain.length - 1))}${CHARS.topRight}`;
  
  const items = MENU.map((m, i) => {
    const isActive = m.key === active;
    const shortcut = `[${i + 1}]`;
    const marker = isActive ? `${colors.primary}${icons.active}${colors.reset}` : icons.inactive;
    const icon = isActive ? `${colors.primary}${m.icon}${colors.reset}` : `${colors.muted}${m.icon}${colors.reset}`;
    const label = isActive ? `${colors.bright}${colors.bold}${m.label}${colors.reset}` : `${colors.muted}${m.label}${colors.reset}`;
    const line = `${marker} ${icon} ${label} ${colors.dim}${shortcut}${colors.reset}`;
    const plainLine = `${isActive ? '▶' : ' '} ${m.icon} ${m.label} ${shortcut}`;
    const padding = width - plainLine.length - 2;
    return `${CHARS.vertical} ${line}${' '.repeat(Math.max(0, padding))} ${CHARS.vertical}`;
  });
  
  const sep = `${CHARS.tee.right}${CHARS.horizontal.repeat(width - 2)}${CHARS.tee.left}`;
  const hintsTitle = `${CHARS.vertical} ${colors.bold}${colors.secondary} HINTS ${colors.reset}${' '.repeat(width - 8)} ${CHARS.vertical}`;
  
  const hintLines = MENU.map(m => {
    const hint = `${colors.muted}${icons.bullet} ${m.hint}${colors.reset}`;
    const plainHint = `• ${m.hint}`;
    const padding = width - plainHint.length - 2;
    return `${CHARS.vertical} ${hint}${' '.repeat(Math.max(0, padding))} ${CHARS.vertical}`;
  });
  
  const bottom = `${CHARS.bottomLeft}${CHARS.horizontal.repeat(width - 2)}${CHARS.bottomRight}`;
  
  return [top, ...items, sep, hintsTitle, ...hintLines, bottom];
}

function renderInput(input: InputState, width: number): string[] {
  if (!input.active) return [];
  
  const cursor = `${colors.primary}│${colors.reset}`;
  const value = input.value + cursor;
  const border = CHARS.horizontal.repeat(Math.max(0, width - 4));
  
  return [
    `${CHARS.topLeft}${CHARS.horizontal} ${colors.bold}${colors.primary}${input.prompt}${colors.reset} ${border}${CHARS.topRight}`,
    `${CHARS.vertical} ${colors.bright}${value}${colors.reset}${' '.repeat(Math.max(0, width - value.length - 3))} ${CHARS.vertical}`,
    `${CHARS.bottomLeft}${CHARS.horizontal} ${colors.muted}${input.hint}${colors.reset} ${' '.repeat(Math.max(0, width - input.hint.length - 4))}${CHARS.bottomRight}`,
    ""
  ];
}

function renderStatusBar(state: PanelState, input: InputState, cols: number): string {
  const time = `${colors.muted}${new Date().toLocaleTimeString()}${colors.reset}`;
  const status = colorizeStatus(input.active ? "input" : state.status);
  const mode = input.active ? `${colors.primary}${colors.bold}INPUT MODE${colors.reset}` : 
               `${colors.muted}NAV MODE${colors.reset}`;
  
  const left = ` ${colors.primary}${icons.network} ${colors.bold}neoTUI${colors.reset}`;
  const center = `${mode} ${colors.muted}•${colors.reset} ${status}`;
  const right = `${time} `;
  
  // Calculate positions (accounting for ANSI codes by using plain text length)
  const leftPlain = ` 🌐 neoTUI`;
  const centerPlain = input.active ? `INPUT MODE • ${input.active ? "input" : state.status}` : 
                     `NAV MODE • ${state.status}`;
  const rightPlain = `${new Date().toLocaleTimeString()} `;
  
  const centerStart = Math.floor((cols - centerPlain.length) / 2);
  const rightStart = cols - rightPlain.length;
  
  let line = left;
  line += ' '.repeat(Math.max(0, centerStart - leftPlain.length)) + center;
  line += ' '.repeat(Math.max(0, rightStart - (leftPlain.length + centerPlain.length))) + right;
  
  return `${colors.dim}${line.slice(0, cols)}${colors.reset}`;
}

function formatNetworkOutput(data: any, type: string): string {
  switch (type) {
    case 'dns':
      return formatDnsResult(data);
    case 'http':
      return formatHttpResult(data);
    case 'scan':
      return formatScanResult(data);
    default:
      return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  }
}

function formatDnsResult(result: any): string {
  if (typeof result === 'string') return result;
  
  const sections = [];
  
  if (result.lookup && !result.lookup.error) {
    sections.push(`${colors.bold}${colors.primary}Lookup Results:${colors.reset}`);
    if (Array.isArray(result.lookup)) {
      result.lookup.forEach((entry: any) => 
        sections.push(`  ${colors.success}${icons.arrow}${colors.reset} ${entry.address} ${colors.muted}(${entry.family === 4 ? 'IPv4' : 'IPv6'})${colors.reset}`)
      );
    }
  }
  
  if (result.A?.length) {
    sections.push(`${colors.bold}${colors.secondary}A Records (IPv4):${colors.reset}`);
    result.A.forEach((ip: string) => 
      sections.push(`  ${colors.success}${icons.bullet}${colors.reset} ${ip}`)
    );
  }
  
  if (result.AAAA?.length) {
    sections.push(`${colors.bold}${colors.secondary}AAAA Records (IPv6):${colors.reset}`);
    result.AAAA.forEach((ip: string) => 
      sections.push(`  ${colors.success}${icons.bullet}${colors.reset} ${ip}`)
    );
  }
  
  if (result.MX?.length) {
    sections.push(`${colors.bold}${colors.secondary}MX Records:${colors.reset}`);
    result.MX.forEach((mx: any) => 
      sections.push(`  ${colors.success}${icons.bullet}${colors.reset} ${mx.exchange} ${colors.muted}(priority: ${mx.priority})${colors.reset}`)
    );
  }
  
  return sections.length ? sections.join('\n') : `${colors.muted}No DNS records found${colors.reset}`;
}

function formatHttpResult(result: any): string {
  if (typeof result === 'string') return result;
  
  const sections = [];
  
  sections.push(`${colors.bold}${colors.primary}HTTP Response:${colors.reset}`);
  sections.push(`${colors.success}${icons.bullet}${colors.reset} URL: ${colors.bright}${result.url}${colors.reset}`);
  
  if (result.status) {
    const statusColor = result.ok ? colors.success : colors.error;
    sections.push(`${colors.success}${icons.bullet}${colors.reset} Status: ${statusColor}${result.status}${colors.reset}`);
  }
  
  if (result.timeMs !== undefined) {
    const timeColor = result.timeMs < 200 ? colors.success : result.timeMs < 1000 ? colors.warning : colors.error;
    sections.push(`${colors.success}${icons.bullet}${colors.reset} Response Time: ${timeColor}${result.timeMs}ms${colors.reset}`);
  }
  
  if (result.headers && Object.keys(result.headers).length > 0) {
    sections.push(`${colors.bold}${colors.secondary}Headers:${colors.reset}`);
    Object.entries(result.headers).slice(0, 10).forEach(([key, value]) => 
      sections.push(`  ${colors.muted}${key}:${colors.reset} ${value}`)
    );
  }
  
  if (result.error) {
    sections.push(`${colors.error}${icons.error} Error: ${result.error}${colors.reset}`);
  }
  
  return sections.join('\n');
}

function formatScanResult(data: any, host?: string): string {
  if (typeof data === 'string') return data;
  
  if (Array.isArray(data) && host) {
    const sections = [];
    sections.push(`${colors.bold}${colors.primary}Port Scan Results for ${colors.bright}${host}${colors.reset}${colors.primary}:${colors.reset}`);
    
    if (data.length === 0) {
      sections.push(`${colors.muted}${icons.bullet} No open ports found${colors.reset}`);
    } else {
      sections.push(`${colors.success}${icons.bullet} Found ${colors.bold}${data.length}${colors.reset}${colors.success} open port(s):${colors.reset}`);
      data.forEach((result: any) => {
        sections.push(`  ${colors.success}${icons.arrow}${colors.reset} Port ${colors.bright}${result.port}${colors.reset} ${colors.success}(open)${colors.reset}`);
      });
    }
    
    return sections.join('\n');
  }
  
  return String(data);
}

function renderUI(state: PanelState, input: InputState): string {
  const cols = Math.max(60, process.stdout.columns || 80);
  const rows = Math.max(20, process.stdout.rows || 24);

  const layout = getLayout(cols);
  const contentH = rows - 3; // header/footer space

  const sidebar = buildSidebar(layout.sideW, state.active);
  const sidebarHeight = Math.min(sidebar.length, contentH);

  const header = `${CHARS.topLeft}${CHARS.horizontal.repeat(layout.sideW)}${CHARS.tee.down}${CHARS.horizontal.repeat(layout.mainW)}${CHARS.topRight}`;
  const footer = `${CHARS.bottomLeft}${CHARS.horizontal.repeat(layout.sideW)}${CHARS.tee.up}${CHARS.horizontal.repeat(layout.mainW)}${CHARS.bottomRight}`;

  const mainTitle = `${colors.bold}${colors.primary} OUTPUT ${colors.reset}`;
  const mainTitlePlain = " OUTPUT ";
  
  let right: string[] = [];
  
  // Add input overlay if active
  if (input.active) {
    right = renderInput(input, layout.mainW);
  }
  
  // Add main content
  const formattedContent = input.active ? state.mainText : 
    (state.active === 'dns' || state.active === 'http') ? 
    state.mainText : state.mainText;
  
  right = right.concat([mainTitle, ""].concat(wrap(formattedContent, layout.mainW - 4)));

  const mainBody = right.slice(0, contentH);

  const body: string[] = [];
  for (let i = 0; i < contentH; i++) {
    const l = sidebar[i] || `${CHARS.vertical}${' '.repeat(layout.sideW - 2)}${CHARS.vertical}`;
    const rContent = mainBody[i] || "";
    const rPlain = mainBody[i]?.replace(/\x1b\[[0-9;]*m/g, '') || ""; // strip ANSI for length calc
    const rPadding = ' '.repeat(Math.max(0, layout.mainW - rPlain.length - 2));
    const r = `${CHARS.vertical} ${rContent}${rPadding} ${CHARS.vertical}`;
    body.push(`${l}${r}`);
  }

  const statusBar = renderStatusBar(state, input, cols);

  return [header, ...body, footer, statusBar].join("\n");
}

// ---- app ----
async function main() {
  const renderer = await createCliRenderer();

  // Terminal capability info for debugging
  const debugInfo = `
Terminal Environment:
- TERM: ${process.env.TERM || 'undefined'}
- COLORTERM: ${process.env.COLORTERM || 'undefined'}  
- LANG: ${process.env.LANG || 'undefined'}
- TTY: ${process.stdout.isTTY}
- Color Support: ${hasColorSupport()}
- Unicode Support: ${hasUnicodeSupport()}

Test Characters:
- Box: ${CHARS.topLeft}${CHARS.horizontal}${CHARS.topRight}
- Icons: ${icons.network} ${icons.ping} ${icons.success}
- Spinner: ${getSpinner()}
`;

  const asciiLogo = `${colors.primary}${colors.bold}` + String.raw`
 _   _                  _______ _   _ 
| \ | | ___  ___  ___ |__   __| | | |
|  \| |/ _ \/ _ \/ _ \   | |  | |_| |
| |\  |  __/  __/  __/   | |  |  _  |
|_| \_|\___|\___|\___|   |_|  |_| |_|
` + `${colors.reset}${colors.secondary}${colors.bold}\n                     neoTUI${colors.reset}`;

  const banner =
`${asciiLogo}
${colors.bright}Navigation:${colors.reset}
${colors.muted}${icons.bullet}${colors.reset} Use ${colors.primary}↑/↓${colors.reset} to choose a command
${colors.muted}${icons.bullet}${colors.reset} Press ${colors.primary}Enter${colors.reset} to run, or ${colors.primary}1-8${colors.reset} to jump
${colors.muted}${icons.bullet}${colors.reset} Type commands at ${colors.secondary}neoTUI>${colors.reset} prompt, ${colors.secondary}?${colors.reset} for help

${colors.bright}Features:${colors.reset}
${colors.muted}${icons.bullet}${colors.reset} Interactive input for missing parameters
${colors.muted}${icons.bullet}${colors.reset} Colorized network output with icons
${colors.muted}${icons.bullet}${colors.reset} Real-time status and spinners

${colors.dim}Select a command from the sidebar to get started...${colors.reset}
${colors.dim}Type 'debug' to see terminal compatibility info.${colors.reset}
`;

  let appState: PanelState = {
    active: "home",
    mainText: banner,
    status: "ready",
  };

  const inputState: InputState = {
    active: false,
    prompt: "",
    value: "",
    hint: "Enter = submit • Esc = cancel • Backspace = delete",
    submit: () => {},
    cancel: () => {}
  };

  // Remember last-used args so Enter can run from the sidebar
  const lastArgs = {
    ping: "",
    dns: "",
    http: "",
    trace: "",
    scan: { host: "", range: "1-1024" }
  };

  let output = new TextRenderable("output", { content: renderUI(appState, inputState) });
  renderer.root.add(output);

  // Smooth rendering with transition effects
  let lastRender = '';
  const redraw = () => {
    const newContent = renderUI(appState, inputState);
    if (newContent !== lastRender) {
      // Clear screen with fade effect for smooth transitions
      const next = new TextRenderable("output", { content: newContent });
      renderer.root.add(next);
      output = next;
      lastRender = newContent;
    }
  };

  // Auto-refresh for animated spinners
  const refreshInterval = setInterval(() => {
    if (appState.status === 'running') {
      redraw();
    }
  }, 100);

  const setMain = (text: string, active?: PanelState["active"], status?: string) => {
    if (active) appState.active = active;
    if (status) appState.status = status;
    appState.mainText = text;
    selectedIndex = MENU.findIndex(m => m.key === appState.active);
    redraw();
  };

  // ---- input modal helpers ----
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout, prompt: "neoTUI> " });

  function startInput(prompt: string, initial: string, onSubmit: (val: string) => Promise<void> | void, onCancel?: () => void) {
    inputState.active = true;
    inputState.prompt = prompt;
    inputState.value = initial;
    inputState.submit = onSubmit;
    inputState.cancel = onCancel || (() => {});
    appState.status = "input";

    // Don't let the REPL eat Enter, but keep the underlying stream flowing for keypress()
    rl.pause();                       // stop REPL 'line' events
    if (process.stdin.isTTY) {
      process.stdin.setRawMode(true); // required for printable keypresses
      process.stdin.resume();         // VERY IMPORTANT: keep 'data' flowing for keypress events
    }

    redraw();
  }

  async function endInput(submitted: boolean) {
    if (submitted) {
      // submit already handled by caller
    } else {
      inputState.cancel && inputState.cancel();
    }
    inputState.active = false;
    inputState.prompt = "";
    inputState.value = "";
    appState.status = "ready";
    redraw();

    rl.resume();
    if (process.stdin.isTTY) process.stdin.resume(); // keep keypress working after modal
    rl.prompt();
  }

  // Convenience: prompt sequences (e.g., Scan host then range)
  function promptSequence(steps: { prompt: string; initial?: string; validate?: (v: string) => string | null }[],
                          done: (answers: string[]) => Promise<void> | void) {
    const answers: string[] = [];
    const runStep = (idx: number) => {
      const step = steps[idx];
      startInput(step.prompt, step.initial ?? "", async (val) => {
        const err = step.validate ? step.validate(val) : null;
        if (err) {
          setMain(`⛔ ${err}`, appState.active, "input-error");
          // re-open same step
          runStep(idx);
          return;
        }
        answers[idx] = val;
        if (idx + 1 < steps.length) {
          runStep(idx + 1);
          return;
        }
        await done(answers);
        await endInput(true);
      }, async () => {
        await endInput(false);
      });
    };
    runStep(0);
  }

  // ---- REPL ----
  rl.prompt();
  rl.on("line", async (line) => {
    if (inputState.active) {          // modal is open → ignore REPL input
      rl.prompt();
      return;
    }
    const cmd = parse(line);
    try {
      if (cmd.t === "help") {
        const isDebug = line.trim().toLowerCase() === "debug";
        setMain(isDebug ? debugInfo : banner, "help", isDebug ? "debug" : "help");
      } else if (cmd.t === "clear") {
        setMain("", "clear", "cleared");
      } else if (cmd.t === "ping") {
        if (!cmd.host) {
          promptSequence(
            [{ prompt: "Host/IP to ping:" }],
            async ([host]) => {
              lastArgs.ping = host;
              setMain(`Pinging ${host} ...`, "ping", "running");
              const res = await ping(host);
              setMain(String(res), "ping", "done");
            }
          );
          return;
        }
        lastArgs.ping = cmd.host;
        setMain(`Pinging ${cmd.host} ...`, "ping", "running");
        const res = await ping(cmd.host);
        setMain(String(res), "ping", "done");
      } else if (cmd.t === "dns") {
        if (!cmd.host) {
          promptSequence(
            [{ prompt: "Hostname for DNS lookup:" }],
            async ([host]) => {
              lastArgs.dns = host;
              setMain(`Resolving ${host} ...`, "dns", "running");
              const res = await dnsLookup(host);
              setMain(formatDnsResult(res), "dns", "done");
            }
          );
          return;
        }
        lastArgs.dns = cmd.host;
        setMain(`Resolving ${cmd.host} ...`, "dns", "running");
        const res = await dnsLookup(cmd.host);
        setMain(formatDnsResult(res), "dns", "done");
      } else if (cmd.t === "http") {
        if (!cmd.target) {
          promptSequence(
            [{ prompt: "URL or host for HTTP check (e.g., https://example.com):" }],
            async ([target]) => {
              lastArgs.http = target;
              setMain(`Fetching ${target} ...`, "http", "running");
              const res = await httpCheck(target);
              setMain(formatHttpResult(res), "http", "done");
            }
          );
          return;
        }
        lastArgs.http = cmd.target;
        setMain(`Fetching ${cmd.target} ...`, "http", "running");
        const res = await httpCheck(cmd.target);
        setMain(formatHttpResult(res), "http", "done");
      } else if (cmd.t === "trace") {
        if (!cmd.host) {
          promptSequence(
            [{ prompt: "Host/IP to traceroute:" }],
            async ([host]) => {
              lastArgs.trace = host;
              setMain(`Tracing route to ${host} ...`, "trace", "running");
              const res = await traceroute(host);
              setMain(String(res), "trace", "done");
            }
          );
          return;
        }
        lastArgs.trace = cmd.host;
        setMain(`Tracing route to ${cmd.host} ...`, "trace", "running");
        const res = await traceroute(cmd.host);
        setMain(String(res), "trace", "done");
      } else if (cmd.t === "scan") {
        const haveArgs = !!(cmd.host && cmd.range);
        if (!haveArgs) {
          promptSequence(
            [
              { prompt: "Host/IP to scan:" },
              { prompt: "Port range (start-end), e.g., 1-1024:", validate: (v) => parseRange(v).length ? null : "Invalid range. Example: 1-1024" }
            ],
            async ([host, range]) => {
              const ports = parseRange(range);
              lastArgs.scan = { host, range };
              setMain(`Scanning ${host} ports ${range} ...`, "scan", "running");
              const res = await portScan(host, ports);
              setMain(formatScanResult(res, host), "scan", "done");
            }
          );
          return;
        }
        const ports = parseRange(cmd.range);
        if (!ports.length) return setMain("Bad range. Example: 1-1024", "scan", "bad-range");
        lastArgs.scan = { host: cmd.host, range: cmd.range };
        setMain(`Scanning ${cmd.host} ports ${cmd.range} ...`, "scan", "running");
        const res = await portScan(cmd.host, ports);
        setMain(formatScanResult(res, cmd.host), "scan", "done");
      }
    } catch (e: any) {
      setMain(`Error: ${e?.message || e}`, appState.active, "error");
    }
    rl.prompt();
  });

  rl.on("SIGINT", () => {
    clearInterval(refreshInterval);
    cleanupRawMode();
    rl.close();
    process.exit(0);
  });

  // ---- Arrow keys + input capture ----
  readline.emitKeypressEvents(process.stdin, rl); // pass rl for maximum compatibility (Warp, Bun)
  if (process.stdin.isTTY) {
    process.stdin.setRawMode(true);
    process.stdin.resume();
  }
  
  let rawEnabled = true; // already enabled above
  const cleanupRawMode = () => {
    if (process.stdin.isTTY && rawEnabled) {
      try { process.stdin.setRawMode(false); } catch {}
      rawEnabled = false;
    }
  };

  let selectedIndex = MENU.findIndex(m => m.key === appState.active);

  const moveSelection = (delta: number) => {
    if (inputState.active) return; // ignore nav while typing
    selectedIndex = (selectedIndex + delta + MENU.length) % MENU.length;
    appState.active = MENU[selectedIndex].key;
    appState.status = "nav";
    redraw();
  };

  const runSelected = async () => {
    const sel = MENU[selectedIndex].key;
    try {
      if (sel === "home" || sel === "help") {
        setMain(banner, "help", "help");
      } else if (sel === "clear") {
        setMain("", "clear", "cleared");
      } else if (sel === "ping") {
        promptSequence(
          [{ prompt: "Host/IP to ping:", initial: lastArgs.ping }],
          async ([host]) => {
            lastArgs.ping = host;
            setMain(`Pinging ${host} ...`, "ping", "running");
            const res = await ping(host);
            setMain(String(res), "ping", "done");
          }
        );
        return;
      } else if (sel === "dns") {
        promptSequence(
          [{ prompt: "Hostname for DNS lookup:", initial: lastArgs.dns }],
          async ([host]) => {
            lastArgs.dns = host;
            setMain(`Resolving ${host} ...`, "dns", "running");
            const res = await dnsLookup(host);
            setMain(formatDnsResult(res), "dns", "done");
          }
        );
        return;
      } else if (sel === "http") {
        promptSequence(
          [{ prompt: "URL or host for HTTP check (e.g., https://example.com):", initial: lastArgs.http }],
          async ([target]) => {
            lastArgs.http = target;
            setMain(`Fetching ${target} ...`, "http", "running");
            const res = await httpCheck(target);
            setMain(formatHttpResult(res), "http", "done");
          }
        );
        return;
      } else if (sel === "trace") {
        promptSequence(
          [{ prompt: "Host/IP to traceroute:", initial: lastArgs.trace }],
          async ([host]) => {
            lastArgs.trace = host;
            setMain(`Tracing route to ${host} ...`, "trace", "running");
            const res = await traceroute(host);
            setMain(String(res), "trace", "done");
          }
        );
        return;
      } else if (sel === "scan") {
        const { host, range } = lastArgs.scan;
        promptSequence(
          [
            { prompt: "Host/IP to scan:", initial: host },
            { prompt: "Port range (start-end), e.g., 1-1024:", initial: range, validate: (v) => parseRange(v).length ? null : "Invalid range. Example: 1-1024" }
          ],
          async ([h, r]) => {
            const ports = parseRange(r);
            if (!ports.length) return setMain("Bad range. Example: 1-1024", "scan", "bad-range");
            lastArgs.scan = { host: h, range: r };
            setMain(`Scanning ${h} ports ${r} ...`, "scan", "running");
            const res = await portScan(h, ports);
            setMain(formatScanResult(res, h), "scan", "done");
          }
        );
        return;
      }
    } catch (e: any) {
      setMain(`Error: ${e?.message || e}`, appState.active, "error");
    }
  };

  process.stdin.on("keypress", async (str, key: any) => {
    if (!key) return;

    // Input mode: capture printable chars, backspace, enter, esc
    if (inputState.active) {
      if (key.ctrl && key.name === "c") {
        await endInput(false);
        clearInterval(refreshInterval);
        cleanupRawMode();
        rl.close();
        process.exit(0);
      }
      if (key.name === "return" || key.name === "enter") {
        const val = inputState.value.trim();
        await inputState.submit(val);
        return; // submit handler calls endInput()
      }
      if (key.name === "escape") {
        await endInput(false);
        return;
      }
      if (key.name === "backspace") {
        inputState.value = inputState.value.slice(0, -1);
        redraw();
        return;
      }
      // Append printable input (including paste)
      if (str && !key.ctrl && !key.meta) {
        inputState.value += str;
        redraw();
      }
      return;
    }

    // Normal nav mode
    if (key.ctrl && key.name === "c") {
      clearInterval(refreshInterval);
      cleanupRawMode();
      rl.close();
      process.exit(0);
    }
    // Quick help
    if (str === "?") {
      setMain(banner, "help", "help");
      rl.prompt();
      return;
    }
    // Numeric shortcuts 1-8
    if (str && /^[1-8]$/.test(str)) {
      const idx = parseInt(str, 10) - 1;
      if (idx >= 0 && idx < MENU.length) {
        selectedIndex = idx;
        appState.active = MENU[selectedIndex].key;
        appState.status = "nav";
        redraw();
      }
      return;
    }
    if (key.name === "up") {
      moveSelection(-1);
      return;
    }
    if (key.name === "down") {
      moveSelection(1);
      return;
    }
    if (key.name === "return" || key.name === "enter") {
      await runSelected();
      rl.prompt();
      return;
    }
  });

  // safety: turn off raw mode on exit
  process.on("exit", () => { clearInterval(refreshInterval); cleanupRawMode(); });
  process.on("SIGTERM", () => { clearInterval(refreshInterval); cleanupRawMode(); process.exit(0); });
}

main();