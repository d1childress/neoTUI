import re
import socket
import subprocess
import sys
import json
import csv
import statistics
from typing import List, Optional, Dict, Any, Union
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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from rich.box import ROUNDED, DOUBLE, HEAVY, MINIMAL
from rich.style import Style
from rich.layout import Layout
from rich.live import Live
from rich.tree import Tree
from rich.bar import Bar

app = typer.Typer(
    help="🚀 Modern network toolkit - Fast, colorful, and user-friendly",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

# Configuration support
CONFIG_FILE = Path.home() / ".neotui_config.json"

class ThemeManager:
    """Advanced theme management for neoTUI"""
    def __init__(self):
        self.themes = {
            "default": {
                "primary": "bright_cyan",
                "secondary": "bright_magenta",
                "success": "bright_green",
                "warning": "bright_yellow",
                "error": "bright_red",
                "info": "bright_blue",
                "dim": "dim",
                "border": "cyan"
            },
            "dark": {
                "primary": "cyan",
                "secondary": "magenta",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "info": "blue",
                "dim": "dim white",
                "border": "dim cyan"
            },
            "light": {
                "primary": "blue",
                "secondary": "purple",
                "success": "dark_green",
                "warning": "dark_orange",
                "error": "dark_red",
                "info": "dark_blue",
                "dim": "grey50",
                "border": "grey70"
            },
            "neon": {
                "primary": "bright_cyan",
                "secondary": "bright_magenta",
                "success": "bright_green",
                "warning": "bright_yellow",
                "error": "bright_red",
                "info": "electric_blue",
                "dim": "dim bright_white",
                "border": "bright_cyan"
            }
        }
        self.current_theme = "default"
    
    def get_color(self, color_type: str) -> str:
        return self.themes[self.current_theme].get(color_type, "white")
    
    def set_theme(self, theme_name: str):
        if theme_name in self.themes:
            self.current_theme = theme_name

class Config:
    """Enhanced configuration manager for neoTUI"""
    def __init__(self):
        self.settings = self.load()
        self.theme_manager = ThemeManager()
        if "theme" in self.settings:
            self.theme_manager.set_theme(self.settings["theme"])
    
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
            "color_scheme": "bright",
            "theme": "default",
            "show_animations": True,
            "show_charts": True,
            "save_history": True,
            "max_history_entries": 100
        }
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.settings[key] = value
        if key == "theme":
            self.theme_manager.set_theme(value)
        self.save()

config = Config()

# ----- Enhanced UI Helpers -----

def get_status_icon(status: str) -> str:
    """Get appropriate icon for status"""
    icons = {
        "success": "🟢",
        "warning": "🟡",
        "error": "🔴",
        "info": "🔵",
        "loading": "⏳",
        "network": "🌐",
        "security": "🔒",
        "speed": "⚡",
        "chart": "📊"
    }
    return icons.get(status, "ℹ️")

def create_gradient_panel(title: str, subtitle: str = "", panel_type: str = "info") -> Panel:
    """Create an enhanced panel with gradients and icons"""
    theme = config.theme_manager
    
    # Panel type configurations
    panel_configs = {
        "info": {
            "icon": get_status_icon("info"),
            "color": theme.get_color("primary"),
            "border_color": theme.get_color("border"),
            "box": ROUNDED
        },
        "success": {
            "icon": get_status_icon("success"),
            "color": theme.get_color("success"),
            "border_color": theme.get_color("success"),
            "box": ROUNDED
        },
        "error": {
            "icon": get_status_icon("error"),
            "color": theme.get_color("error"),
            "border_color": theme.get_color("error"),
            "box": HEAVY
        },
        "warning": {
            "icon": get_status_icon("warning"),
            "color": theme.get_color("warning"),
            "border_color": theme.get_color("warning"),
            "box": ROUNDED
        },
        "network": {
            "icon": get_status_icon("network"),
            "color": theme.get_color("primary"),
            "border_color": theme.get_color("border"),
            "box": DOUBLE
        }
    }
    
    panel_config = panel_configs.get(panel_type, panel_configs["info"])
    
    # Format title with icon
    formatted_title = f"{panel_config['icon']} {title}"
    if subtitle:
        formatted_title += f"\n[{theme.get_color('dim')}]{subtitle}[/]"
    
    return Panel(
        formatted_title,
        style=panel_config["color"],
        border_style=panel_config["border_color"],
        box=panel_config["box"],
        padding=(0, 1)
    )

def panel(title: str, subtitle: str = "") -> Panel:
    """Create a styled panel with optional subtitle (backward compatibility)"""
    return create_gradient_panel(title, subtitle, "network")

