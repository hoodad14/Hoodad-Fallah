# راهنمای Elasticsearch در ArenaPass

این قابلیت بخش Backend فاز چهارم داک پروژه را پوشش می‌دهد. فقط API عمومی جستجوی بلیط (`GET /api/v1/tickets`) در حالت فعال از Elasticsearch استفاده می‌کند؛ PostgreSQL همچنان **منبع حقیقت** است و تمام رزرو، موجودی، پرداخت و عملیات پشتیبان فقط در PostgreSQL انجام می‌شوند.

## دو حالت اجرا

### حالت سبک: PostgreSQL + Redis

در `.env` مقدار زیر را نگه دارید:

```env
ELASTICSEARCH_ENABLED=false
```

سپس اجرا کنید:

```bash
docker compose up --build -d
```

در این حالت جستجو با SQL پارامتری و ایندکس‌های PostgreSQL انجام می‌شود.

### حالت کامل فاز چهارم: Elasticsearch

در `.env` قرار دهید:

```env
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_FALLBACK_TO_SQL=true
ELASTICSEARCH_SYNC_ON_STARTUP=true
```

برای اولین اجرای این نسخه یا پس از تغییر فایل‌های SQL:

```bash
docker compose --profile search down -v
docker compose --profile search up --build -d
```

وضعیت سرویس‌ها:

```bash
docker compose --profile search ps
docker compose --profile search logs -f elasticsearch backend worker
```

بررسی آمادگی:

```bash
curl http://127.0.0.1:8000/api/v1/ready
```

در پاسخ، این موارد باید `true` باشند:

```json
{
  "elasticsearch": true,
  "elasticsearch_index_ready": true,
  "elasticsearch_enabled": true
}
```

## همگام‌سازی ایمن داده‌ها

معماری همگام‌سازی از سه لایه تشکیل شده است:

1. Triggerهای PostgreSQL هر تغییر مؤثر بر کاتالوگ بلیط را در جدول `search_sync_outbox` ثبت می‌کنند.
2. `worker.py` رکوردهای Outbox را با `FOR UPDATE SKIP LOCKED` Claim می‌کند و سند جاری بلیط را از View رسمی `v_ticket_catalog` در Elasticsearch Upsert/Delete می‌کند.
3. Full Reconciliation دوره‌ای، یک Concrete Index جدید می‌سازد و Alias عمومی را به‌صورت اتمیک جابه‌جا می‌کند. Advisory Lock پایگاه داده از اجرای هم‌زمان و ناسازگار چند Rebuild جلوگیری می‌کند.

Outbox دارای Revision، Retry با Exponential Backoff، قفل منقضی‌شونده و ثبت آخرین خطاست. بنابراین قطع موقت Elasticsearch باعث Rollbackشدن تراکنش اصلی PostgreSQL نمی‌شود و تغییر بعداً دوباره پردازش خواهد شد.

## فرمان‌های مدیریتی

Full Rebuild دستی:

```bash
docker compose --profile search exec backend python sync_search_index.py --full
```

فقط پردازش Outboxهای Pending:

```bash
docker compose --profile search exec worker python sync_search_index.py --outbox-only
```

اجرای بدون Docker:

```bash
python sync_search_index.py --full
python sync_search_index.py --outbox-only
```

## رفتار هنگام اختلال

با تنظیم زیر:

```env
ELASTICSEARCH_FALLBACK_TO_SQL=true
```

اگر Elasticsearch هنگام یک درخواست جستجو از دسترس خارج شود، API همان درخواست را با PostgreSQL اجرا می‌کند. اگر مقدار `false` باشد، پاسخ استاندارد `503 search_unavailable` برمی‌گردد. Readiness در حالت فعال تا زمانی که هم سرویس و هم Alias جستجو آماده نباشند، وضعیت آماده اعلام نمی‌کند.

## تنظیمات مهم

```env
ELASTICSEARCH_URL=http://127.0.0.1:9200
ELASTICSEARCH_INDEX=arenapass_tickets
ELASTICSEARCH_TIMEOUT_SECONDS=8
ELASTICSEARCH_SYNC_BATCH_SIZE=500
ELASTICSEARCH_OUTBOX_BATCH_SIZE=100
ELASTICSEARCH_FULL_SYNC_SECONDS=3600
ELASTICSEARCH_OUTBOX_RETENTION_DAYS=7
```

برای سرویس مدیریت‌شده می‌توان دقیقاً یکی از این دو روش احراز هویت را تنظیم کرد:

```env
ELASTICSEARCH_API_KEY=...
```

یا:

```env
ELASTICSEARCH_USERNAME=...
ELASTICSEARCH_PASSWORD=...
```

استفاده هم‌زمان از API Key و Basic Auth در حالت Production توسط `config.py` رد می‌شود.

## امنیت Production

سرویس Docker موجود در این بسته فقط برای توسعه Local است و Security داخلی Elasticsearch در آن خاموش شده، اما پورت فقط روی `127.0.0.1` Publish می‌شود. برای Production:

- Elasticsearch را مستقیماً روی اینترنت Publish نکنید.
- TLS و Authentication را فعال کنید یا از سرویس مدیریت‌شده استفاده کنید.
- Secretها را در `.env` Commit نکنید.
- `DEBUG=false` و تنظیمات Production در `SECURITY.md` را اعمال کنید.
- Worker را همیشه همراه Backend اجرا کنید؛ وگرنه تغییرات Outbox به‌صورت لحظه‌ای Sync نمی‌شوند.

## تست سریع جستجو

```bash
curl "http://127.0.0.1:8000/api/v1/tickets?q=tehran&ordering=demand&page=1&page_size=10"
```

فیلترهای API در هر دو Backend جستجو یکسان‌اند و شامل نوع ورزش، تیم، شهر، ورزشگاه، رده، سکشن، بازه زمانی، قیمت، ظرفیت، نوع صندلی و مرتب‌سازی هستند.
