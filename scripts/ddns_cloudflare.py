import os, sys, requests
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
ZONE_ID = os.getenv("ZONE_ID", "").strip()  
DOMAIN = os.getenv("DOMAIN", "yourdomain.com").strip().lower()

SUBDOMAINS = ["bz","rt","owncast","re","nc","home","tor","ptainer","uptime","adguard","npm"]

def get_ip():
    for url in ["https://api.ipify.org", "https://icanhazip.com"]:
        try:
            r = requests.get(url, timeout=5)
            return r.text.strip()
        except: continue
    return None

def main():
    if not API_TOKEN or not ZONE_ID:
        print("[Error] Edit .env with CLOUDFLARE_API_TOKEN and ZONE_ID")
        sys.exit(1)
    
    ip = get_ip()
    if not ip:
        print("[Error] Could not fetch IP")
        return
    
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records?type=A", 
                        headers=headers, timeout=15)
        
        if r.status_code == 401 or r.status_code == 403:
            print("[Error] Invalid API token. Check permissions.")
            return
        elif r.status_code == 404:
            print("[Error] Zone not found. Verify ZONE_ID is correct.")
            return
        
        existing = {rec["name"].rstrip('.').lower(): rec["id"] for rec in r.json().get("result", [])}
        
        ops = []
        for sub in SUBDOMAINS:
            hostname = DOMAIN if not sub or sub == "@" else f"{sub}.{DOMAIN}"
            data = {"type": "A", "name": hostname, "content": ip, "proxied": False, "comment": "Auto DDNS"}
            
            if hostname.lower() in existing:
                ops.append({"action": "update", "id": existing[hostname.lower()], "request": data})
                print(f"  [Update] {hostname}")
            else:
                ops.append({"action": "create", "request": data})
                print(f"  [Create] {hostname} (new)")
        
        r = requests.post("https://api.cloudflare.com/client/v4/client/bulk", 
                        headers={"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"},
                        json=ops, timeout=30)
        
        if r.status_code == 200:
            result = r.json()
            success = len([s for s in result.get("result", []) if s.get("success")])
            print(f"[Done] Updated {success}/{len(ops)} subdomains. IP={ip}")
        else:
            print(f"[Error] API failed (status {r.status_code})")
            
    except Exception as e:
        print(f"[Error] {e}")

if __name__ == "__main__":
    main()