def error_panel(message: str, suggestion: str = "") -> Panel:
    """Create an enhanced error panel with suggestions"""
    content = f"[{config.theme_manager.get_color('error')}]{message}[/]"
    if suggestion:
        content += f"\n\n[{config.theme_manager.get_color('warning')}]💡 Suggestion: {suggestion}[/]"
    return create_gradient_panel(content, panel_type="error")

def success_panel(message: str) -> Panel:
    """Create an enhanced success panel"""
    return create_gradient_panel(f"[{config.theme_manager.get_color('success')}]{message}[/]", panel_type="success")

def warning_panel(message: str) -> Panel:
    """Create a warning panel"""
    return create_gradient_panel(f"[{config.theme_manager.get_color('warning')}]{message}[/]", panel_type="warning")

def create_ascii_chart(data: List[float], title: str = "", width: int = 50) -> str:
    """Create a simple ASCII bar chart"""
    if not data or not config.get("show_charts", True):
        return ""
    
    max_val = max(data) if data else 1
    min_val = min(data) if data else 0
    
    chart_lines = []
    if title:
        chart_lines.append(f"📊 {title}")
        chart_lines.append("═" * len(f"📊 {title}"))
    
    for i, value in enumerate(data):
        if max_val > 0:
            bar_length = int((value / max_val) * width)
        else:
            bar_length = 0
        
        bar = "█" * bar_length + "░" * (width - bar_length)
        chart_lines.append(f"{i+1:2d} │{bar}│ {value:.2f}ms")
    
    if data:
        stats_line = f"Min: {min_val:.2f}ms | Max: {max_val:.2f}ms | Avg: {statistics.mean(data):.2f}ms"
        chart_lines.append("─" * len(stats_line))
        chart_lines.append(stats_line)
    
    return "\n".join(chart_lines)

def create_health_indicator(value: float, thresholds: Dict[str, float]) -> str:
    """Create a health status indicator with emoji"""
    if value <= thresholds.get("good", 50):
        return f"🟢 Excellent ({value:.1f})"
    elif value <= thresholds.get("okay", 100):
        return f"🟡 Good ({value:.1f})"
    elif value <= thresholds.get("poor", 200):
        return f"🟠 Fair ({value:.1f})"
    else:
        return f"🔴 Poor ({value:.1f})"

def create_trend_indicator(current: float, previous: float) -> str:
    """Create a trend indicator"""
    if abs(current - previous) < 0.01:  # Essentially the same
        return "➡️"
    elif current < previous:
        return "📈 Improving"
    else:
        return "📉 Declining"

def create_enhanced_table(title: str, columns: List[str], data: List[List], show_stats: bool = False) -> Table:
    """Create an enhanced table with better styling"""
    theme = config.theme_manager
    
    table = Table(
        title=f"📊 {title}",
        show_header=True,
        header_style=f"bold {theme.get_color('primary')}",
        border_style=theme.get_color("border"),
        box=ROUNDED,
        show_lines=True
    )
    
    # Add columns with appropriate styling
    for i, column in enumerate(columns):
        if i == 0:
            table.add_column(column, style=theme.get_color("info"))
        elif "status" in column.lower() or "result" in column.lower():
            table.add_column(column, justify="center")
        elif "time" in column.lower() or "latency" in column.lower():
            table.add_column(column, style=theme.get_color("secondary"), justify="right")
        else:
            table.add_column(column, style=theme.get_color("primary"))
    
    # Add data rows
    for row in data:
        table.add_row(*[str(cell) for cell in row])
    
    return table

def save_to_history(command: str, data: Dict[str, Any]):
    """Save command results to history"""
    if not config.get("save_history", True):
        return
    
    history_file = Path.home() / ".neotui_history.json"
    history = []
    
    # Load existing history
    if history_file.exists():
        try:
            with open(history_file) as f:
                history = json.load(f)
        except:
            history = []
    
    # Add new entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "data": data
    }
    history.append(entry)
    
    # Keep only the most recent entries
    max_entries = config.get("max_history_entries", 100)
    history = history[-max_entries:]
    
    # Save back to file
    try:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        console.print(f"[{config.theme_manager.get_color('warning')}]Warning: Could not save history: {e}[/]")

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
    """Enhanced export functionality with multiple formats"""
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
        elif format == "html":
            # Generate HTML report
            html_content = generate_html_report(data)
            with open(filename, 'w') as f:
                f.write(html_content)
        elif format == "xml":
            # Generate XML export
            xml_content = generate_xml_report(data)
            with open(filename, 'w') as f:
                f.write(xml_content)
        
        console.print(success_panel(f"Results exported to {filename} ({format.upper()} format)"))
        return True
    except Exception as e:
        console.print(error_panel(f"Failed to export: {e}"))
        return False

