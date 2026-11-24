import os
import sys
from dotenv import load_dotenv
import requests
import json
import socket
from typing import Optional


# Load environment variables from .env file
load_dotenv()

# ===================================================
# Cấu hình Cloudflare (từ .env)
# ===================================================
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
ZONE_ID = os.getenv("ZONE_ID", "")
DOMAIN = os.getenv("DOMAIN", "yourdomain.com")
PROXIED = os.getenv("PROXIED", "false").lower() == "true"

# Đọc SUBDOMAINS từ .env (nếu có) hoặc dùng default
subdomains_env = os.getenv("SUBDOMAINS")
if subdomains_env:
    try:
        # Parse JSON array from string
        SUBDOMAINS = list(set(json.loads(subdomains_env)))
        print(f"[Config] Đã load {len(SUBDOMAINS)} subdomains từ .env")
    except json.JSONDecodeError as e:
        print(f"[Warning] Lỗi parse JSON trong SUBDOMAINS: {e}. Dùng default.")
else:
    # Default subdomains (hardcode)
    SUBDOMAINS = list(set([
        "bz",
        "rt",
        "owncast",
        "re",
        "nc",
        "home",
        "tor",
        "ptainer",
        "uptime",
        "adguard",
        "npm"
    ]))

API_BASE = "https://api.cloudflare.com/client/v4"

# ===================================================
# Cấu hình Discord (từ .env)
# ===================================================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ===================================================
# Cấu hình Telegram (từ .env)
# ===================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ===================================================
# File lưu IP đã cập nhật lần cuối
# ===================================================
CACHE_FILE = "ddns_last_ip.cache"


def load_cached_ip() -> Optional[str]:
    """Đọc IP đã cập nhật lần cuối từ file cache."""
    try:
        with open(CACHE_FILE, "r") as f:
            ip = f.read().strip()
            print(f"[Cache] IP lần trước: {ip}")
            return ip if ip else None
    except FileNotFoundError:
        print("[Cache] Chưa có cache.")
        return None
    except IOError as e:
        print(f"[Cache] Lỗi đọc cache: {e}")
        return None


def save_cached_ip(ip: str) -> None:
    """Lưu IP vừa cập nhật vào file cache."""
    try:
        with open(CACHE_FILE, "w") as f:
            f.write(ip)
        print(f"[Cache] Đã lưu IP: {ip}")
    except IOError as e:
        print(f"[Cache] Lỗi lưu cache: {e}")


def get_public_ip() -> Optional[str]:
    """Lấy IP công cộng, thử nhiều service dự phòng."""
    for url in ["https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"]:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            ip = response.text.strip()
            print(f"[IP] IP công cộng: {ip}")
            return ip
        except requests.RequestException:
            continue
    print("[IP] Không lấy được IP công cộng từ tất cả service.")
    return None


def get_local_ip() -> Optional[str]:
    """Lấy IP nội bộ (dự phòng)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
        s.close()
        print(f"[IP] IP nội bộ: {ip}")
        return ip
    except socket.error as e:
        print(f"[IP] Lỗi lấy IP nội bộ: {e}")
        return None


def get_existing_records() -> dict:
    """
    Lấy danh sách tất cả bản ghi A hiện có trên Cloudflare.
    Trả về dict: {hostname: record_id}
    """
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    url = f"{API_BASE}/zones/{ZONE_ID}/dns_records?type=A&per_page=100"
    print(f"[DNS] Đang lấy danh sách bản ghi A hiện có...")

    all_records = {}
    cursor = ""
    page = 1

    while True:
        params = {"type": "A", "per_page": 100}
        if cursor:
            params["cursor"] = cursor

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            for record in data.get("result", []):
                name = record["name"]
                all_records[name] = record["id"]

            info = data.get("result_info", {})
            if not info.get("total_pages", 1) or page >= info.get("total_pages", 1):
                break
            cursor = ""
            page += 1

        except requests.RequestException as e:
            print(f"[DNS] Lỗi lấy danh sách bản ghi: {e}")
            return all_records

    print(f"[DNS] Tìm thấy {len(all_records)} bản ghi A.")
    return all_records


def bulk_update_dns(ip: str) -> bool:
    """
    Cập nhật TẤT CẢ subdomain bằng Cloudflare Bulk API.
    Tự động tạo mới nếu chưa tồn tại, cập nhật nếu đã có.
    Trả về True nếu thành công.
    """
    # 1. Lấy danh sách bản ghi hiện có
    existing = get_existing_records()

    # 2. Xây dựng batch operations
    operations = []
    for sub in SUBDOMAINS:
        if sub == "" or sub == "@":
            hostname = DOMAIN
        else:
            hostname = f"{sub}.{DOMAIN}"

        record_data = {
            "type": "A",
            "name": hostname,
            "content": ip,
            "proxied": PROXIED,
            "comment": "Auto DDNS"
        }

        if hostname in existing
