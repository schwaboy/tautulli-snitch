Tautulli User Devices & IPs Reporter

A Python script to analyze Tautulli users by unique devices and IP addresses, matching the web UI's user history table.
Features

    Summary mode: List all users with device counts and unique IP counts, sortable by name/devices/IPs

    Detailed mode (--user): Per-user breakdown from get_history showing:

        IPs sorted by total plays with last seen timestamps

        Devices (player/platform/product) sorted by total plays with last seen timestamps

Installation

Prerequisites:
- Python 3.8 or higher
- Poetry (for dependency management)

Steps:

1. Clone the repository and navigate to the project directory

2. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. Install dependencies:
   ```bash
   poetry install
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Configure your environment variables in `.env`:
   ```text
   TAUTULLI_URL=http://your-tautulli:8181
   TAUTULLI_API_KEY=your_api_key_here
   ```

Usage
Summary Reports (all users)

```bash
# Default: sort by devices (descending)
poetry run python tautulli.py

# Sort by name (ascending)
poetry run python tautulli.py --sort name

# Sort by unique IPs (descending)  
poetry run python tautulli.py --sort ips
```

Output format:

text
User                          Devices     Unique IPs
----------------------------------------------------------------------
User1                        15          8
User2                        32         12
...

Detailed User Report

```bash
# Show detailed stats for specific user
poetry run python tautulli.py --user someusername
```

Output format:

text
User: Some User (ID: 12345)
  History rows loaded: 847
  IP addresses (by plays):
    - 192.168.1.100  (plays: 245, last_seen: 2025-12-14 10:23:45)
    - 10.0.0.50      (plays: 189, last_seen: 2025-12-13 19:12:33)
  Devices (by plays):
    - PS5 / PlayStation  (plays: 156, last_seen: 2025-12-14 09:45:22)
    - iPhone / iOS       (plays: 89, last_seen: 2025-12-13 22:17:09)
----------------------------------------------------------------------

How It Works
Summary Mode

    get_user_names() → all users

    get_user_player_stats(user_id) → device types per user

    get_user_ips(user_id) → unique IPs per user (paginated)

Detailed Mode (--user)

    get_history(user_id) → raw play history rows

    Aggregates by ip_address and player/platform/product

    Counts plays per IP/device, tracks max date/started/stopped as last seen

    Sorts by total plays (descending)

Data Sources
Mode	API Call	Purpose
Summary	get_user_player_stats	Device type counts
Summary	get_user_ips	Unique IP addresses
Detailed	get_history(user_id)	Per-play history w/ timestamps, IPs, players
Notes

    Devices: Summary shows total player stat entries; detailed mode shows unique player/platform/product combinations from history

    Pagination: Handles get_user_ips and get_history pagination automatically (length=10000)

    Timestamps: last_seen uses max of date, started, stopped from history rows

    Plays: Each history row = 1 play (not duration-based)

Troubleshooting

    No output: Check .env values and Tautulli API key permissions

    0 users: Verify get_user_names works in browser: http://your-tautulli/api/v2?apikey=KEY&cmd=get_user_names

    25 IP limit: Fixed by pagination parameters in script

License

MIT License - use freely for personal Plex/Tautulli monitoring.
