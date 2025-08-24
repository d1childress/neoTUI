# neoTUI 🚀

A modern, powerful network toolkit written in Python with a beautiful, colorful CLI interface.

<img width="1212" height="827" alt="CleanShot 2025-08-24 at 17 51 25" src="https://github.com/user-attachments/assets/fd0b0381-0a20-484c-98f1-0fb94f72f73c" />


## ✨ Features

- **🏓 Advanced Ping** - Detailed latency statistics with packet loss analysis
- **🔍 DNS Resolution** - Comprehensive DNS lookups with reverse DNS support
- **🌐 HTTP Testing** - Full HTTP request analysis with headers and timing
- **🛤️ Traceroute** - Visual network path tracing with hop details
- **🔓 Port Scanning** - Fast parallel port scanning with service detection
- **📦 Batch Operations** - Process multiple targets from a file
- **⚙️ Configuration** - Persistent settings management
- **📊 Export Results** - Save results in JSON or CSV format
- **🎨 Beautiful Output** - Rich colored tables and progress indicators
- **💡 Smart Error Handling** - Helpful error messages with suggestions

## 📦 Installation

1. Ensure you have Python 3.11 or newer.
2. Clone the repository and change into the project directory:
   ```bash
   git clone <repository_url>
   cd neoTUI
   ```
3. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Quick Start

```bash
# Get help
python neoTUI.py --help

# Show version
python neoTUI.py --version

# Quick commands with aliases
python neoTUI.py p google.com      # Ping (alias for 'ping')
python neoTUI.py d example.com     # DNS (alias for 'dns')
python neoTUI.py h https://api.github.com  # HTTP (alias for 'http')
python neoTUI.py s localhost 80,443  # Scan (alias for 'scan')
python neoTUI.py t google.com      # Trace (alias for 'trace')
```

## 📖 Detailed Usage

### Ping - Test Connectivity
```bash
# Basic ping
python neoTUI.py ping google.com

# Custom options
python neoTUI.py ping google.com --count 10 --timeout 5

# Export results
python neoTUI.py ping google.com --export ping_results.json
```

### DNS - Resolve Domain Names
```bash
# Basic DNS lookup
python neoTUI.py dns example.com

# Specific record type
python neoTUI.py dns example.com --type A

# Export results
python neoTUI.py dns example.com --export dns_results.json
```

### HTTP - Test Web Services
```bash
# Basic GET request
python neoTUI.py http https://api.github.com

# Show headers and use POST method
python neoTUI.py http https://httpbin.org/post --method POST --headers

# Custom timeout and export
python neoTUI.py http https://example.com --timeout 15 --export http_results.json
```

### Trace - Network Path Analysis
```bash
# Basic traceroute
python neoTUI.py trace google.com

# Limit maximum hops
python neoTUI.py trace example.com --max-hops 20
```

### Scan - Port Discovery
```bash
# Scan common ports
python neoTUI.py scan localhost

# Scan specific ports
python neoTUI.py scan example.com 80,443,8080

# Scan port range with custom settings
python neoTUI.py scan scanme.nmap.org 1-1000 --timeout 0.5 --threads 100

# Export scan results
python neoTUI.py scan localhost 1-65535 --export scan_results.json
```

### Batch Operations
```bash
# Run batch ping operations
python neoTUI.py batch hosts.txt --command ping

# Run batch DNS lookups
python neoTUI.py batch domains.txt --command dns

# Run batch port scans
python neoTUI.py batch targets.txt --command scan
```

### Configuration Management
```bash
# Show current configuration
python neoTUI.py config-cmd --show

# Set configuration values
python neoTUI.py config-cmd --set default_timeout=10
python neoTUI.py config-cmd --set export_format=csv

# Reset to defaults
python neoTUI.py config-cmd --reset
```

## 📝 Batch File Format

Create a text file with one target per line:
```text
# Comments start with #
google.com
8.8.8.8
github.com

# For port scanning, use host:ports format
localhost:80,443
scanme.nmap.org:22,80,443
```

## 🔧 Configuration Options

neoTUI stores configuration in `~/.neotui_config.json`:

- `default_timeout` - Default timeout for network operations (seconds)
- `ping_count` - Default number of pings to send
- `scan_timeout` - Timeout for port scanning (seconds)
- `http_timeout` - Timeout for HTTP requests (seconds)
- `export_format` - Default export format (json/csv)
- `color_scheme` - Color scheme for output

## 🎯 Pro Tips

1. **Use aliases for faster access**: `p`, `d`, `h`, `s`, `t` instead of full command names
2. **Export results for analysis**: Add `--export filename.json` to any command
3. **Batch operations for multiple targets**: Process entire lists efficiently
4. **Customize timeouts**: Adjust for slow networks or distant hosts
5. **Parallel scanning**: Use `--threads` for faster port scanning

## 🛡️ Security Note

- Port scanning should only be performed on systems you own or have permission to test
- Some networks may flag or block scanning activity
- Always respect rate limits and server resources when testing

## 📊 Export Formats

Results can be exported in:
- **JSON**: Structured data with full details
- **CSV**: Tabular format for spreadsheet analysis

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
