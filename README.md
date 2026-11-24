# 🌐 Cloudflare DDNS - Auto Update DNS Records

## Mục đích

Script tự động cập nhật **TẤT CẢ subdomains** của bạn trên [Cloudflare](https://www.cloudflare.com/) mỗi khi IP công cộng thay đổi. Đặc biệt: chỉ gọi 1 API bulk update duy nhất, không spam API.

## 🚀 Quick Start

### 1. Clone & Setup
```bash
cd E:/Nextcloud/MyData/Apps/ddns-cloudflare
cp .env.example .env
nano .env  # Điền thông tin bên dưới
mkdir -p data/logs data/cache
```

### 2. Build Docker Image
```bash
docker build -t cloudflare-ddns .
```

### 3. Chạy container
```bash
docker compose up -d
```

### 4. Xem log
```bash
docker compose logs -f ddns-cloudflare
```
