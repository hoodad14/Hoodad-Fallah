# ماتریس پوشش نیازمندی‌های بک‌اند ArenaPass

| نیاز داک | Endpoint / پیاده‌سازی | وضعیت |
|---|---|---|
| ثبت‌نام و JWT | `POST /api/v1/auth/signup`, `/signup/resend`, `/signup/verify` | کامل؛ ایجاد User فقط پس از OTP |
| ورود با رمز | `POST /api/v1/auth/password/login` | کامل |
| درخواست و تأیید OTP | `POST /api/v1/auth/otp/request`, `/verify` | کامل؛ Redis TTL/HMAC/Rate limit |
| Refresh و Logout | `/auth/token/refresh`, `/auth/logout` | کامل؛ Rotation و Replay detection |
| پروفایل و تغییر اطلاعات | `GET/PATCH /api/v1/profile` | کامل؛ Cache invalidation |
| تغییر رمز دو مرحله‌ای | `/profile/password/otp/request`, `/profile/password` | کامل |
| تغییر Contact/روش ورود | `/profile/contact/request`, `/confirm` | کامل؛ OTP و ابطال نشست‌ها |
| شهرها و ورزشگاه‌ها | `GET /api/v1/cities`, `/venues` | کامل و Cache شده |
| جستجوی پیشرفته بلیط | `GET /api/v1/tickets` | کامل؛ PostgreSQL/Elasticsearch، فیلتر، ترتیب، صفحه‌بندی، Cache |
| جزئیات بلیط | `GET /api/v1/tickets/{id}` | کامل؛ امکانات و کنترل Visibility |
| رزرو ده‌دقیقه‌ای | `POST /api/v1/reservations` + `reserve_ticket` | کامل؛ Lock و ضد Overselling |
| رزروهای فعال/تاریخچه | `GET /api/v1/reservations`, `/{id}` | کامل |
| پرداخت محلی | `POST /api/v1/reservations/{id}/pay` | کامل؛ Wallet/Local gateway و Idempotency |
| کیف پول/تراکنش | `GET /api/v1/wallet`, `/payments` | کامل |
| لیست خریدها | `GET /api/v1/bookings` | کامل؛ آینده/گذشته/کنسل‌شده |
| جریمه کنسلی | `GET /api/v1/reservations/{id}/cancellation-quote` | کامل؛ Policy برگزارکننده |
| درخواست کنسلی و Refund | `POST .../cancellation-requests` + Support review | کامل |
| تغییر صندلی | Seat change request/options + Support review | کامل برای مقصد هم‌قیمت |
| گزارش مشکل | `GET/POST /api/v1/reports` | کامل |
| بلیط صادرشده/QR | `GET /api/v1/issued-tickets` | کامل |
| گفتگوی مستقیم تماشاگر و پشتیبان | `support-chat` و `support/chats` | کامل؛ پیام، خوانده‌نشده، پاسخ، بستن/بازگشایی |
| داشبورد پشتیبان | `GET /api/v1/support/dashboard` | کامل |
| بررسی/تأیید/اصلاح/لغو رزرو | Support reservation APIs | کامل |
| پرداخت مشکوک | `GET /api/v1/support/payments/suspicious` | کامل |
| رسیدگی گزارش‌ها | Support report APIs | کامل |
| مدیریت بلیط | Support ticket CRUD/deactivation | کامل |
| انقضای خودکار | `worker.py`, `expire_pending_reservations` | کامل |
| Redis Sync/Invalidation | `cache.py`, service invalidators | کامل |
| Raw SQL بدون ORM | `database.py`, SQL functions | کامل |
| Elasticsearch فاز چهارم | `search_engine.py`, `search_sync_outbox`, `worker.py` | کامل در حالت اختیاری؛ Alias اتمیک، Sync و SQL fallback |
| Docker | `Dockerfile`, `docker-compose.yml` | کامل؛ DB/Redis/API/Worker و Profile اختیاری Search |
| مستندات و تست | README, OpenAPI, Postman, Pytest, Smoke/Integration | کامل در بسته |
