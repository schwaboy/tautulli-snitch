# Tautulli User Devices & IPs Reporter

A Python script to analyze Tautulli users by unique devices and IP addresses, matching the web UI's user history table.

## ✨ Features

- **Summary mode**: List all users with device counts and unique IP counts, sortable by name/devices/IPs
- **Detailed mode** (`--user`): Per-user breakdown showing:
  - IPs sorted by total plays with last seen timestamps
  - Devices (player/platform/product) sorted by total plays with last seen timestamps

## 📋 Prerequisites

- Python 3.8 or higher
- Poetry (for dependency management)

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/schwaboy/tautulli-snitch.git
   cd tautulli-snitch
   ```

2. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies:
   ```bash
   poetry install --no-root
   ```
   
   > **Note**: This project uses Poetry in dependency-only mode (`package-mode = false` in `pyproject.toml`) since it's a standalone script rather than an installable package.

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Configure your environment variables in `.env`:
   ```env
   TAUTULLI_URL=http://your-tautulli:8181
   TAUTULLI_API_KEY=your_api_key_here
   ```

## 💻 Usage

### Summary Report (All Users)

```bash
# Default: sort by devices (descending)
poetry run python snitch.py

# Sort by name (ascending)
poetry run python snitch.py --sort name

# Sort by unique IPs (descending)  
poetry run python snitch.py --sort ips
```

**Output example:**
```
User                          Devices     Unique IPs
----------------------------------------------------------------------
User1                        15          8
User2                        32         12
```

### Detailed User Report

```bash
# Show detailed stats for specific user
poetry run python snitch.py --user someusername
```

**Output example:**
```
User: Some User (ID: 12345)
  History rows loaded: 847
  IP addresses (by plays):
    - 192.168.1.100  (plays: 245, last_seen: 2025-12-14 10:23:45)
    - 10.0.0.50      (plays: 189, last_seen: 2025-12-13 19:12:33)
  Devices (by plays):
    - PS5 / PlayStation  (plays: 156, last_seen: 2025-12-14 09:45:22)
    - iPhone / iOS       (plays: 89, last_seen: 2025-12-13 22:17:09)
```

### Inactive Users Report

```bash
# Find users who haven't had a play in the last N days
poetry run python snitch.py --inactive 30

# Find users inactive for 90 days
poetry run python snitch.py --inactive 90
```

**Output example:**
```
Found 3 inactive user(s) in the last 30 days:

User                          Last Seen
----------------------------------------------------------------------
User3                         2025-11-01 14:23:45
User4                         2025-10-15 09:12:33
User5                         Never
----------------------------------------------------------------------
```

**Notes:**
- Days must be between 1 and 36500 (100 years)
- Input is validated to ensure it's a positive integer
- Users with "Never" as last_seen have no history in Tautulli

## 🔧 How It Works

### Summary Mode

1. `get_user_names()` → Fetches all users
2. `get_user_player_stats(user_id)` → Gets device types per user
3. `get_user_ips(user_id)` → Gets unique IP addresses per user (paginated)

### Detailed Mode (--user)

1. `get_history(user_id)` → Retrieves raw play history rows
2. Aggregates by IP address and player/platform/product
3. Counts plays per IP/device and tracks last seen timestamps
4. Sorts results by total plays (descending)

## 📊 Data Sources

| Mode | API Call | Purpose |
|------|----------|---------|
| Summary | `get_user_player_stats` | Device type counts |
| Summary | `get_user_ips` | Unique IP addresses |
| Detailed | `get_history(user_id)` | Per-play history with timestamps and IPs |

## 📝 Notes

- **Devices**: Summary mode shows total player stat entries; detailed mode shows unique player/platform/product combinations from history
- **Pagination**: Automatically handles pagination for `get_user_ips` and `get_history` (length=10000)
- **Timestamps**: `last_seen` uses the maximum of date/started/stopped from history rows
- **Plays**: Each history row counts as 1 play (not duration-based)

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| No output | Check `.env` values and verify Tautulli API key permissions |
| 0 users | Verify `get_user_names` works: `http://your-tautulli/api/v2?apikey=KEY&cmd=get_user_names` |
| 25 IP limit | Already fixed by pagination parameters in script |

## 📄 License

MIT License - Use freely for personal Plex/Tautulli monitoring. See [LICENSE](LICENSE) for details.
