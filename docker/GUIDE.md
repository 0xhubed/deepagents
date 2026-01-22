# DeepAgents Docker Setup Guide

This guide explains how to run DeepAgents in a Docker container on Windows, with support for local LLMs via Ollama.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Docker Setup](#docker-setup)
4. [File Handling](#file-handling)
5. [File Format Best Practices](#file-format-best-practices)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Running DeepAgents in Docker provides:

- **Cross-platform compatibility**: Linux environment inside the container handles all shell commands
- **No Windows command issues**: The agent uses bash/Linux commands natively
- **Easy file access**: Windows folders are mounted into the container
- **Isolation**: Dependencies don't affect your host system
- **Portability**: Same setup works on any machine with Docker

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Windows Host                                                    │
│                                                                  │
│  ┌──────────────────┐      ┌─────────────────────────────────┐  │
│  │ C:\agent-workspace│ ←──→ │  Docker Container               │  │
│  │                  │      │  ┌─────────────────────────┐    │  │
│  │  - project files │      │  │ /workspace              │    │  │
│  │  - input data    │      │  │  - same files appear    │    │  │
│  │  - output files  │      │  │    here automatically   │    │  │
│  │                  │      │  └─────────────────────────┘    │  │
│  └──────────────────┘      │                                 │  │
│                            │  DeepAgents CLI (Linux)         │  │
│                            └───────────────┬─────────────────┘  │
│                                            │                     │
└────────────────────────────────────────────┼─────────────────────┘
                                             │ API calls
                                             ▼
                              ┌─────────────────────────────┐
                              │  Ollama Server              │
                              │  http://10.8.137.71:11435   │
                              │                             │
                              │  Models:                    │
                              │  - gpt-oss:20b              │
                              │  - glm-4.7-flash:latest     │
                              └─────────────────────────────┘
```

---

## Quick Start

### Prerequisites

1. **Docker Desktop for Windows** installed and running
   - Download from: https://www.docker.com/products/docker-desktop/
   - Ensure WSL2 backend is enabled (Docker Desktop handles this automatically)

2. **Network access** to your Ollama server (http://10.8.137.71:11435)

### Steps

1. **Create your workspace folder** on Windows:
   ```
   C:\agent-workspace
   ```

2. **Copy Docker files** to a location (e.g., `C:\deepagents-docker\`)

3. **Configure environment**: Edit `.env` file with your settings

4. **Run the agent**: Double-click `run-agent.bat`

---

## Docker Setup

### Files Overview

```
docker/
├── Dockerfile           # Container image definition
├── docker-compose.yml   # Service configuration
├── .env.example         # Example environment variables
├── run-agent.bat        # Windows startup script
└── GUIDE.md            # This documentation
```

### Building the Image

```bash
# From the docker/ directory
docker-compose build
```

### Running the Container

**Option 1: Using docker-compose (recommended)**
```bash
docker-compose run --rm deepagents
```

**Option 2: Using the batch script**
Double-click `run-agent.bat` or run from command prompt:
```cmd
run-agent.bat
```

**Option 3: Direct docker run**
```bash
docker run -it --rm \
  -v C:\agent-workspace:/workspace \
  -e OLLAMA_BASE_URL=http://10.8.137.71:11435 \
  -e OLLAMA_MODEL=gpt-oss:20b \
  deepagents-cli
```

---

## File Handling

### How Volume Mounts Work

Docker volume mounts create a bridge between a Windows folder and a path inside the container:

| Windows Path | Container Path | Description |
|--------------|----------------|-------------|
| `C:\agent-workspace` | `/workspace` | Your working directory |
| `C:\agent-workspace\input` | `/workspace/input` | Input files |
| `C:\agent-workspace\output` | `/workspace/output` | Generated output |

**Key points:**
- Files are NOT copied - they exist in one place (Windows) and are accessible from both sides
- Changes made by the agent appear instantly on Windows
- Changes you make on Windows appear instantly in the container
- File permissions are handled automatically by Docker Desktop

### Recommended Workspace Structure

Create this structure on Windows:

```
C:\agent-workspace\
├── input\                    # Place files for the agent to process
│   ├── data\                 # Data files (CSV, JSON, etc.)
│   ├── documents\            # Reference documents (Markdown, TXT)
│   └── requirements\         # Project requirements, specs
├── output\                   # Agent-generated output goes here
│   ├── code\                 # Generated code
│   ├── reports\              # Generated reports
│   └── exports\              # Exported/converted files
├── projects\                 # Active projects
│   └── my-project\           # Individual project folders
└── temp\                     # Temporary working files
```

### Path Translation

When talking to the agent, use **Linux-style paths**:

| You have on Windows | Tell the agent |
|---------------------|----------------|
| `C:\agent-workspace\input\data.csv` | `/workspace/input/data.csv` |
| `C:\agent-workspace\projects\myapp` | `/workspace/projects/myapp` |

**Example prompt:**
```
Please analyze the CSV file at /workspace/input/sales_data.csv
and create a summary report at /workspace/output/reports/sales_summary.md
```

---

## File Format Best Practices

### Preferred Formats

| Use Case | Recommended Format | Why |
|----------|-------------------|-----|
| Documents | **Markdown (.md)** | Plain text, version-control friendly, easy to parse |
| Data | **CSV (.csv)** | Universal, text-based, easy to process |
| Structured data | **JSON (.json)** | Widely supported, human-readable |
| Configuration | **YAML (.yaml)** | Readable, good for config files |
| Code | Native extensions | `.py`, `.js`, `.ts`, etc. |

### Excel Files → CSV Conversion

**The agent cannot directly read Excel files (.xlsx, .xls)**. Convert them to CSV first.

#### Why CSV instead of Excel?

- CSV is plain text - the agent can read and manipulate it directly
- No proprietary format dependencies
- Smaller file sizes
- Better for version control
- Avoids formatting/macro complications

#### How to Convert Excel to CSV

**Option 1: Manual conversion in Excel**
1. Open the Excel file
2. File → Save As
3. Choose "CSV (Comma delimited) (*.csv)"
4. Save to `C:\agent-workspace\input\`

**Option 2: Using Python script**

Place this script in your workspace as `convert_excel.py`:

```python
import pandas as pd
import sys
from pathlib import Path

def convert_excel_to_csv(excel_path: str, output_dir: str = None):
    """Convert Excel file to CSV(s).

    If the Excel file has multiple sheets, creates one CSV per sheet.
    """
    excel_path = Path(excel_path)
    output_dir = Path(output_dir) if output_dir else excel_path.parent

    # Read all sheets
    excel_file = pd.ExcelFile(excel_path)

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # Create output filename
        if len(excel_file.sheet_names) == 1:
            csv_name = excel_path.stem + '.csv'
        else:
            csv_name = f"{excel_path.stem}_{sheet_name}.csv"

        csv_path = output_dir / csv_name
        df.to_csv(csv_path, index=False)
        print(f"Created: {csv_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_excel.py <excel_file> [output_dir]")
        sys.exit(1)

    excel_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    convert_excel_to_csv(excel_file, output_dir)
```

Run it:
```bash
python convert_excel.py input/financial_data.xlsx input/data/
```

**Option 3: Using PowerShell (Windows)**

```powershell
# Convert single Excel file to CSV
$excel = New-Object -ComObject Excel.Application
$workbook = $excel.Workbooks.Open("C:\agent-workspace\input\data.xlsx")
$workbook.SaveAs("C:\agent-workspace\input\data.csv", 6)  # 6 = CSV format
$workbook.Close()
$excel.Quit()
```

#### Handling Multiple Sheets

If your Excel file has multiple sheets:
1. Convert each sheet to a separate CSV file
2. Name them descriptively: `sales_2024_q1.csv`, `sales_2024_q2.csv`
3. Or combine into one CSV if the structure is the same

#### Data Preparation Tips

Before converting to CSV:
1. **Remove merged cells** - they don't translate well to CSV
2. **Flatten headers** - ensure single-row headers
3. **Remove formatting** - colors, fonts don't carry over (and shouldn't)
4. **Check for special characters** - ensure proper encoding (UTF-8)
5. **Handle dates** - convert to ISO format (YYYY-MM-DD) if possible

### Markdown Files

Markdown is the preferred format for documents the agent reads or writes.

#### Why Markdown?

- Plain text - no special software needed
- Easy for the agent to read, parse, and generate
- Renders nicely in many tools (GitHub, VS Code, etc.)
- Version control friendly
- Supports code blocks, tables, lists

#### Markdown Best Practices

**For input documents (requirements, specs):**
```markdown
# Project Requirements

## Overview
Brief description of what you need.

## Detailed Requirements

### Feature 1: User Authentication
- Must support email/password login
- Must support OAuth (Google, GitHub)
- Session timeout: 30 minutes

### Feature 2: Dashboard
- Display key metrics
- Support date range filtering

## Technical Constraints
- Python 3.11+
- PostgreSQL database
- REST API

## Out of Scope
- Mobile app (future phase)
- Real-time notifications
```

**For data documentation:**
```markdown
# Dataset: Sales Data

## Source
Exported from Salesforce on 2024-01-15

## Files
- `sales_2024.csv` - All sales transactions for 2024

## Schema

| Column | Type | Description |
|--------|------|-------------|
| id | integer | Unique transaction ID |
| date | date | Transaction date (YYYY-MM-DD) |
| amount | decimal | Sale amount in USD |
| customer_id | integer | Reference to customer |
| product_id | integer | Reference to product |

## Notes
- Amounts are in USD
- Dates are in UTC timezone
```

### Other File Types

| File Type | Handling |
|-----------|----------|
| **PDF** | Convert to text/markdown if possible, or extract relevant data |
| **Word (.docx)** | Convert to markdown or plain text |
| **Images** | The agent can view images if needed |
| **JSON** | Fully supported, use for structured data |
| **XML** | Supported, but JSON preferred for new data |
| **SQL** | Supported for database schemas and queries |

---

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Ollama Configuration (Required)
OLLAMA_BASE_URL=http://10.8.137.71:11435
OLLAMA_MODEL=gpt-oss:20b

# Alternative models
# OLLAMA_MODEL=glm-4.7-flash:latest

# Optional: Cloud provider fallbacks (if Ollama unavailable)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Optional: Web search capability
# TAVILY_API_KEY=...

# Optional: LangSmith tracing for debugging
# LANGCHAIN_TRACING_V2=true
# LANGSMITH_API_KEY=...
# LANGSMITH_PROJECT=deepagents-local
```

### Switching Models

To use a different Ollama model:

**Option 1: Change `.env` file**
```bash
OLLAMA_MODEL=glm-4.7-flash:latest
```

**Option 2: Command line override**
```bash
docker-compose run --rm deepagents --model "ollama:glm-4.7-flash:latest"
```

### Custom Workspace Path

To use a different workspace folder, edit `docker-compose.yml`:

```yaml
volumes:
  - D:\my-projects:/workspace  # Change left side to your path
```

Or edit `run-agent.bat`:
```batch
set WORKSPACE=D:\my-projects
```

---

## Troubleshooting

### Cannot connect to Ollama server

**Symptoms:** Error about connection refused or timeout

**Solutions:**
1. Verify Ollama server is running:
   ```bash
   curl http://10.8.137.71:11435/api/tags
   ```
2. Check firewall allows connection from your machine
3. Verify the port is correct (11435 not 11434)

### Files not appearing in container

**Symptoms:** Agent says file doesn't exist, but it's on your Windows drive

**Solutions:**
1. Ensure file is in the mounted workspace folder
2. Use correct Linux path (`/workspace/...` not `C:\...`)
3. Check Docker Desktop has access to the drive (Settings → Resources → File Sharing)

### Permission denied errors

**Symptoms:** Agent cannot write files

**Solutions:**
1. Restart Docker Desktop
2. Check Windows folder permissions
3. Try running Docker Desktop as administrator

### Model not found

**Symptoms:** Error about model not available

**Solutions:**
1. Verify model is pulled on Ollama server:
   ```bash
   curl http://10.8.137.71:11435/api/tags
   ```
2. Check model name spelling matches exactly
3. Pull the model if missing:
   ```bash
   # On the Ollama server
   ollama pull gpt-oss:20b
   ```

### Container exits immediately

**Symptoms:** Container starts and stops without showing prompt

**Solutions:**
1. Run with `-it` flags for interactive mode
2. Check Docker logs: `docker-compose logs`
3. Ensure `.env` file exists and has required variables

---

## Usage Examples

### Example 1: Analyze CSV Data

1. Place your CSV file:
   ```
   C:\agent-workspace\input\sales_data.csv
   ```

2. Start the agent:
   ```
   run-agent.bat
   ```

3. Prompt:
   ```
   Analyze the sales data at /workspace/input/sales_data.csv
   Calculate monthly totals and identify top products.
   Save the analysis to /workspace/output/reports/sales_analysis.md
   ```

### Example 2: Code Generation

1. Create requirements file:
   ```
   C:\agent-workspace\input\requirements\api_spec.md
   ```

2. Prompt:
   ```
   Read the API specification at /workspace/input/requirements/api_spec.md
   Generate a Python FastAPI implementation in /workspace/output/code/api/
   ```

### Example 3: Document Processing

1. Place markdown documents:
   ```
   C:\agent-workspace\input\documents\
   ```

2. Prompt:
   ```
   Read all markdown files in /workspace/input/documents/
   Create a consolidated summary at /workspace/output/summary.md
   ```

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review Docker Desktop logs
3. Verify Ollama server connectivity
