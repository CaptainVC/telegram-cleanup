# telegram-cleanup

Local utility to detect “trading-related” Telegram channels/groups and help you leave them.

- Runs locally on Windows (manual weekly run)
- Uses Telethon (Telegram user API)
- Generates a local HTML review report
- Leaves only what you explicitly select

## Quick start (Windows 11)

### 1) Install Python
Install Python 3.11+ from https://www.python.org/downloads/

### 2) Clone and install deps
```powershell
git clone https://github.com/CaptainVC/telegram-cleanup
cd telegram-cleanup
python -m pip install -r requirements.txt
```

### 3) Create `.env`
Copy `.env.example` → `.env` and fill:
- `TG_API_ID`
- `TG_API_HASH`

Get them from: https://my.telegram.org/apps

### 4) Run scan
```powershell
python tg_cleanup.py scan
```
First run will ask for OTP (and 2FA password if enabled). It stores a local session file so you won’t OTP every time.

Outputs:
- `out/report.html`
- `out/candidates.json`

### 5) Review + apply
Open `out/report.html`, select chats to leave, export `out/selection.json`, then:
```powershell
python tg_cleanup.py apply out/selection.json
```

## Notes
- No secrets are committed.
- Session files and outputs are ignored by git.

## License
MIT