def generate_html_report(data: Dict[str, Any]) -> str:
    """Generate an HTML report from data"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>neoTUI Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .success {{ border-left: 5px solid #27ae60; }}
            .warning {{ border-left: 5px solid #f39c12; }}
            .error {{ border-left: 5px solid #e74c3c; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌐 neoTUI Network Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="section">
            <h2>Command: {data.get('command', 'Unknown')}</h2>
            <pre>{json.dumps(data, indent=2, default=str)}</pre>
        </div>
    </body>
    </html>
    """
    return html

def generate_xml_report(data: Dict[str, Any]) -> str:
    """Generate an XML report from data"""
    def dict_to_xml(d, root="item"):
        xml = f"<{root}>"
        for key, value in d.items():
            if isinstance(value, dict):
                xml += dict_to_xml(value, key)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        xml += dict_to_xml(item, key)
                    else:
                        xml += f"<{key}>{item}</{key}>"
            else:
                xml += f"<{key}>{value}</{key}>"
        xml += f"</{root}>"
        return xml
    
    return f'<?xml version="1.0" encoding="UTF-8"?>\\n{dict_to_xml(data, "report")}'

@app.command()
def export_history(
    output: str = typer.Argument(..., help="Output filename"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, csv, html, xml)"),
    command_filter: Optional[str] = typer.Option(None, "--filter", help="Filter by command type")
):
    """📁 Export command history to various formats."""
    history_file = Path.home() / ".neotui_history.json"
    
    if not history_file.exists():
        console.print(error_panel("No command history found"))
        raise typer.Exit(code=1)
    
    try:
        with open(history_file) as f:
            history_data = json.load(f)
    except Exception as e:
        console.print(error_panel(f"Failed to read history: {e}"))
        raise typer.Exit(code=1)
    
    # Filter by command type if specified
    if command_filter:
        history_data = [entry for entry in history_data if entry.get("command") == command_filter]
    
    if not history_data:
        console.print(warning_panel("No matching history entries found"))
        return
    
    # Prepare export data
    export_data = {
        "export_type": "history",
        "generated": datetime.now().isoformat(),
        "total_entries": len(history_data),
        "filter": command_filter,
        "entries": history_data
    }
    
    success = export_results(export_data, output, format)
    if success:
        console.print(create_gradient_panel(
            f"History Export Complete",
            f"Exported {len(history_data)} entries to {output}",
            "success"
        ))

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
    latency_data = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
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
                    latency_data.append(delay)
                    
                    results.append({
                        "sequence": i + 1,
                        "status": "success",
                        "latency_ms": round(delay, 2),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Enhanced status display with health indicator
                    health_status = create_health_indicator(delay, {"good": 50, "okay": 100, "poor": 200})
                    console.print(f"  [green]✓ Reply from {host}: time={delay:.1f}ms {health_status}[/]")
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
    
    # Display enhanced statistics
    if successful > 0:
        avg_delay = total_delay / successful
        packet_loss = ((count - successful) / count) * 100
        
        # Create enhanced statistics table
        stats_data = [
            ["Host", host],
            ["Packets Sent", str(count)],
            ["Packets Received", str(successful)],
            ["Packet Loss", f"{packet_loss:.1f}%"],
            ["Min Latency", f"{min_delay:.2f} ms"],
            ["Max Latency", f"{max_delay:.2f} ms"],
            ["Avg Latency", f"{avg_delay:.2f} ms"],
            ["Health Status", create_health_indicator(avg_delay, {"good": 50, "okay": 100, "poor": 200})]
        ]
        
        stats_table = create_enhanced_table("Ping Statistics", ["Metric", "Value"], stats_data)
        console.print("\n")
        console.print(stats_table)
        
        # Show ASCII chart if enabled
        if config.get("show_charts", True) and len(latency_data) > 1:
            chart = create_ascii_chart(latency_data, "Latency Trend", 40)
            if chart:
                console.print(f"\n[{config.theme_manager.get_color('info')}]{chart}[/]")
        
        # Save to history
        ping_data = {
            "host": host,
            "avg_latency": avg_delay,
            "packet_loss": packet_loss,
            "successful_pings": successful,
            "total_pings": count
        }
        save_to_history("ping", ping_data)
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

@app.command()
def theme(
    name: Optional[str] = typer.Argument(None, help="Theme name (default, dark, light, neon)"),
    list_themes: bool = typer.Option(False, "--list", "-l", help="List available themes")
):
    """🎨 Manage color themes for neoTUI."""
    if list_themes:
        console.print(create_gradient_panel("Available Themes", panel_type="info"))
        
        theme_table = create_enhanced_table(
            "Themes", 
            ["Theme", "Description", "Status"],
            [
                ["default", "Default bright theme", "✅ Active" if config.theme_manager.current_theme == "default" else ""],
                ["dark", "Dark mode theme", "✅ Active" if config.theme_manager.current_theme == "dark" else ""],
                ["light", "Light mode theme", "✅ Active" if config.theme_manager.current_theme == "light" else ""],
                ["neon", "High contrast neon", "✅ Active" if config.theme_manager.current_theme == "neon" else ""]
            ]
        )
        console.print(theme_table)
        return
    
    if name:
        if name in config.theme_manager.themes:
            config.set("theme", name)
            console.print(success_panel(f"Theme changed to '{name}'"))
            console.print(create_gradient_panel("Theme Preview", f"This is how your new '{name}' theme looks!", "info"))
        else:
            available_themes = ", ".join(config.theme_manager.themes.keys())
            console.print(error_panel(
                f"Unknown theme: {name}",
                f"Available themes: {available_themes}"
            ))
            raise typer.Exit(code=1)
    else:
        current_theme = config.theme_manager.current_theme
        console.print(create_gradient_panel(f"Current Theme: {current_theme}", "Use --list to see all available themes", "info"))

@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of history entries to show"),
    command_filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by command type"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear command history")
):
    """📚 View and manage command history."""
    history_file = Path.home() / ".neotui_history.json"
    
    if clear:
        if Confirm.ask("Clear all command history?"):
            if history_file.exists():
                history_file.unlink()
            console.print(success_panel("Command history cleared"))
            return
    
    if not history_file.exists():
        console.print(warning_panel("No command history found"))
        return
    
    try:
        with open(history_file) as f:
            history_data = json.load(f)
    except Exception as e:
        console.print(error_panel(f"Failed to read history: {e}"))
        return
    
    # Filter by command type if specified
    if command_filter:
        history_data = [entry for entry in history_data if entry.get("command") == command_filter]
    
    # Limit results
    history_data = history_data[-limit:]
    
    if not history_data:
        console.print(warning_panel("No matching history entries found"))
        return
    
    console.print(create_gradient_panel("Command History", f"Showing last {len(history_data)} entries", "info"))
    
    for entry in history_data:
        timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        command = entry["command"]
        data = entry.get("data", {})
        
        # Create summary based on command type
        if command == "ping":
            host = data.get("host", "unknown")
            avg_latency = data.get("avg_latency", 0)
            packet_loss = data.get("packet_loss", 0)
            summary = f"Host: {host} | Avg: {avg_latency:.1f}ms | Loss: {packet_loss:.1f}%"
        else:
            summary = str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
        
        console.print(f"[{config.theme_manager.get_color('dim')}]{timestamp}[/] [{config.theme_manager.get_color('info')}]{command}[/] {summary}")

