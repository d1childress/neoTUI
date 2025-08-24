# neoTUI 🚀

[![Version](https://img.shields.io/badge/version-3.0-blue.svg)](https://github.com/d1childress/neoTUI)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-cross--platform-lightgrey.svg)]()

**neoTUI** is a modern, powerful network diagnostic toolkit written in Python featuring an intuitive command-line interface with rich visual output. Designed for network administrators, developers, and security professionals who need reliable network analysis tools with beautiful, informative displays.

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Detailed Usage](#-detailed-usage)
- [Batch Operations](#batch-operations)
- [Configuration](#-configuration-options)
- [Export Formats](#-export-formats)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 📸 Preview

<img width="1209" height="290" alt="CleanShot 2025-08-17 at 18 32 15" src="https://github.com/user-attachments/assets/0f7706f5-775b-47b5-aa7a-c2fa54b26362" />

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

## 📋 Requirements

### System Requirements
- **Python**: 3.11 or newer
- **Operating System**: Cross-platform (Windows, macOS, Linux)
- **Network Access**: Required for network diagnostic operations

### Python Dependencies
- `typer[all]` - Modern CLI framework
- `rich` - Rich text and beautiful formatting
- `requests` - HTTP library for web requests
- `ping3` - Pure Python ping implementation
- `dnspython` - DNS toolkit

### Optional Requirements
- **Administrator/Root privileges**: Required for some advanced network operations
- **ICMP permissions**: Needed for ping functionality on some systems

## 📦 Installation

### Option 1: Quick Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/d1childress/neoTUI.git
cd neoTUI

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 neoTUI.py --version
```

### Option 2: Development Installation

For development or isolated environments:

```bash
# Clone the repository
git clone https://github.com/d1childress/neoTUI.git
cd neoTUI

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 neoTUI.py --version
```

### Troubleshooting Installation

- **Permission Issues**: On some systems, you may need to use `sudo` for ping operations
- **Python Version**: Ensure you're using Python 3.11+ with `python3 --version`
- **Dependencies**: If pip fails, try `pip3` or `python3 -m pip`

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

## 🔧 Troubleshooting

### Common Issues

#### Permission Denied Errors
```bash
# Problem: Permission denied when running ping operations
# Solution: Run with appropriate privileges
sudo python3 neoTUI.py ping google.com

# Or add user to appropriate group (Linux)
sudo setcap cap_net_raw+ep /usr/bin/python3
```

#### Import Errors
```bash
# Problem: Module not found errors
# Solution: Ensure all dependencies are installed
pip install -r requirements.txt

# For specific modules:
pip install typer rich requests ping3 dnspython
```

#### Slow Performance
- **Network latency**: Adjust timeout values with `--timeout`
- **Port scanning**: Reduce thread count with `--threads`
- **Large batch operations**: Process smaller batches

#### Export Issues
```bash
# Problem: Cannot write export files
# Solution: Check directory permissions
chmod 755 /path/to/export/directory

# Use absolute paths for export
python3 neoTUI.py ping google.com --export /full/path/to/results.json
```

### Platform-Specific Notes

#### Windows
- Use `python` instead of `python3` in most cases
- Some operations may require "Run as Administrator"
- Windows Defender may flag network scanning tools

#### macOS
- Requires Python 3.11+ from Homebrew or python.org
- Some network operations may require `sudo`
- Firewall settings may affect scanning

#### Linux
- Install Python 3.11+ via package manager
- May require additional network capabilities
- Some distributions need `python3-pip` package

### Getting Help

If you encounter issues not covered here:

1. **Check Python version**: `python3 --version`
2. **Verify dependencies**: `pip list | grep -E "(typer|rich|requests)"`
3. **Test basic functionality**: `python3 neoTUI.py --version`
4. **Review system logs**: Check for network policy restrictions
5. **Create an issue**: [GitHub Issues](https://github.com/d1childress/neoTUI/issues)

## 🤝 Contributing

We welcome contributions to neoTUI! Whether you're reporting bugs, suggesting features, or submitting code improvements, your help makes the project better.

### Ways to Contribute

- 🐛 **Bug Reports**: Found an issue? [Create an issue](https://github.com/d1childress/neoTUI/issues)
- 💡 **Feature Requests**: Have an idea? We'd love to hear it!
- 📖 **Documentation**: Help improve our docs and examples
- 🧪 **Testing**: Test on different platforms and report compatibility
- 💻 **Code**: Submit pull requests for bug fixes or new features

### Development Setup

```bash
# Fork and clone your fork
git clone https://github.com/YOUR_USERNAME/neoTUI.git
cd neoTUI

# Create development environment
python3 -m venv dev-env
source dev-env/bin/activate  # On Windows: dev-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests (if available)
python3 -m pytest

# Test your changes
python3 neoTUI.py --version
```

### Pull Request Guidelines

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Test** your changes thoroughly
4. **Commit** with clear messages (`git commit -m 'Add amazing feature'`)
5. **Push** to your branch (`git push origin feature/amazing-feature`)
6. **Open** a Pull Request

### Code Standards

- Follow existing code style and patterns
- Include docstrings for new functions
- Test on multiple platforms when possible
- Update documentation for new features

## 📋 Changelog

### Version 3.0 (Latest)
- 🎨 **New Features**: Multiple color themes support
- 📊 **Enhancement**: ASCII data visualization
- 🟢 **Improvement**: Smart health indicators
- 📚 **Feature**: Command history tracking
- ⚡ **Performance**: Enhanced execution speed
- 🎯 **Export**: Advanced export options

### Previous Versions
- **v2.x**: Core network toolkit functionality
- **v1.x**: Initial release with basic ping, DNS, and HTTP testing

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
