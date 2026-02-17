# UK Tax Residency Day Tracker

A self-hosted web application for tracking UK tax residency days, managing evidence, and generating annual residency statements. Designed for UK non-residents who need to monitor their UK presence under the Statutory Residence Test (SRT).

## Features

- **UK Tax Year Model**: Canonical 6 April → 5 April grouping for all data
- **Operational Profiles**: Year 1 / Year 2 / Year 3+ planning targets aligned to first full non-resident tax year
- **Dashboard**: Real-time UK presence control with GREEN/AMBER/RED risk status
- **Heatmap**: Visual calendar showing UK midnights per tax year
- **TNR 5-Year Clock**: Temporary Non-Residence planning timer
- **Travel Management**: CRUD for travel records with UK midnight computation
- **Evidence Vault**: Upload, categorise, and hash evidence files (SHA-256)
- **Annual Statements**: Generate HTML/PDF residency statements with hash manifests
- **Export Packs**: Summary + CSVs + attachments + hashes
- **Localhost-Only Deployment**: Docker with SSH tunnel access (no public exposure)

## Quick Start (Local Development)

```bash
# Clone and enter project
cd daytracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env and set SECRET_KEY to a random string

# Run development server
FLASK_ENV=development python run.py
```

Open http://localhost:8000 in your browser.

## VM Deployment (Docker)

### Prerequisites
- A VM with a public IP accessible via SSH
- Docker and Docker Compose installed

### 1. Install Docker on VM (Debian/Ubuntu)

```bash
ssh root@YOUR_VM_IP

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt-get install -y docker-compose-plugin

# Verify
docker compose version
```

### 2. Deploy the Application

```bash
# Create application directory
mkdir -p /opt/daytracker/{data,vault,backups}
cd /opt/daytracker

# Copy project files to VM (from your local machine)
# scp -r ./daytracker/* root@YOUR_VM_IP:/opt/daytracker/

# Or clone from your repo
# git clone YOUR_REPO_URL /opt/daytracker

# Configure environment
cp .env.example .env
nano .env  # Set SECRET_KEY to a long random string

# Build and start
docker compose up -d

# Check status
docker compose ps
docker compose logs -f
```

### 3. Access via SSH Tunnel

**Critical**: The app binds to `127.0.0.1:8000` only — it is NOT publicly accessible.

From your laptop/workstation:

```bash
ssh -L 8000:127.0.0.1:8000 root@YOUR_VM_IP
```

Then open http://localhost:8000 in your browser.

To run the tunnel in the background:

```bash
ssh -fNL 8000:127.0.0.1:8000 root@YOUR_VM_IP
```

### 4. Backups

```bash
# Manual backup
./scripts/backup.sh

# Automated nightly backup (add to crontab)
crontab -e
# Add this line:
# 0 2 * * * /opt/daytracker/scripts/backup.sh >> /var/log/daytracker-backup.log 2>&1
```

Backups are stored in `/opt/daytracker/backups/` and include:
- SQLite database snapshot (safe `.backup` command)
- Vault archive (tar.gz)
- Auto-cleanup of backups older than 30 days

## Configuration

Access Settings via the web UI or edit the config directly.

### Key Settings

| Setting | Description | Example |
|---------|-------------|---------|
| `departure_date` | Date you left the UK | `2026-03-26` |
| `first_full_nonresident_tax_year` | First complete tax year as non-resident | `2026-2027` |
| Year 1 Target | Conservative midnight limit for year 1 | `30` |
| Year 2 Target | Conservative midnight limit for year 2 | `85` |
| Year 3+ Target | Conservative midnight limit for year 3+ | `120` |

### Profile Mapping

| Tax Year | Profile | Based On |
|----------|---------|----------|
| First full non-resident year | Year 1 | `first_full_nonresident_tax_year` |
| Next year | Year 2 | +1 tax year |
| All subsequent years | Year 3+ | +2 tax years onwards |

### Risk Status

| Status | Condition |
|--------|-----------|
| 🟢 GREEN | `used <= target - buffer` |
| 🟡 AMBER | `target - buffer < used < target` |
| 🔴 RED | `used >= target` |

## Project Structure

```
daytracker/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # SQLAlchemy models
│   ├── config_manager.py    # Config table management
│   ├── tax_year.py          # UK tax year logic
│   ├── profiles.py          # Operational profile mapping
│   ├── uk_midnights.py      # UK midnight computation
│   ├── routes/              # Flask blueprints
│   │   ├── dashboard.py     # Main dashboard
│   │   ├── heatmap.py       # Heatmap view
│   │   ├── travels.py       # Travel CRUD
│   │   ├── evidence.py      # Evidence vault
│   │   ├── reports.py       # Annual statements
│   │   ├── settings.py      # Configuration
│   │   └── api.py           # JSON API
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS
├── tests/                   # pytest test suite
├── scripts/backup.sh        # Backup script
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── Makefile
├── requirements.txt
├── run.py
└── README.md
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Current tax year status + risk |
| `/api/config` | GET | Current configuration |
| `/api/midnights/<tax_year>` | GET | UK midnights for tax year |
| `/api/travels` | GET | All travel records (JSON) |

## Important Notes

- **Not Tax Advice**: This tool is for personal planning and record-keeping only. Always consult a qualified tax adviser.
- **SRT Simplification**: The app does not implement full SRT tie-counting logic. It relies on user-defined profile assumptions and conservative buffers.
- **Security**: The app has no authentication. Security is provided by localhost-only binding + SSH tunnel access.
- **UK Tax Year**: Always runs 6 April to 5 April. All grouping, reporting, and exports use this as the canonical period.

## License

Private use. All rights reserved.