@app.command()
def dashboard():
    """📊 Launch interactive dashboard (experimental)."""
    console.print(create_gradient_panel("Interactive Dashboard", "Real-time network monitoring", "info"))
    console.print(warning_panel("Dashboard mode is experimental and under development"))
    
    # This would be where we'd implement a live TUI dashboard
    # For now, show a preview of what it could look like
    
    layout = Layout()
    layout.split_column(
        Layout(create_gradient_panel("System Status", "All systems operational", "success"), size=3),
        Layout(create_gradient_panel("Recent Activity", "Last 5 commands executed", "info"), size=10),
    )
    
    console.print(layout)
    console.print("\n[dim]Press Ctrl+C to exit dashboard mode[/]")
    
    try:
        time.sleep(2)  # Simulate dashboard activity
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed[/]")

# Add command aliases
app.command(name="p")(ping_host)
app.command(name="d")(dns)
app.command(name="h")(http)
app.command(name="t")(trace)
app.command(name="s")(scan)

# Improved help and version
def version_callback(value: bool):
    if value:
        version_info = create_gradient_panel(
            "neoTUI v3.0", 
            "Enhanced Modern Network Toolkit with Advanced UI", 
            "info"
        )
        console.print(version_info)
        
        # Show feature highlights
        features = [
            "🎨 Multiple Color Themes",
            "📊 ASCII Data Visualization", 
            "🟢 Smart Health Indicators",
            "📚 Command History Tracking",
            "⚡ Enhanced Performance",
            "🎯 Advanced Export Options"
        ]
        
        feature_text = "\n".join([f"  {feature}" for feature in features])
        console.print(f"\n[{config.theme_manager.get_color('info')}]New Features:[/]\n{feature_text}")
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
