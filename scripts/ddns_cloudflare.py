# ---------------------------------------------------------------
# Cloudflare DDNS (batch version)
# Updates A records for a list of subdomains to the current public
# IP, and creates any record that doesn't exist yet.
# ---------------------------------------------------------------

import os, sys, json, requests          # standard libs + HTTP client
from dotenv import load_dotenv          # reads variables from the .env file

# Load variables from .env into the process environment
load_dotenv()

# ---------- Configuration (read from .env) ----------

# Cloudflare API token (needs Zone -> DNS -> Edit permission)
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
# ID of the zone (found on the domain's Overview page in Cloudflare)
ZONE_ID = os.getenv("ZONE_ID", "")
# Root domain, e.g. example.com (no default, so it can't hit the wrong domain)
DOMAIN = os.getenv("DOMAIN", "")

# Fallback list used when SUBDOMAINS is missing or invalid in .env
DEFAULT_SUBDOMAINS = ["bz", "rt", "owncast", "re", "nc", "home", "tor",
                      "ptainer", "uptime", "adguard", "npm"]

# SUBDOMAINS in .env is a JSON array, e.g. ["bz","rt","nc"]
try:
    # Parse the JSON; if it is empty/missing, use the default list
    SUBDOMAINS = json.loads(os.getenv("SUBDOMAINS", "")) or DEFAULT_SUBDOMAINS
except json.JSONDecodeError as e:
    # Invalid JSON: warn and fall back to the default list
    print(f"[Warning] Bad SUBDOMAINS JSON: {e}. Using default.")
    SUBDOMAINS = DEFAULT_SUBDOMAINS

# Base URL of the DNS records endpoint for this zone
API = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records"
# Maximum number of operations sent per batch request
BATCH_SIZE = 100


# ---------- Step 1: get the current public IP ----------
def get_ip():
    # Try two independent services, in order
    for url in ("https://api.ipify.org", "https://icanhazip.com"):
        try:
            r = requests.get(url, timeout=5)   # ask the service for our IP
            r.raise_for_status()               # raise on HTTP errors (4xx/5xx)
            return r.text.strip()              # return the IP without whitespace
        except Exception as e:
            # This service failed; log it and try the next one
            print(f"[IP] {url} failed: {e}")
    # Both services failed
    return None


# ---------- Step 2: read existing A records ----------
def list_a_records(session):
    """Return {hostname: [records]} for all A records, following pagination."""
    records, page = {}, 1                      # result dict and current page number
    while True:
        # Request one page of A records (max 100 per page)
        r = session.get(API, params={"type": "A", "per_page": 100, "page": page}, timeout=15)
        r.raise_for_status()                   # stop on HTTP errors
        data = r.json()                        # parse the JSON response
        for rec in data.get("result", []):
            # Group records by hostname (a name can have more than one A record)
            records.setdefault(rec["name"], []).append(rec)
        # Stop when we've read the last page
        if page >= data.get("result_info", {}).get("total_pages", 1):
            break
        page += 1                              # otherwise fetch the next page
    return records


# ---------- Step 4: send one batch request ----------
def send_batch(session, patches, posts):
    # One request: "patches" update records, "posts" create records
    r = session.post(f"{API}/batch", json={"patches": patches, "posts": posts}, timeout=30)
    try:
        body = r.json()                        # try to parse the response body
    except ValueError:
        body = {}                              # body was not JSON
    if r.ok and body.get("success"):
        return True, body                      # whole batch was applied
    # Batch failed: return the error details for printing
    errors = body.get("errors") or r.text[:300]
    return False, errors


def main():
    # ---------- Validate configuration ----------
    if not API_TOKEN or not ZONE_ID or not DOMAIN:
        print("[Error] CLOUDFLARE_API_TOKEN, ZONE_ID and DOMAIN must be set in .env")
        sys.exit(1)                            # stop: nothing can work without these

    # ---------- Step 1: current public IP ----------
    ip = get_ip()
    if not ip:
        print("[Error] Could not fetch public IP. Exiting.")
        sys.exit(1)                            # never write an empty/unknown IP to DNS

    # ---------- Prepare an HTTP session ----------
    # A session reuses the connection and sends the same headers every time
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {API_TOKEN}",    # authenticate with the API token
        "Content-Type": "application/json",        # we send JSON bodies
    })

    # ---------- Step 2: list existing A records ----------
    try:
        existing = list_a_records(session)
    except Exception as e:
        print(f"[Error] Could not list DNS records: {e}")
        sys.exit(1)
    print(f"[DNS] Found {sum(len(v) for v in existing.values())} existing A records.")

    # ---------- Step 3: decide what to update and what to create ----------
    patches, posts = [], []                    # operations to update / to create
    for sub in SUBDOMAINS:
        # Build the full hostname ("" or "@" means the root domain itself)
        hostname = DOMAIN if sub in ("", "@") else f"{sub}.{DOMAIN}"
        recs = existing.get(hostname)          # existing records for this name, if any
        if recs:
            for rec in recs:
                if rec["content"] == ip:
                    # IP already correct: skip, no API call needed
                    print(f"  [Same]   {hostname}")
                else:
                    # IP changed: patch only "content" so proxied/ttl stay unchanged
                    patches.append({"id": rec["id"], "content": ip})
                    print(f"  [Update] {hostname} ({rec['content']} -> {ip})")
        else:
            # Record doesn't exist yet: queue a create operation
            posts.append({
                "type": "A",                   # IPv4 record
                "name": hostname,              # full hostname
                "content": ip,                 # current public IP
                "ttl": 1,                      # 1 = automatic TTL
                "proxied": False,              # DNS only (grey cloud)
                "comment": "Auto DDNS",        # note shown in the Cloudflare dashboard
            })
            print(f"  [Create] {hostname}")

    # Nothing to do: avoid a pointless API call
    if not patches and not posts:
        print("[Done] Nothing to change.")
        return

    # ---------- Step 4: send the operations in batches ----------
    # Tag each operation with its type so it can be split into chunks
    ops = [("patch", p) for p in patches] + [("post", p) for p in posts]
    failed = 0                                 # count of operations that were not applied
    for i in range(0, len(ops), BATCH_SIZE):
        chunk = ops[i:i + BATCH_SIZE]          # take up to BATCH_SIZE operations
        # Split the chunk back into updates and creates
        chunk_patches = [o for t, o in chunk if t == "patch"]
        chunk_posts = [o for t, o in chunk if t == "post"]
        # Send this chunk as a single batch request
        ok, info = send_batch(session, chunk_patches, chunk_posts)
        if ok:
            print(f"[Batch] OK: {len(chunk_patches)} updated, {len(chunk_posts)} created")
        else:
            # A failed batch is rolled back entirely by Cloudflare
            failed += len(chunk)
            print(f"[Batch] FAILED ({len(chunk)} operations): {info}")

    # ---------- Step 5: summary ----------
    print(f"[Done] IP={ip}, {len(ops) - failed}/{len(ops)} operations applied.")
    if failed:
        sys.exit(1)                            # non-zero exit code so cron/monitoring notices


# Run main() only when the file is executed directly (not when imported)
if __name__ == "__main__":
    main()