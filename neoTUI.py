import re
import socket
import subprocess
import sys
from typing import List

import requests
import typer
from ping3 import ping
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Modern network toolkit", add_completion=False)
console = Console()

# ----- helpers -----

def panel(title: str) -> Panel:
    return Panel.fit(title, style="bright_cyan", border_style="cyan")

# ----- commands -----

@app.command()
def ping_host(host: str):
    """Ping a host and show latency."""
    console.print(panel(f"Pinging [bold magenta]{host}[/]"))
    try:
        delay = ping(host, unit='ms')
        if delay is None:
            console.print(f"[red]No response from {host}[/]")
        else:
            console.print(f"[green]Reply in {delay:.1f} ms[/]")
    except Exception as e:
        console.print(f"[red]{e}[/]")

@app.command()
def dns(host: str):
    """Resolve DNS for a host."""
    console.print(panel(f"Resolving [bold magenta]{host}[/]"))
    try:
        infos = socket.getaddrinfo(host, None)
        ips = sorted({info[4][0] for info in infos})
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("IP Address")
        for ip in ips:
            table.add_row(f"[bright_magenta]{ip}[/]")
        console.print(table)
    except Exception as e:
        console.print(f"[red]{e}[/]")

@app.command()
def http(url: str):
    """Perform a simple HTTP GET request."""
    console.print(panel(f"Fetching [bold magenta]{url}[/]"))
    try:
        r = requests.get(url, timeout=5)
        console.print(f"[green]Status {r.status_code}[/]")
    except Exception as e:
        console.print(f"[red]{e}[/]")

@app.command()
def trace(host: str):
    """Run traceroute to a host."""
    console.print(panel(f"Tracing [bold magenta]{host}[/]"))
    cmd = ["traceroute", host] if sys.platform != "win32" else ["tracert", host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        console.print(result.stdout or result.stderr)
    except Exception as e:
        console.print(f"[red]{e}[/]")

@app.command()
def scan(host: str, port_range: str = typer.Argument("1-1024", help="start-end")):
    """Scan a host for open TCP ports."""
    console.print(panel(f"Scanning [bold magenta]{host}[/] ports [bold]{port_range}[/]"))
    m = re.fullmatch(r"(\d+)-(\d+)", port_range)
    if not m:
        console.print("[red]Invalid range. Use start-end[/]")
        raise typer.Exit(code=1)
    a, b = sorted((int(m.group(1)), int(m.group(2))))
    open_ports: List[int] = []
    for port in range(a, b + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            try:
                s.connect((host, port))
                open_ports.append(port)
            except Exception:
                pass
    if open_ports:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Open Ports")
        for p in open_ports:
            table.add_row(f"[bright_magenta]{p}[/]")
        console.print(table)
    else:
        console.print("[yellow]No open ports found in range[/]")


if __name__ == "__main__":
    app()
