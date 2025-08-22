import re
import socket
import subprocess
import sys
import json
import csv
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import typer
from ping3 import ping
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint
from rich.text import Text

app = typer.Typer(
    help="🚀 Modern network toolkit - Fast, colorful, and user-friendly",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

# Configuration support
CONFIG_FILE = Path.home() / ".neotui_config.json"

class Config:
    """Configuration manager for neoTUI"""
    def __init__(self):
        self.settings = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return json.load(f)
            except Exception:
                return self.default_config()
        return self.default_config()
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save config: {e}[/]")
    
    def default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "default_timeout": 5,
            "ping_count": 4,
            "scan_timeout": 0.3,
            "http_timeout": 10,
            "export_format": "json",
            "color_scheme": "bright"
        }
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.settings[key] = value
        self.save()

config = Config()

# ----- helpers -----

def panel(title: str, subtitle: str = "") -> Panel:
    """Create a styled panel with optional subtitle"""
    if subtitle:
        title = f"{title}\n[dim]{subtitle}[/dim]"
    return Panel.fit(title, style="bright_cyan", border_style="cyan")

def error_panel(message: str, suggestion: str = "") -> Panel:
    """Create an error panel with optional suggestion"""
    content = f"[red]❌ {message}[/red]"
    if suggestion:
        content += f"\n\n[yellow]💡 Suggestion: {suggestion}[/yellow]"
    return Panel(content, style="red", border_style="red", title="Error")

def success_panel(message: str) -> Panel:
    """Create a success panel"""
    return Panel(f"[green]✅ {message}[/green]", style="green", border_style="green", title="Success")

def validate_host(host: str) -> bool:
    """Validate hostname or IP address"""
    # Check if it's a valid IP
    try:
        socket.inet_aton(host)
        return True
    except socket.error:
        pass
    
    # Check if it's a valid hostname
    hostname_regex = re.compile(
        r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*'
        r'([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
    )
    return bool(hostname_regex.match(host))

def validate_url(url: str) -> bool:
    """Validate URL format"""
    url_regex = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(url_regex.match(url))

def export_results(data: Dict[str, Any], filename: str, format: str = "json"):
    """Export results to file"""
    try:
        if format == "json":
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif format == "csv":
            # Flatten the data for CSV export
            if isinstance(data, dict) and 'results' in data:
                results = data['results']
                if results and isinstance(results, list):
                    with open(filename, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=results[0].keys())
                        writer.writeheader()
                        writer.writerows(results)
            else:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    for key, value in data.items():
                        writer.writerow([key, value])
        
        console.print(success_panel(f"Results exported to {filename}"))
        return True
    except Exception as e:
        console.print(error_panel(f"Failed to export: {e}"))
        return False

# ----- commands -----

