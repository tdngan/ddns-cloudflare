# 🌐 Cloudflare DDNS - Auto Update DNS (CRON LINH HOẠT!)

## Mục đích ⚡

Tự động cập nhật **11 subdomains** trên [Cloudflare](https://www.cloudflare.com/) mỗi khi IP thay đổi. Chỉ dùng 1 API call bulk update!

### Subdomains:
```
bz.yourdomain.com   - Backup server  
rt.yourdomain.com   - Reverse tunnel
owncast.yourdomain.com   - Owncast streaming
re.yourdomain.com   - Remote access
nc.yourdomain.com   - Nextcloud
home.yourdomain.com   - Home page
tor.yourdomain.com   - Tor service
ptainer.yourdomain.com   - Portainer
uptime.yourdomain.com   - Uptime monitoring
adguard.yourdomain.com   - AdGuard DNS
npm.yourdomain.com   - NPM registry
```

## 🚀 Quick Start (10 phút)

### 1. Setup local environment
```bash
cd E:/Nextcloud/MyData/Apps/ddns-cloudflare
mkdir -p data/logs data/cache
cp .env.example .env
nano .env  # Điền CLOUDFLARE_API_TOKEN, ZONE_ID, DOMAIN
```

### 2. Build Docker image
```bash
docker build -t cloudflare-ddns .
```

### 3. Chạy container
```bash
docker compose up -d

# Xem log (cron chạy mỗi 5 phút mặc định)
docker logs -f cloudflare-ddns | grep "IP"
```

## ⭐ Thay đổi tần suất cron (LINH HOẠT!)

**Chỉ cần sửa .env file:**

```ini
CRON_EXPR="*/10 * * * *"    # Mỗi 10 phút thay vì 5 phút
# Các giá trị phổ biến:
#   */5 * * * *      → Mỗi 5 phút (mặc định)
#   */10 * * * *     → Mỗi 10 phút  
#   0 * * * *        → Mỗi giờ
#   0 */2 * * *      → Mỗi 2 giờ
```

**Sau đó restart container:**
```bash
docker compose restart ddns-cloudflare
```

## 📋 Cấu hình .env cần thiết

### 🔴 BẮT BUỘC:
| Biến | Ví dụ | Nơi lấy thông tin |
|------|-------|-------------------|
| `CLOUDFLARE_API_TOKEN` | token từ [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens) | Template: "Edit zone DNS" |
| `ZONE_ID` | Zone ID của domain bạn | Cloudflare Dashboard → Domain → Overview |  
| `DOMAIN` | example.com | Tên domain chính |

### 🟢 TUÝ CHỌN:
| Biến | Ví dụ | Mô tả |
|------|-------|-------|
| `SUBDOMAINS` | JSON array với danh sách subdomains | Thêm/xóa subdomain cần update (default đã có 11 domains) |
| `CRON_EXPR` | `"*/10 * * * *"` | Tần suất cron - thay đổi mà không cần rebuild! ⭐ |

## 🔄 GitHub Actions Auto-Deploy

### Setup Secrets trong GitHub:
1. Vào repository → Settings → Secrets and variables → Actions
2. Thêm 3 secrets:

| Name | Value |
|------|-------|
| `GITHUB_TOKEN` | Personal Access Token với scope `write:packages` (tạo từ [Settings → Tokens](https://github.com/settings/tokens)) |
| `DOCKER_USERNAME` | `tdngan` |
| `DOCKER_PASSWORD` | (không cần nếu chỉ dùng ghcr.io) |

### Push code lên main branch:
```bash
git add .
git commit -m "Update configuration"  
git push origin main  # ← Tự động build & push lên GHCR!
```

Image sẽ được push lên:
```
ghcr.io/tdngan/ddns-cloudflare:latest        ✅ Latest tag
ghcr.io/tdngan/ddns-cloudflare:a1b2c3d...    ✅ Commit SHA tag
```

## 🔍 Kiểm tra hoạt động

```bash
# Xem cron job logs
cat data/logs/ddns_cron.log | tail -n 20

# Check IP đã lưu
cat data/cache/ddns_last_ip.cache

# Xem container logs
docker logs cloudflare-ddns
```

## 💡 Cron Expression Format

| Expression    | Mô tả | Khi nào chạy? |
|---------------|-------|---------------|
| `*/5 * * * *`      | Mỗi 5 phút (default) | Phút: 0, 5, 10, 15... |
| `*/10 * * * *`     | Mỗi 10 phút | Phút: 0, 10, 20, 30... |
| `0 * * * *`        | Mỗi giờ (phút 0) | 00:00, 01:00, 02:00... |

## 🛠️ Troubleshooting

### Cron không chạy?
```bash
# Kiểm tra cron config trong container
docker exec cloudflare-ddns cat /etc/crontabs/ddns-cron.conf

# Xem cron daemon có chạy không
docker exec cloudflare-ddns ps aux | grep "[c]ron"
```

### Docker build lỗi?
```bash
# Rebuild từ đầu
docker compose down
rm -rf .docker .gitignore
docker build --no-cache -t cloudflare-ddns .
```

---

**Giấy phép:** MIT | **Cập nhật:** 2026-11-24 (CRON_EXPR linh hoạt!)
