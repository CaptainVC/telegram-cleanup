# telegram-cleanup

Local utility to detect “trading-related” Telegram channels/groups and help you leave them.

- Runs locally on Windows (manual weekly run)
- Uses Telethon (Telegram user API)
- Generates a local HTML review report
- Leaves only what you explicitly select

## Quick start (Windows 11)

### Option A: Docker (recommended for reproducibility)

1) Install Docker Desktop (WSL2 backend).
2) In PowerShell:

```powershell
cd D:\Files\TelegramCleanup
docker compose run --rm telegram-cleanup python tg_cleanup.py scan
```

Then open `out\report.html`.

To apply a selection:

```powershell
docker compose run --rm telegram-cleanup python tg_cleanup.py apply out\selection.json
```

### Option B: Local Python



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

## Understanding credentials (important)
There are **two different things** involved:

1) **Telegram API app credentials** (in `.env`)
- `TG_API_ID` and `TG_API_HASH` come from https://my.telegram.org/apps
- They identify your *developer app* so Telethon can connect.

2) **Your account login** (entered interactively on first run)
- Phone number + OTP code (and 2FA password if enabled) are used to sign into your **Telegram user account**.
- After the first successful login, Telethon stores a local session file under:
  - `out/session/telegram_cleanup.session`
- Because the project directory is mounted into Docker, the session persists on your machine and future runs should not ask for OTP again.

> `.env` does **not** replace OTP/2FA. It only provides the API app credentials.

## Stopping Docker + running later
You can safely stop/remove containers in Docker Desktop.

Your Telegram login persists because Telethon stores a **session file** on your machine:
- `out/session/telegram_cleanup.session`

As long as that file remains, you generally **won’t need OTP again** even if you run the tool next month.

It will ask for OTP again if you delete the session file, revoke Telegram sessions (Settings → Devices), or Telegram invalidates the session.
