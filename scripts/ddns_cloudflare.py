import os, sys, requests, json
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
ZONE_ID = os.getenv("ZONE_ID", "")
DOMAIN = os.getenv("DOMAIN", "yourdomain.com")

# Correct way to handle SUBDOMAINS JSON array
subdomains_env = os.getenv("SUBDOMAINS")
if subdomains_env:
    try:
        SUBDOMAINS = json.loads(subdomains_env)
        print(f"[Config] Loaded {len(SUBDOMAINS)} subdomains from .env")
    except json.JSONDecodeError as e:
        print(f"[Warning] JSON parse error in SUBDOMAINS: {e}. Using default.")
        SUBDOMAINS = ["bz", "rt", "owncast", "re", "nc", "home", "tor", "ptainer", "uptime", "adguard", "npm"]
else:
    SUBDOMAINS = ["bz", "rt", "owncast", "re", "nc", "home", "tor", "ptainer", "uptime", "adguard", "npm"]

def get_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception as e:
        print(f"[IP] Failed to fetch IP from api.ipify.org: {e}")
        try:
            return requests.get("https://icanhazip.com", timeout=5).text.strip()
        except Exception as e2:
            print(f"[IP] All services failed. Using local IP.")
            # Fallback to localhost (will use public API instead)
            return None

def main():
    if not API_TOKEN or not ZONE_ID:
        print("[Error] Missing CLOUDFLARE_API_TOKEN and/or ZONE_ID in .env file")
        print("Please edit .env.example -> .env and add these values")
        sys.exit(1)

    ip = get_ip()
    if not ip:
        print("[Error] Could not fetch public IP. Exiting.")
        return

    try:
        # Get existing A records from Cloudflare
        headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
        r = requests.get(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
            params={"type": "A", "per_page": 100},
            headers=headers,
            timeout=15
        )

        if r.status_code != 200:
            print(f"[DNS] Error fetching records: {r.status_code}")
            return

        data = r.json()
        existing_records = {}

        for record in data.get("result", []):
            name = record.get("name")
            record_id = record.get("id")
            if name and record_id:
                existing_records[name] = record_id

        print(f"[DNS] Found {len(existing_records)} existing A records.")

        # Build bulk operations for all subdomains
        ops = []
        for sub in SUBDOMAINS:
            hostname = DOMAIN if not sub or sub == "@" else f"{sub}.{DOMAIN}"

            record_data = {
                "type": "A",
                "name": hostname,
                "content": ip,
                "proxied": False,
                "comment": "Auto DDNS"
            }

            if hostname in existing_records:
                ops.append({
                    "action": "update",
                    "id": existing_records[hostname],
                    "request": record_data
                })
                print(f"  [Update] {hostname}")
            else:
                ops.append({
                    "action": "create",
                    "request": record_data
                })
                print(f"  [Create] {hostname}")

        if not ops:
            print("[DNS] No operations to perform.")
            return

        # Send bulk update request
        r = requests.post(
            "https://api.cloudflare.com/client/v4/client/bulk",
            headers={
                "Authorization": f"Bearer {API_TOKEN}", 
                "Content-Type": "application/json"
            },
            json=ops,
            timeout=30
        )

        if r.status_code == 200:
            result = r.json()

            # Count successful updates/creations
            successes = 0
            failed_ops = []

            for item in result.get("result", []):
                if item.get("success"):
                    hostname = item.get("request", {}).get("name", "unknown")
                    print(f"    ✓ {hostname}")
                    successes += 1
                else:
                    error_msg = item.get("error", {}).get("message", "Unknown error")
                    failed_ops.append(f"    ✗ {item.get('request', {}).get('name', 'unknown')}: {error_msg}")

            print()
            if failed_ops:
                print("[DNS] Some operations failed:")
                for msg in failed_ops[:5]:  # Show first 5 errors
                    print(msg)
                if len(failed_ops) > 5:
                    print(f"... and {len(failed_ops)-5} more")

            print(f"[Done] Successfully updated {successes}/{len(ops)} subdomains. IP={ip}")
        else:
            print(f"[Error] Bulk update failed with status code {r.status_code}: {r.text[:300]}")

    except Exception as e:
        print(f"[Error] Unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
