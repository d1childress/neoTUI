# neoTUI

A modern, minimal network toolkit written in Python with a bright, colorful CLI.

<img width="1209" height="290" alt="CleanShot 2025-08-17 at 18 32 15" src="https://github.com/user-attachments/assets/0f7706f5-775b-47b5-aa7a-c2fa54b26362" />

## Installation

1. Ensure you have Python 3.11 or newer.
2. Clone the repository and change into the project directory:
   ```bash
   git clone <repository_url>
   cd neoTUI
   ```
3. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run `neoTUI.py` with the desired command:

```bash
python neoTUI.py --help
```

### Examples

Ping a host:

```bash
python neoTUI.py ping google.com
```

Resolve DNS records:

```bash
python neoTUI.py dns example.com
```

Fetch a URL:

```bash
python neoTUI.py http https://example.com
```

Run a traceroute:

```bash
python neoTUI.py trace example.com
```

Scan TCP ports:

```bash
python neoTUI.py scan localhost 1-1024
```
