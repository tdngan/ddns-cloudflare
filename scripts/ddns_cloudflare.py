import os, sys, requests, json
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
ZONE_ID = os.getenv("ZONE_ID", "")
DOMAIN = os.getenv("DOMAIN", "yourdomain.com")
SUBDOMAINS = os.getenv("SUBDOMAINS", "["bz","rt","owncast","re","nc","home","tor","ptainer","uptime","adguard","npm"]").split(",") if os.getenv("SUBDOMAINS") else ["bz","rt"]

def get_ip():
    try: return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except: pass
    try: return requests.get("https://icanhazip.com", timeout=5).text.strip()  
    except: pass
    return None

def main():
    if not API_TOKEN or not ZONE_ID:
        print("[Error] Edit .env with API_TOKEN and ZONE_ID")
        sys.exit(1)

    ip = get_ip()
    if not ip:
        print("[Error] Could not fetch IP")
        return

    try:
        # Get existing records
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records?type=A", headers=headers, timeout=15)
        existing = {rec["name"]: rec["id"] for rec in r.json().get("result", [])}

        # Build bulk operations
        ops = []
        for sub in SUBDOMAINS:
            host = DOMAIN if not sub or sub == "@" else f"{sub}.{DOMAIN}"
            data = {"type": "A", "name": host, "content": ip, "proxied": False, "comment": "Auto DDNS"}

            if host in existing:
                ops.append({"action": "update", "id": existing[host], "request": data})
                print(f"  [Update] {host}")
            else:
                ops.append({"action": "create", "request": data})
                print(f"  [Create] {host}")

        # Send bulk request
        r = requests.post("https://api.cloudflare.com/client/v4/client/bulk", 
                        headers={"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"},
                        json=ops, timeout=30)

        if r.status_code == 200:
            result = r.json()
            success = len([s for s in result.get("result", []) if s.get("success")])
            print(f"[Done] Updated {success}/{len(ops)} subdomains. IP={ip}")
        else:
            print(f"[Error] API failed with status {r.status_code}: {r.text[:200]}")

    except Exception as e:
        print(f"[Error] {e}")

if __name__ == "__main__":
    main()