@app.command(name="ping")
def ping_host(
    host: str = typer.Argument(..., help="Hostname or IP address to ping"),
    count: int = typer.Option(4, "--count", "-c", help="Number of pings to send"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Timeout in seconds"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export results to file")
):
    """🏓 Ping a host and show detailed latency statistics."""
    # Input validation
    if not validate_host(host):
        console.print(error_panel(
            f"Invalid hostname or IP address: {host}",
            "Please provide a valid hostname (e.g., google.com) or IP address (e.g., 8.8.8.8)"
        ))
        raise typer.Exit(code=1)
    
    console.print(panel(f"Pinging [bold magenta]{host}[/]", f"Sending {count} packets"))
    
    results = []
    successful = 0
    min_delay = float('inf')
    max_delay = 0
    total_delay = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Pinging {host}...", total=count)
        
        for i in range(count):
            try:
                start_time = time.time()
                delay = ping(host, timeout=timeout, unit='ms')
                
                if delay is not None:
                    successful += 1
                    min_delay = min(min_delay, delay)
                    max_delay = max(max_delay, delay)
                    total_delay += delay
                    
                    results.append({
                        "sequence": i + 1,
                        "status": "success",
                        "latency_ms": round(delay, 2),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    console.print(f"  [green]Reply from {host}: time={delay:.1f}ms[/]")
                else:
                    results.append({
                        "sequence": i + 1,
                        "status": "timeout",
                        "latency_ms": None,
                        "timestamp": datetime.now().isoformat()
                    })
                    console.print(f"  [red]Request timeout[/]")
                
            except Exception as e:
                results.append({
                    "sequence": i + 1,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                console.print(f"  [red]Error: {e}[/]")
            
            progress.update(task, advance=1)
    
    # Display statistics
    if successful > 0:
        avg_delay = total_delay / successful
        packet_loss = ((count - successful) / count) * 100
        
        stats_table = Table(title="Ping Statistics", show_header=True, header_style="bold cyan")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="bright_magenta")
        
        stats_table.add_row("Host", host)
        stats_table.add_row("Packets Sent", str(count))
        stats_table.add_row("Packets Received", str(successful))
        stats_table.add_row("Packet Loss", f"{packet_loss:.1f}%")
        stats_table.add_row("Min Latency", f"{min_delay:.2f} ms")
        stats_table.add_row("Max Latency", f"{max_delay:.2f} ms")
        stats_table.add_row("Avg Latency", f"{avg_delay:.2f} ms")
        
        console.print("\n")
        console.print(stats_table)
    else:
        console.print(error_panel(
            f"No response from {host} after {count} attempts",
            "Check if the host is online and not blocking ICMP packets"
        ))
    
    # Export results if requested
    if export:
        export_data = {
            "command": "ping",
            "host": host,
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "packets_sent": count,
                "packets_received": successful,
                "packet_loss_percent": ((count - successful) / count) * 100 if count > 0 else 100,
                "min_latency_ms": round(min_delay, 2) if successful > 0 else None,
                "max_latency_ms": round(max_delay, 2) if successful > 0 else None,
                "avg_latency_ms": round(avg_delay, 2) if successful > 0 else None
            },
            "results": results
        }
        export_results(export_data, export, config.get("export_format", "json"))

@app.command()
def dns(
    host: str = typer.Argument(..., help="Hostname to resolve"),
    record_type: str = typer.Option("A", "--type", "-t", help="DNS record type (A, AAAA, MX, TXT, etc.)"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export results to file")
):
    """🔍 Resolve DNS records for a host with detailed information."""
    if not validate_host(host):
        console.print(error_panel(
            f"Invalid hostname: {host}",
            "Please provide a valid hostname (e.g., example.com)"
        ))
        raise typer.Exit(code=1)
    
    console.print(panel(f"Resolving DNS for [bold magenta]{host}[/]", f"Record type: {record_type}"))
    
    results = {"host": host, "record_type": record_type, "timestamp": datetime.now().isoformat()}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Querying DNS servers...", total=None)
        
        try:
            # Get IP addresses
            if record_type.upper() in ["A", "AAAA"]:
                infos = socket.getaddrinfo(host, None)
                ips = sorted({info[4][0] for info in infos})
                
                # Separate IPv4 and IPv6
                ipv4_addrs = [ip for ip in ips if ':' not in ip]
                ipv6_addrs = [ip for ip in ips if ':' in ip]
                
                table = Table(title=f"DNS Resolution Results for {host}", show_header=True, header_style="bold cyan")
                table.add_column("Type", style="cyan")
                table.add_column("IP Address", style="bright_magenta")
                table.add_column("Reverse DNS", style="yellow")
                
                all_records = []
                
                for ip in ipv4_addrs:
                    try:
                        reverse = socket.gethostbyaddr(ip)[0]
                    except:
                        reverse = "N/A"
                    table.add_row("IPv4", ip, reverse)
                    all_records.append({"type": "IPv4", "address": ip, "reverse_dns": reverse})
                
                for ip in ipv6_addrs:
                    try:
                        reverse = socket.gethostbyaddr(ip)[0]
                    except:
                        reverse = "N/A"
                    table.add_row("IPv6", ip, reverse)
                    all_records.append({"type": "IPv6", "address": ip, "reverse_dns": reverse})
                
                results["records"] = all_records
                progress.update(task, completed=100)
                console.print("\n")
                console.print(table)
                
                # Additional information
                try:
                    canonical_name = socket.getfqdn(host)
                    if canonical_name != host:
                        console.print(f"\n[cyan]Canonical name:[/] [bright_magenta]{canonical_name}[/]")
                        results["canonical_name"] = canonical_name
                except:
                    pass
                    
            else:
                # For other record types, we'd need dnspython library
                console.print(f"[yellow]Note: Advanced record types require additional libraries. Showing basic resolution only.[/]")
                ip = socket.gethostbyname(host)
                console.print(f"[green]Resolved to: {ip}[/]")
                results["ip_address"] = ip
                
        except socket.gaierror as e:
            progress.update(task, completed=100)
            console.print(error_panel(
                f"DNS resolution failed: {e}",
                "Check if the hostname is correct and your DNS server is accessible"
            ))
            results["error"] = str(e)
        except Exception as e:
            progress.update(task, completed=100)
            console.print(error_panel(f"Unexpected error: {e}"))
            results["error"] = str(e)
    
    # Export results if requested
    if export:
        export_results(results, export, config.get("export_format", "json"))

@app.command()
def http(
    url: str = typer.Argument(..., help="URL to fetch"),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method"),
    headers: bool = typer.Option(False, "--headers", "-H", help="Show response headers"),
    follow: bool = typer.Option(True, "--follow", "-f", help="Follow redirects"),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Request timeout in seconds"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export results to file")
):
    """🌐 Perform HTTP requests with detailed response information."""
    if not validate_url(url):
        console.print(error_panel(
            f"Invalid URL format: {url}",
            "Please provide a valid URL starting with http:// or https://"
        ))
        raise typer.Exit(code=1)
    
    console.print(panel(f"Fetching [bold magenta]{url}[/]", f"Method: {method}"))
    
    results = {
        "url": url,
        "method": method,
        "timestamp": datetime.now().isoformat()
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Sending request...", total=None)
        
        try:
            start_time = time.time()
            response = requests.request(
                method=method,
                url=url,
                timeout=timeout,
                allow_redirects=follow,
                headers={"User-Agent": "neoTUI/1.0"}
            )
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
            
            progress.update(task, completed=100)
            
            # Create response table
            table = Table(title="HTTP Response", show_header=True, header_style="bold cyan")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="bright_magenta")
            
            # Determine status color
            if 200 <= response.status_code < 300:
                status_color = "green"
            elif 300 <= response.status_code < 400:
                status_color = "yellow"
            else:
                status_color = "red"
            
            table.add_row("Status Code", f"[{status_color}]{response.status_code}[/]")
            table.add_row("Status Text", response.reason)
            table.add_row("Response Time", f"{elapsed_time:.2f} ms")
            table.add_row("Content Length", f"{len(response.content)} bytes")
            table.add_row("Content Type", response.headers.get("Content-Type", "N/A"))
            table.add_row("Server", response.headers.get("Server", "N/A"))
            
            if response.history:
                redirects = " → ".join([str(r.status_code) for r in response.history])
                table.add_row("Redirects", redirects)
            
            console.print("\n")
            console.print(table)
            
            # Show headers if requested
            if headers:
                headers_table = Table(title="Response Headers", show_header=True, header_style="bold cyan")
                headers_table.add_column("Header", style="cyan")
                headers_table.add_column("Value", style="bright_magenta")
                
                for header, value in response.headers.items():
                    headers_table.add_row(header, value[:100] + "..." if len(value) > 100 else value)
                
                console.print("\n")
                console.print(headers_table)
            
            # Store results
            results.update({
                "status_code": response.status_code,
                "status_text": response.reason,
                "response_time_ms": round(elapsed_time, 2),
                "content_length": len(response.content),
                "headers": dict(response.headers),
                "redirects": [{"url": r.url, "status": r.status_code} for r in response.history]
            })
            
            # Show a preview of the content if it's text
            if "text" in response.headers.get("Content-Type", ""):
                preview = response.text[:500]
                if len(response.text) > 500:
                    preview += "\n[dim]... (truncated)[/dim]"
                console.print("\n[cyan]Content Preview:[/]")
                console.print(Panel(preview, style="dim"))
                
        except requests.exceptions.Timeout:
            progress.update(task, completed=100)
            console.print(error_panel(
                f"Request timed out after {timeout} seconds",
                "Try increasing the timeout with --timeout option"
            ))
            results["error"] = "Timeout"
        except requests.exceptions.ConnectionError as e:
            progress.update(task, completed=100)
            console.print(error_panel(
                f"Connection failed: {e}",
                "Check if the URL is correct and the server is accessible"
            ))
            results["error"] = str(e)
        except Exception as e:
            progress.update(task, completed=100)
            console.print(error_panel(f"Unexpected error: {e}"))
            results["error"] = str(e)
    
    # Export results if requested
    if export:
        export_results(results, export, config.get("export_format", "json"))

@app.command()
def trace(
    host: str = typer.Argument(..., help="Hostname or IP to trace"),
    max_hops: int = typer.Option(30, "--max-hops", "-m", help="Maximum number of hops"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export results to file")
):
    """🛤️ Trace the network path to a host with hop details."""
    if not validate_host(host):
        console.print(error_panel(
            f"Invalid hostname or IP address: {host}",
            "Please provide a valid hostname or IP address"
        ))
        raise typer.Exit(code=1)
    
    console.print(panel(f"Tracing route to [bold magenta]{host}[/]", f"Max hops: {max_hops}"))
    
    cmd = ["traceroute", "-m", str(max_hops), host] if sys.platform != "win32" else ["tracert", "-h", str(max_hops), host]
    
    results = {
        "host": host,
        "max_hops": max_hops,
        "timestamp": datetime.now().isoformat(),
        "hops": []
    }
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Tracing route...", total=None)
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            table = Table(title=f"Route to {host}", show_header=True, header_style="bold cyan")
            table.add_column("Hop", style="cyan", width=5)
            table.add_column("Host", style="bright_magenta")
            table.add_column("IP Address", style="yellow")
            table.add_column("Response Times", style="green")
            
            hop_pattern = re.compile(r'^\s*(\d+)')
            
            for line in process.stdout:
                line = line.strip()
                if line and hop_pattern.match(line):
                    console.print(f"  [dim]{line}[/dim]")
                    
                    # Parse the line (basic parsing, format varies by OS)
                    parts = line.split()
                    if parts:
                        hop_num = parts[0]
                        # Extract IPs and hostnames from the line
                        ip_pattern = re.compile(r'\d+\.\d+\.\d+\.\d+')
                        ips = ip_pattern.findall(line)
                        
                        if ips:
                            results["hops"].append({
                                "hop": hop_num,
                                "ip": ips[0] if ips else "N/A",
                                "raw": line
                            })
            
            process.wait()
            progress.update(task, completed=100)
            
            if process.returncode != 0:
                stderr = process.stderr.read()
                if stderr:
                    console.print(f"[yellow]Warning: {stderr}[/]")
                    
    except FileNotFoundError:
        console.print(error_panel(
            f"traceroute/tracert command not found",
            "Please install traceroute (Linux/Mac) or ensure tracert is available (Windows)"
        ))
        results["error"] = "Command not found"
    except Exception as e:
        console.print(error_panel(f"Failed to trace route: {e}"))
        results["error"] = str(e)
    
    # Export results if requested
    if export:
        export_results(results, export, config.get("export_format", "json"))

@app.command()
def scan(
    host: str = typer.Argument(..., help="Hostname or IP to scan"),
    port_range: str = typer.Argument("1-1024", help="Port range (e.g., 80, 1-1024, 80,443,8080)"),
    timeout: float = typer.Option(0.3, "--timeout", "-t", help="Connection timeout in seconds"),
    threads: int = typer.Option(50, "--threads", "-T", help="Number of threads for parallel scanning"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export results to file")
):
    """🔓 Scan TCP ports with service detection and parallel scanning."""
    if not validate_host(host):
        console.print(error_panel(
            f"Invalid hostname or IP address: {host}",
            "Please provide a valid hostname or IP address"
        ))
        raise typer.Exit(code=1)
    
    # Parse port range
    ports_to_scan = []
    
    # Check if it's a comma-separated list
    if ',' in port_range:
        for port_str in port_range.split(','):
            try:
                ports_to_scan.append(int(port_str.strip()))
            except ValueError:
                console.print(error_panel(
                    f"Invalid port number: {port_str}",
                    "Ports must be numbers between 1 and 65535"
                ))
                raise typer.Exit(code=1)
    # Check if it's a range
    elif '-' in port_range:
        match = re.fullmatch(r"(\d+)-(\d+)", port_range)
        if not match:
            console.print(error_panel(
                "Invalid port range format",
                "Use format: start-end (e.g., 1-1024) or comma-separated (e.g., 80,443,8080)"
            ))
            raise typer.Exit(code=1)
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        if start < 1 or end > 65535:
            console.print(error_panel(
                "Port numbers must be between 1 and 65535",
                "Valid range example: 1-1024"
            ))
            raise typer.Exit(code=1)
        ports_to_scan = list(range(start, end + 1))
    # Single port
    else:
        try:
            ports_to_scan = [int(port_range)]
        except ValueError:
            console.print(error_panel(
                f"Invalid port: {port_range}",
                "Provide a valid port number, range (1-1024), or list (80,443,8080)"
            ))
            raise typer.Exit(code=1)
    
    console.print(panel(
        f"Scanning [bold magenta]{host}[/]",
        f"Ports: {len(ports_to_scan)} | Timeout: {timeout}s | Threads: {threads}"
    ))
    
    # Common service ports mapping
    common_services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
        8443: "HTTPS-Alt", 27017: "MongoDB", 3389: "RDP", 5900: "VNC"
    }
    
    open_ports = []
    closed_count = 0
    
    def scan_port(port):
        """Scan a single port"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                if result == 0:
                    service = common_services.get(port, "Unknown")
                    return {"port": port, "status": "open", "service": service}
                else:
                    return {"port": port, "status": "closed"}
        except socket.gaierror:
            return {"port": port, "status": "error", "error": "Host resolution failed"}
        except Exception as e:
            return {"port": port, "status": "error", "error": str(e)}
    
    results = {
        "host": host,
        "port_range": port_range,
        "total_ports_scanned": len(ports_to_scan),
        "timestamp": datetime.now().isoformat(),
        "scan_results": []
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task(f"[cyan]Scanning {len(ports_to_scan)} ports...", total=len(ports_to_scan))
        
        with ThreadPoolExecutor(max_workers=min(threads, len(ports_to_scan))) as executor:
            futures = {executor.submit(scan_port, port): port for port in ports_to_scan}
            
            for future in as_completed(futures):
                result = future.result()
                results["scan_results"].append(result)
                
                if result["status"] == "open":
                    open_ports.append(result)
                    console.print(f"  [green]✓ Port {result['port']} ({result['service']}) is open[/]")
                elif result["status"] == "closed":
                    closed_count += 1
                
                progress.update(task, advance=1)
    
    # Display results table
    if open_ports:
        table = Table(title="Open Ports", show_header=True, header_style="bold cyan")
        table.add_column("Port", style="cyan")
        table.add_column("Service", style="bright_magenta")
        table.add_column("Status", style="green")
        
        for port_info in sorted(open_ports, key=lambda x: x["port"]):
            table.add_row(
                str(port_info["port"]),
                port_info["service"],
                "Open"
            )
        
        console.print("\n")
        console.print(table)
        console.print(f"\n[green]Found {len(open_ports)} open ports[/]")
    else:
        console.print("\n[yellow]No open ports found in the specified range[/]")
    
    console.print(f"[dim]Closed ports: {closed_count}[/]")
    
    results["open_ports_count"] = len(open_ports)
    results["closed_ports_count"] = closed_count
    
    # Export results if requested
    if export:
        export_results(results, export, config.get("export_format", "json"))

@app.command()
def batch(
    file: str = typer.Argument(..., help="File containing list of hosts/commands"),
    command: str = typer.Option("ping", "--command", "-c", help="Command to run (ping, dns, scan)")
):
    """📦 Run batch operations from a file."""
    file_path = Path(file)
    if not file_path.exists():
        console.print(error_panel(
            f"File not found: {file}",
            "Please provide a valid file path"
        ))
        raise typer.Exit(code=1)
    
    try:
        with open(file_path) as f:
            targets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        console.print(error_panel(f"Failed to read file: {e}"))
        raise typer.Exit(code=1)
    
    console.print(panel(
        f"Batch operation: [bold magenta]{command}[/]",
        f"Processing {len(targets)} targets from {file}"
    ))
    
    for i, target in enumerate(targets, 1):
        console.print(f"\n[cyan]═══ [{i}/{len(targets)}] Processing: {target} ═══[/]\n")
        
        try:
            if command == "ping":
                ping_host(target, count=2, timeout=3.0, export=None)
            elif command == "dns":
                dns(target, record_type="A", export=None)
            elif command == "scan":
                # For scan, check if port range is specified
                parts = target.split(':')
                if len(parts) == 2:
                    host, ports = parts
                    scan(host, ports, timeout=0.3, threads=50, export=None)
                else:
                    scan(target, "80,443", timeout=0.3, threads=50, export=None)
            else:
                console.print(f"[yellow]Unknown command: {command}[/]")
        except Exception as e:
            console.print(f"[red]Failed to process {target}: {e}[/]")
        
        # Small delay between operations
        if i < len(targets):
            time.sleep(0.5)
    
    console.print(success_panel(f"Batch operation completed: {len(targets)} targets processed"))

@app.command()
def config_cmd(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    set_key: Optional[str] = typer.Option(None, "--set", help="Set config key=value"),
    reset: bool = typer.Option(False, "--reset", "-r", help="Reset to default configuration")
):
    """⚙️ Manage neoTUI configuration settings."""
    if reset:
        if Confirm.ask("Reset configuration to defaults?"):
            config.settings = config.default_config()
            config.save()
            console.print(success_panel("Configuration reset to defaults"))
            return
    
    if set_key:
        if '=' not in set_key:
            console.print(error_panel(
                "Invalid format for --set",
                "Use format: --set key=value (e.g., --set default_timeout=10)"
            ))
            raise typer.Exit(code=1)
        
        key, value = set_key.split('=', 1)
        
        # Try to parse value as appropriate type
        try:
            # Try as number first
            if '.' in value:
                value = float(value)
            else:
                value = int(value)
        except ValueError:
            # Keep as string
            pass
        
        config.set(key, value)
        console.print(success_panel(f"Configuration updated: {key} = {value}"))
        return
    
    # Show configuration
    table = Table(title="neoTUI Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="bright_magenta")
    table.add_column("Description", style="dim")
    
    descriptions = {
        "default_timeout": "Default timeout for network operations (seconds)",
        "ping_count": "Default number of pings to send",
        "scan_timeout": "Timeout for port scanning (seconds)",
        "http_timeout": "Timeout for HTTP requests (seconds)",
        "export_format": "Default export format (json/csv)",
        "color_scheme": "Color scheme for output"
    }
    
    for key, value in config.settings.items():
        desc = descriptions.get(key, "")
        table.add_row(key, str(value), desc)
    
    console.print(table)
    console.print("\n[dim]Config file:[/] " + str(CONFIG_FILE))
    console.print("[dim]Use --set key=value to modify settings[/]")

# Add command aliases
app.command(name="p")(ping_host)
app.command(name="d")(dns)
app.command(name="h")(http)
app.command(name="t")(trace)
app.command(name="s")(scan)

# Improved help and version
def version_callback(value: bool):
    if value:
        console.print(panel("neoTUI v2.0", "Modern Network Toolkit"))
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version information"
    )
):
    """
    🚀 neoTUI - Modern Network Toolkit
    
    A powerful, user-friendly CLI for network diagnostics and testing.
    
    [bold cyan]Quick Start:[/]
    
    • ping google.com           - Test connectivity
    • dns example.com           - Resolve DNS records  
    • http https://api.github.com - Test HTTP endpoints
    • scan localhost 80,443     - Scan specific ports
    • trace google.com          - Trace network path
    
    [bold cyan]Features:[/]
    
    • Beautiful colored output with progress indicators
    • Export results to JSON/CSV files
    • Batch operations from file
    • Configurable settings
    • Detailed error messages with helpful suggestions
    
    [dim]Use --help with any command for more options[/]
    """
    pass

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/]")
        raise typer.Exit(code=130)
    except Exception as e:
        console.print(error_panel(f"Unexpected error: {e}", "Please report this issue"))
        raise typer.Exit(code=1)
