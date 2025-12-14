import os
import argparse
import requests
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime
from typing import Any, Dict, List, Optional

# Load environment variables from .env
load_dotenv()

TAUTULLI_URL = os.getenv("TAUTULLI_URL")
API_KEY = os.getenv("TAUTULLI_API_KEY")


def call_tautulli(cmd: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if params is None:
        params = {}

    if not TAUTULLI_URL or not API_KEY:
        raise RuntimeError(
            "TAUTULLI_URL or TAUTULLI_API_KEY not set in environment"
        )

    base_params = {"apikey": API_KEY, "cmd": cmd}
    base_params.update(params)

    resp = requests.get(f"{TAUTULLI_URL}/api/v2", params=base_params, timeout=30)
    resp.raise_for_status()

    payload = resp.json()
    response = payload.get("response", {})
    if response.get("result") != "success":
        error_msg = response.get("message", "Unknown error")
        raise RuntimeError(f"Tautulli API error for command '{cmd}': {error_msg}")

    return response


def get_users() -> List[Dict[str, Any]]:
    resp = call_tautulli("get_user_names")
    data = resp.get("data")
    return data if isinstance(data, list) else []


def get_user_player_stats(user_id: int) -> List[Dict[str, Any]]:
    resp = call_tautulli("get_user_player_stats", {"user_id": user_id})
    data = resp.get("data")
    if isinstance(data, dict) and "players" in data:
        players = data.get("players") or []
        return players
    if isinstance(data, list):
        return data
    return []


def get_user_ips(user_id: int) -> List[Dict[str, Any]]:
    # get_user_ips for summary mode (per-user IP table)[file:1]
    resp = call_tautulli(
        "get_user_ips",
        {
            "user_id": user_id,
            "start": 0,
            "length": 10000,
        },
    )
    outer_data = resp.get("data")
    if isinstance(outer_data, dict):
        inner = outer_data.get("data")
        return inner if isinstance(inner, list) else []
    if isinstance(outer_data, list):
        return outer_data
    return []


def device_label_from_entry(entry: Dict[str, Any]) -> str:
    fields = [
        entry.get("player"),
        entry.get("product"),
        entry.get("platform"),
        entry.get("device"),
    ]
    parts = [f for f in fields if f]
    return " / ".join(parts) or "Unknown device"


def build_summary_results() -> List[Dict[str, Any]]:
    """Summary mode: per-user devices + unique IPs using player stats and user IP table."""
    users = get_users()
    print(f"Found {len(users)} users")

    user_devices = defaultdict(list)
    user_ips = defaultdict(set)

    for user in users:
        user_id = user.get("user_id")
        name = user.get("friendly_name") or user.get("username") or f"User {user_id}"
        key = (user_id, name)

        # Devices
        try:
            player_rows = get_user_player_stats(user_id)
        except Exception as e:
            print(f"[ERROR] Devices for {name} ({user_id}): {e}")
            player_rows = []

        for entry in player_rows:
            user_devices[key].append(device_label_from_entry(entry))

        # IPs
        try:
            ip_rows = get_user_ips(user_id)
        except Exception as e:
            print(f"[ERROR] IPs for {name} ({user_id}): {e}")
            ip_rows = []

        for row in ip_rows:
            ip = row.get("ip_address")
            if ip:
                user_ips[key].add(ip)

    results = []
    for (user_id, name), devices in user_devices.items():
        ips = user_ips.get((user_id, name), set())
        results.append(
            {
                "user_id": user_id,
                "name": name,
                "device_entries": len(devices),
                "unique_ips": len(ips),
            }
        )

    return results


def get_user_history_rows(user_id: int, max_rows: int = 100000) -> List[Dict[str, Any]]:
    """
    Use get_history filtered by user_id to retrieve that user's play history.
    This is the same data the web UI shows on the user's History tab.[file:1][web:21]
    """
    resp = call_tautulli(
        "get_history",
        {
            "user_id": user_id,
            "start": 0,
            "length": max_rows,
            "grouping": 0,  # ensure individual rows
        },
    )
    outer = resp.get("data")
    if isinstance(outer, dict):
        rows = outer.get("data")
        return rows if isinstance(rows, list) else []
    if isinstance(outer, list):
        return outer
    return []


def get_user_last_activity(user_id: int) -> int:
    """
    Get the timestamp of a user's most recent play.
    Returns 0 if no history found.
    """
    try:
        rows = get_user_history_rows(user_id, max_rows=1)
        if rows and len(rows) > 0:
            row = rows[0]
            ts = row.get("date") or row.get("started") or row.get("stopped") or 0
            return int(ts) if ts else 0
    except Exception:
        pass
    return 0


def fmt_ts(ts: Any) -> str:
    if not ts:
        return "unknown"
    try:
        return datetime.fromtimestamp(int(ts)).isoformat(sep=" ", timespec="seconds")
    except (OSError, OverflowError, ValueError, TypeError):
        return str(ts)


def validate_days_input(days: str) -> int:
    """
    Validate and sanitize days input.
    Must be a positive integer between 1 and 36500 (100 years).
    """
    try:
        days_int = int(days)
    except (ValueError, TypeError):
        raise ValueError("Days must be an integer")
    
    if days_int < 1:
        raise ValueError("Days must be at least 1")
    
    if days_int > 36500:
        raise ValueError("Days must be 36500 or less")
    
    return days_int


def build_inactive_users(days: int) -> List[Dict[str, Any]]:
    """
    Find users who haven't had any plays in the last N days.
    """
    now = datetime.now().timestamp()
    cutoff_timestamp = now - (days * 86400)  # 86400 seconds in a day
    
    users = get_users()
    print(f"Checking {len(users)} users for inactivity in the last {days} days...")
    
    inactive = []
    for user in users:
        user_id = user.get("user_id")
        name = user.get("friendly_name") or user.get("username") or f"User {user_id}"
        
        try:
            last_activity = get_user_last_activity(user_id)
            if last_activity == 0 or last_activity < cutoff_timestamp:
                last_seen = fmt_ts(last_activity) if last_activity > 0 else "Never"
                inactive.append({
                    "user_id": user_id,
                    "name": name,
                    "last_activity": last_activity,
                    "last_seen": last_seen,
                })
        except Exception as e:
            print(f"[WARNING] Could not get activity for {name} ({user_id}): {e}")
    
    return inactive


def build_user_detail(user_filter: str) -> List[Dict[str, Any]]:
    """
    Detailed mode for a specific user:
    - Uses get_history(user_id=...) to derive per-IP and per-device stats.[file:1][web:21]
    """
    # Validate user input
    if not user_filter or not isinstance(user_filter, str):
        raise ValueError("User filter must be a non-empty string")
    
    if len(user_filter) > 255:
        raise ValueError("User filter must be 255 characters or less")
    
    users = get_users()

    # Match users by friendly_name/username substring
    target = user_filter.lower()
    matches = []
    for u in users:
        name = u.get("friendly_name") or u.get("username") or f"User {u.get('user_id')}"
        if target in name.lower():
            matches.append(
                {
                    "user_id": u.get("user_id"),
                    "name": name,
                }
            )

    return matches


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tautulli user devices and IPs report"
    )
    parser.add_argument(
        "--sort",
        choices=["name", "devices", "ips"],
        default="devices",
        help="Sort by user name, number of devices, or number of IPs (default: devices)",
    )
    parser.add_argument(
        "--user",
        help=(
            "Show detailed devices and IPs for a specific user name "
            "(matches friendly_name or username, case-insensitive)"
        ),
    )
    parser.add_argument(
        "--inactive",
        type=str,
        help="List users who haven't had a play in the last N days (1-36500)",
    )
    args = parser.parse_args()

    if args.inactive:
        # Inactive users: find users with no activity in the last N days
        try:
            days = validate_days_input(args.inactive)
        except ValueError as e:
            print(f"[ERROR] Invalid days input: {e}")
            return
        
        inactive_users = build_inactive_users(days)
        if not inactive_users:
            print(f"No inactive users found in the last {days} days.")
            return
        
        # Sort by last activity (oldest first)
        inactive_users.sort(key=lambda x: x["last_activity"])
        
        print(f"\nFound {len(inactive_users)} inactive user(s) in the last {days} days:")
        print(f"\n{'User':30} {'Last Seen':35}")
        print("-" * 70)
        for user in inactive_users:
            print(
                f"{user['name'][:28]:30} {user['last_seen']:35}"
            )
        print("-" * 70)

    elif args.user:
        # Detailed: per-IP and per-device stats via get_history
        user_matches = build_user_detail(args.user)
        print(f"Found {len(user_matches)} user(s) matching {args.user!r}")

        if not user_matches:
            print("No users matched that filter.")
            return

        for um in user_matches:
            user_id = um["user_id"]
            name = um["name"]
            print(f"\nUser: {name} (ID: {user_id})")

            # Aggregation structures
            ip_stats = defaultdict(lambda: {"plays": 0, "last_seen": 0})
            dev_stats = defaultdict(lambda: {"plays": 0, "last_seen": 0})

            try:
                rows = get_user_history_rows(user_id)
            except Exception as e:
                print(f"[ERROR] get_history for {name} ({user_id}): {e}")
                continue

            print(f"  History rows loaded: {len(rows)}")

            for row in rows:
                # Each row is a play; use 'date' as primary timestamp, fallback to started/stopped.[file:1][web:21]
                ts = row.get("date") or row.get("started") or row.get("stopped") or 0
                try:
                    ts_int = int(ts)
                except (TypeError, ValueError):
                    ts_int = 0

                # IP aggregation
                ip = row.get("ip_address")
                if ip:
                    s = ip_stats[ip]
                    s["plays"] += 1
                    s["last_seen"] = max(s["last_seen"], ts_int)

                # Device aggregation: use player as individual device name; include platform/product for clarity.[file:1][web:21]
                player = row.get("player") or "Unknown player"
                platform = row.get("platform") or ""
                product = row.get("product") or ""
                label_parts = [player]
                if platform:
                    label_parts.append(platform)
                if product:
                    label_parts.append(product)
                dev_label = " / ".join(label_parts)

                d = dev_stats[dev_label]
                d["plays"] += 1
                d["last_seen"] = max(d["last_seen"], ts_int)

            # IP output, sorted by plays desc, then last_seen desc, then IP
            if ip_stats:
                print("  IP addresses (by plays):")
                for ip, stats in sorted(
                    ip_stats.items(),
                    key=lambda kv: (-kv[1]["plays"], -kv[1]["last_seen"], kv[0]),
                ):
                    print(
                        f"    - {ip}  "
                        f"(plays: {stats['plays']}, last_seen: {fmt_ts(stats['last_seen'])})"
                    )
            else:
                print("  IP addresses: none recorded")

            # Device output, sorted by plays desc, then last_seen desc, then label
            if dev_stats:
                print("  Devices (by plays):")
                for label, stats in sorted(
                    dev_stats.items(),
                    key=lambda kv: (-kv[1]["plays"], -kv[1]["last_seen"], kv[0]),
                ):
                    print(
                        f"    - {label}  "
                        f"(plays: {stats['plays']}, last_seen: {fmt_ts(stats['last_seen'])})"
                    )
            else:
                print("  Devices: none recorded")

            print("-" * 80)

    else:
        # Summary mode: per-user devices + unique IPs
        results = build_summary_results()
        if not results:
            print("No results to display (0 users or all calls failed).")
            return

        if args.sort == "name":
            results.sort(key=lambda x: x["name"].lower())
        elif args.sort == "devices":
            results.sort(key=lambda x: (-x["device_entries"], x["name"].lower()))
        elif args.sort == "ips":
            results.sort(key=lambda x: (-x["unique_ips"], x["name"].lower()))

        print(f"\n{'User':30} {'Devices':10} {'Unique IPs':12}")
        print("-" * 70)
        for row in results:
            print(
                f"{row['name'][:28]:30} "
                f"{row['device_entries']:10d} "
                f"{row['unique_ips']:12d}"
            )


if __name__ == "__main__":
    main()

