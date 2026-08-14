# MahTicket - بسته کامل دیتابیس، بک‌اند و فرانت‌اند

> **Delivery safety:** the ZIP contains a placeholder `.env` for easier setup, but no real mailbox password or deployable secret. Run `python configure_gmail.py` before starting Docker and never commit the generated `.env`.

## فرانت‌اند نهایی

این نسخه علاوه بر تمام اجزای دیتابیس و بک‌اند v3.1.0، یک فرانت‌اند کامل و حرفه‌ای با **HTML، CSS و JavaScript خالص** دارد. فایل‌های `index.html`، `styles.css` و `app.js` مستقیماً در همین پوشه قرار گرفته‌اند و با قرارداد `openapi.json` متصل می‌شوند. رابط شامل صفحه اصلی، جستجوی پیشرفته، جزئیات و رزرو بلیط، ورود رمز/OTP، ثبت‌نام، پنل تماشاگر، پرداخت، کنسلی و استرداد، تغییر جایگاه، گزارش مشکل، گفتگوی مستقیم تماشاگر با پشتیبان و پنل کامل پشتیبان است. راهنمای جزئیات و اجرا در `FRONTEND_README.md` آمده است.

اجرای کامل و یکپارچه پروژه:

```bash
python configure_gmail.py
docker compose up --build -d
```

دستور اول آدرس Gmail فرستنده و **Google App Password** را به‌صورت امن دریافت و SMTP واقعی را در `.env` فعال می‌کند. سپس OTP ثبت‌نام، ورود، تغییر رمز و تغییر راه ارتباطی واقعاً به Inbox کاربر ارسال می‌شود. برای تست مستقل:

```bash
docker compose exec backend python smtp_smoke.py --to recipient@example.com
```

راهنمای کامل در `GMAIL_SMTP_SETUP.md` آمده است. برای بازگشت موقت به صندوق آزمایشی محلی می‌توانید `python configure_gmail.py --mailpit` را اجرا کنید.

سپس آدرس `http://127.0.0.1:${FRONTEND_HOST_PORT}` را باز کنید (پیش‌فرض `8080` و در صورت اشغال‌بودن پورت می‌توانید در `.env` مقدار `8081` بگذارید). سرویس `frontend` با Nginx اجرا می‌شود و درخواست‌های `/api/v1` را داخل شبکه Docker به بک‌اند می‌فرستد؛ بنابراین ورود و OTP روی هر پورت فرانت‌اند به‌صورت Same-Origin کار می‌کنند و نیازی به تنظیم دستی CORS نیست. در حالت پیش‌فرض Gmail، کد به ایمیل واقعی کاربر می‌رود؛ مسیر `/mailpit/` فقط پس از فعال‌کردن حالت محلی Mailpit استفاده می‌شود.

بسته کامل سامانه رزرو و خرید بلیط مسابقات ورزشی شامل دیتابیس، بک‌اند و فرانت‌اند، با بک‌اند پیاده‌سازی‌شده با **Django + PostgreSQL + Redis** و موتور جستجوی اختیاری **Elasticsearch**، مطابق الزام داک پروژه مبنی بر **عدم استفاده از ORM**. تمام فایل‌های تحویل عمداً در یک پوشه تخت قرار دارند و هیچ پوشه کد یا دیتابیس جداگانه‌ای وجود ندارد.

## وضعیت پوشش پروژه

این بسته موارد اصلی فاز سوم داک را پوشش می‌دهد:

- ثبت‌نام دومرحله‌ای با تأیید Email/Phone، ورود با رمز، ورود OTP و JWT نقش‌محور برای `spectator` و `support`
- Refresh Token چرخشی، تشخیص استفاده مجدد، Logout و ابطال همه نشست‌ها پس از تغییر رمز یا اطلاعات تماس
- OTP در Redis با TTL، محدودیت درخواست/تلاش و ارسال مجدد، ذخیره HMAC و مصرف یک‌باره؛ ارسال پیش‌فرض ایمیل با SMTP واقعی Gmail و حالت اختیاری Mailpit یا Webhook عمومی SMS
- پروفایل، تغییر رمز با تأیید OTP، شهرها، ورزشگاه‌ها، مسابقات، رشته‌ها، رده‌ها، امکانات و روش‌های پرداخت
- جستجوی پیشرفته بلیط با فیلتر، مرتب‌سازی، صفحه‌بندی و Redis Cache؛ قابل اجرا روی PostgreSQL یا Elasticsearch
- رزرو اتمیک محدود به زمان، جلوگیری از Overselling، پرداخت محلی، کیف پول، صدور بلیط و QR
- انقضای خودکار رزرو و Hold تغییر صندلی توسط Worker مستقل
- Elasticsearch اختیاری با Strict Mapping، Alias اتمیک، Transactional Outbox، Retry و Full Reconciliation
- قیمت‌گذاری کنسلی، درخواست کنسلی، بررسی پشتیبان، Refund و ثبت Ledger کیف پول
- تغییر صندلی/سکشن، گزارش مشکل، تاریخچه خرید و پنل عملیاتی پشتیبان
- چت مستقیم تماشاگر و پشتیبان با دکمه شناور دنبال‌کننده اسکرول، پیام‌های خوانده‌نشده، پاسخ پشتیبان و بستن/بازگشایی گفتگو
- تأیید/علامت‌گذاری رزرو توسط پشتیبان و اصلاح امن صندلی از مسیر Seat Change
- Audit Log، Request ID، CORS Allow-list، Security Headers، Rate Limit و پاسخ JSON استاندارد
- OpenAPI 3.1، Postman Collection، Unit/Contract Test، Smoke Test و Integration Test
- Query String سخت‌گیرانه، Visibility عمومی/پشتیبان مجزا، Readiness وابسته به تنظیمات و Headerهای استاندارد HTTP
- کنترل چندلایه فعال‌بودن Sport/Team/Category و پنجره فروش در رزرو، پرداخت و تغییر صندلی
- غیرفعال‌سازی امن Ticket با جلوگیری از دورزدن Holdهای رزرو و تغییر صندلی
- Retry-After دقیق و Redis Index برای ابطال سریع Refresh Token Family

## معماری

```text
Client
  │ HTTPS / JSON / Bearer JWT
  ▼
Django API (بدون ORM)
  ├── views.py                    Endpoint validation + single responsibility
  ├── authentication.py           JWT / OTP / RBAC / rate limiting
  ├── services_auth.py            حساب و پروفایل
  ├── services_catalog.py         Lookup / search / ticket details
  ├── services_reservations.py    Reservation / payment / wallet / report
  ├── services_support.py         عملیات پشتیبان
  ├── services_chat.py            گفتگوی مستقیم تماشاگر و پشتیبان
  ├── database.py                 psycopg pool + raw parameterized SQL
  ├── cache.py                    Redis cache / OTP / token state
  ├── search_engine.py            Elasticsearch REST / Alias / Outbox sync
  └── worker.py                   expiration + reminders + search sync
          │                   │                    │
          ▼                   ▼                    ▼
    PostgreSQL             Redis             Elasticsearch
Source of truth       OTP/Cache/JWT       Search-only index
Constraints/Functions Outbox state        Atomic alias swap
```

منطق حساس موجودی و مالی داخل توابع تراکنشی PostgreSQL اجرا می‌شود. API صرفاً ورودی را اعتبارسنجی کرده، مجوز را بررسی می‌کند و توابع دیتابیس را داخل Transaction مناسب فراخوانی می‌کند.

## اجرای پیشنهادی با Docker

### پیش‌نیازها

- Docker Desktop یا Docker Engine
- Docker Compose v2 یا جدیدتر

### راه‌اندازی

برای جلوگیری از تحویل Secret، بسته فقط `.env.example` دارد. ابتدا فایل محلی `.env` را بسازید:

```bash
python setup_env.py
```

مقادیر نمونه صرفاً برای اجرای Local هستند و قبل از Production باید Secretها و تنظیمات امنیتی تغییر کنند. سپس:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f frontend backend worker db redis
```

آدرس‌ها:

```text
وب‌سایت:      http://127.0.0.1:8080  (یا پورت FRONTEND_HOST_PORT)
API مستقیم:   http://127.0.0.1:8000/api/v1
API از فرانت: http://127.0.0.1:8080/api/v1
Mailpit OTP:  http://127.0.0.1:8080/mailpit/  (همان پورت فرانت‌اند)
Health:       http://127.0.0.1:8080/api/v1/health
Readiness:    http://127.0.0.1:8080/api/v1/ready
```

Backend و Worker قبل از شروع، وجود PostgreSQL، Redis، جداول، ستون `session_version` و توابع اصلی رزرو/پرداخت را بررسی می‌کنند. سرویس Frontend نیز تا سالم‌شدن Readiness بک‌اند منتظر می‌ماند و سپس رابط را روی پورت ۸۰۸۰ ارائه می‌کند. در صورت ناقص‌بودن Schema، سرویس با پیام روشن متوقف می‌شود.

### اجرای حالت کامل جستجو با Elasticsearch

در `.env` مقدار `ELASTICSEARCH_ENABLED=true` قرار دهید و Profile جستجو را فعال کنید:

```bash
docker compose --profile search down -v
docker compose --profile search up --build -d
docker compose --profile search logs -f elasticsearch backend worker
```

در این حالت Startup یک Index جدید از `v_ticket_catalog` می‌سازد و Alias عمومی را اتمیک فعال می‌کند. تغییرات بعدی از طریق جدول `search_sync_outbox` و Worker همگام می‌شوند. راهنمای کامل، فرمان Sync دستی، Fallback و نکات Production در `ELASTICSEARCH.md` است.

### نکته مهم درباره Volume

اسکریپت‌های `docker-entrypoint-initdb.d` فقط هنگام ساخت Volume خالی اجرا می‌شوند. پس از تغییر SQLها یا هنگام اولین اجرای این نسخه، بازسازی کامل توصیه می‌شود:

```bash
docker compose down -v
docker compose up --build -d
```

توقف بدون حذف داده:

```bash
docker compose down
```

### اجرای آفلاین

اولین Build معمولاً برای دریافت Imageهای Docker و Packageهای Python به اینترنت نیاز دارد. پس از Cacheشدن Imageها و Layerها، اجرای بعدی می‌تواند بدون اینترنت انجام شود. خود برنامه در حالت Local به سرویس خارجی وابسته نیست؛ مگر اینکه ارسال واقعی ایمیل/SMS را فعال کنید.

## اجرای بدون Docker

پیش‌نیاز: Python 3.10+، PostgreSQL 15+ و Redis. Elasticsearch فقط در حالت `ELASTICSEARCH_ENABLED=true` لازم است.

```bash
cp .env.example .env
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

فایل‌های SQL را دقیقاً به ترتیب زیر اجرا کنید:

```text
00_schema.sql
01_seed_data.sql
02_required_queries.sql
03_required_functions.sql
04_business_functions.sql
06_backend_extensions.sql
05_validation_tests.sql
```

نمونه:

```bash
psql "$DATABASE_URL" -f "00_schema.sql"
psql "$DATABASE_URL" -f "01_seed_data.sql"
psql "$DATABASE_URL" -f "02_required_queries.sql"
psql "$DATABASE_URL" -f "03_required_functions.sql"
psql "$DATABASE_URL" -f "04_business_functions.sql"
psql "$DATABASE_URL" -f "06_backend_extensions.sql"
psql "$DATABASE_URL" -f "05_validation_tests.sql"
```

سپس در دو ترمینال:

```bash
python preflight.py
python manage.py runserver 127.0.0.1:8000
```

```bash
python worker.py
```

یا از `run_local.sh/.bat` و `run_worker_local.sh/.bat` استفاده کنید.

## کاربران Seed

رمز همه کاربران نمونه:

```text
Demo@123
```

تماشاگر:

```text
Email: hossein.m@gmail.com
Phone: 09131000006
```

پشتیبان:

```text
Email: sara.ahmadi@support.ir
Phone: 09121000001
```

## قرارداد پاسخ

موفق:

```json
{
  "success": true,
  "data": {},
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "pages": 5
  }
}
```

خطا:

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "quantity must be at least 1.",
    "request_id": "..."
  }
}
```

مقادیر مالی `Decimal` به شکل String و زمان‌ها به شکل ISO-8601 برگردانده می‌شوند.

## احراز هویت سریع

ورود با رمز:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/password/login \
  -H "Content-Type: application/json" \
  -d '{"contact":"hossein.m@gmail.com","password":"Demo@123"}'
```

درخواست OTP محلی:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"contact":"hossein.m@gmail.com"}'
```

در تنظیم پیش‌فرض، `OTP_DEBUG_RETURN_CODE=false` و `EMAIL_DELIVERY_MODE=smtp` است؛ بک‌اند کد را از طریق SMTP واقعی ارسال می‌کند و فقط بعد از پذیرش پیام توسط سرویس ایمیل پاسخ موفق می‌دهد. برای تست مستقل از `smtp_smoke.py` استفاده کنید. حالت Mailpit با `python configure_gmail.py --mailpit` فعال می‌شود و `OTP_DEBUG_RETURN_CODE=true` فقط برای تست ایزوله است و در Production ممنوع است.

### تست رابط ثبت‌نام و OTP ایمیل

1. وب‌سایت را باز کنید و تب «ثبت‌نام» را انتخاب کنید.
2. یک ایمیل دلخواه، نام و رمز قوی مانند `TestPass1` وارد کنید و روش ترجیحی را Email بگذارید.
3. بعد از ارسال، فرم ورود کد شش‌رقمی در همان Dialog نمایش داده می‌شود.
4. دکمه «باز کردن صندوق ایمیل» را بزنید یا مسیر `/mailpit/` همان سایت را باز کنید، آخرین ایمیل را بخوانید و کد را در فرم وارد کنید.
5. پس از تأیید، حساب در PostgreSQL ساخته، Contact تأیید و JWT صادر می‌شود.
6. برای ورود OTP به تب «ورود با کد یکبار مصرف» بروید و Email همان حساب یا `hossein.m@gmail.com` را وارد کنید.

جزئیات کامل، تنظیم SMTP واقعی و سناریوهای تست در `AUTHENTICATION_GUIDE.md` آمده است.

## فهرست APIها

| Method | Endpoint | وظیفه | دسترسی |
|---|---|---|---|
| `GET` | `/api/v1/health` | Process health | عمومی |
| `GET` | `/api/v1/ready` | PostgreSQL and Redis readiness | عمومی |
| `POST` | `/api/v1/auth/signup` | Start verified spectator registration and send OTP | عمومی |
| `POST` | `/api/v1/auth/signup/resend` | Resend pending signup OTP | عمومی |
| `POST` | `/api/v1/auth/signup/verify` | Verify signup OTP, create account and issue tokens | عمومی |
| `POST` | `/api/v1/auth/password/login` | Password login | عمومی |
| `POST` | `/api/v1/auth/otp/request` | Request login OTP | عمومی |
| `POST` | `/api/v1/auth/otp/verify` | Verify OTP and issue tokens | عمومی |
| `POST` | `/api/v1/auth/token/refresh` | Rotate refresh token | عمومی |
| `POST` | `/api/v1/auth/logout` | Revoke current tokens | JWT |
| `GET` | `/api/v1/profile` | Get current profile | JWT |
| `PATCH` | `/api/v1/profile` | Update current profile | JWT |
| `POST` | `/api/v1/profile/password` | Change password with current password and OTP | JWT |
| `POST` | `/api/v1/profile/contact/request` | Request OTP for contact change | JWT |
| `POST` | `/api/v1/profile/contact/confirm` | Confirm contact change | JWT |
| `GET` | `/api/v1/cities` | List cities and provinces | عمومی |
| `GET` | `/api/v1/venues` | List active venues | عمومی |
| `GET` | `/api/v1/sports` | List active sport types | عمومی |
| `GET` | `/api/v1/matches` | List matches | عمومی |
| `GET` | `/api/v1/ticket-categories` | List ticket categories | عمومی |
| `GET` | `/api/v1/amenities` | List amenities | عمومی |
| `GET` | `/api/v1/payment-methods` | List payment methods | عمومی |
| `GET` | `/api/v1/report-categories` | List report categories | عمومی |
| `GET` | `/api/v1/tickets` | Search available tickets | عمومی |
| `GET` | `/api/v1/tickets/{ticket_id}` | Get ticket details | عمومی |
| `GET` | `/api/v1/wallet` | Get wallet and recent ledger | JWT |
| `POST` | `/api/v1/wallet/top-up` | Top up local wallet | JWT |
| `GET` | `/api/v1/reservations` | List own reservations | JWT |
| `POST` | `/api/v1/reservations` | Create atomic ticket hold | JWT |
| `GET` | `/api/v1/reservations/{reservation_id}` | Get reservation details | JWT |
| `POST` | `/api/v1/reservations/{reservation_id}/pay` | Pay reservation | JWT |
| `GET` | `/api/v1/reservations/{reservation_id}/cancellation-quote` | Calculate cancellation penalty/refund | JWT |
| `POST` | `/api/v1/reservations/{reservation_id}/cancellation-requests` | Request cancellation | JWT |
| `POST` | `/api/v1/reservations/{reservation_id}/seat-change-requests` | Request same-price seat or section change | JWT |
| `GET` | `/api/v1/seat-change-options` | List eligible seat-change destinations | JWT |
| `GET` | `/api/v1/payments` | List own payments | JWT |
| `GET` | `/api/v1/bookings` | List purchased tickets | JWT |
| `GET` | `/api/v1/reports` | List own reports | JWT |
| `POST` | `/api/v1/reports` | Create ticket/payment/reservation issue report | JWT |
| `GET` | `/api/v1/issued-tickets` | List issued ticket and QR records | JWT |
| `GET` | `/api/v1/support-chat` | دریافت گفتگوی کاربر و پیام‌ها | JWT تماشاگر |
| `POST` | `/api/v1/support-chat/messages` | ارسال پیام کاربر به پشتیبانی | JWT تماشاگر |
| `POST` | `/api/v1/support-chat/read` | علامت‌گذاری پاسخ‌ها به‌عنوان خوانده‌شده | JWT تماشاگر |
| `GET` | `/api/v1/support/chats` | فهرست گفتگوهای پشتیبانی | JWT پشتیبان |
| `GET` | `/api/v1/support/chats/{conversation_id}` | دریافت جزئیات یک گفتگو | JWT پشتیبان |
| `POST` | `/api/v1/support/chats/{conversation_id}/messages` | پاسخ پشتیبان به گفتگو | JWT پشتیبان |
| `PATCH` | `/api/v1/support/chats/{conversation_id}/status` | بستن یا بازگشایی گفتگو | JWT پشتیبان |
| `GET` | `/api/v1/support/dashboard` | Support dashboard | JWT |
| `GET` | `/api/v1/support/reservations` | Support reservation search | JWT |
| `POST` | `/api/v1/support/reservations/{reservation_id}/cancel` | Support cancellation of held reservation | JWT |
| `GET` | `/api/v1/support/payments/suspicious` | List suspicious payments | JWT |
| `GET` | `/api/v1/support/cancellation-requests` | List cancellation requests | JWT |
| `POST` | `/api/v1/support/cancellation-requests/{request_id_value}/review` | Approve or reject cancellation/refund | JWT |
| `GET` | `/api/v1/support/seat-change-requests` | List seat-change requests | JWT |
| `POST` | `/api/v1/support/seat-change-requests/{request_id_value}/review` | Approve or reject seat change | JWT |
| `GET` | `/api/v1/support/reports` | List all reports | JWT |
| `PATCH` | `/api/v1/support/reports/{report_id}` | Assign/respond/close report | JWT |
| `POST` | `/api/v1/support/users/{user_id}/deactivate` | Deactivate user safely | JWT |
| `GET` | `/api/v1/support/tickets` | List ticket rows for support | JWT |
| `POST` | `/api/v1/support/tickets` | Create ticket row | JWT |
| `PATCH` | `/api/v1/support/tickets/{ticket_id}` | Update ticket row | JWT |
| `DELETE` | `/api/v1/support/tickets/{ticket_id}` | Deactivate ticket row | JWT |
| `POST` | `/api/v1/profile/password/otp/request` | Request OTP for password change | JWT |
| `POST` | `/api/v1/support/reservations/{reservation_id}/review` | Confirm or flag a reservation for correction | JWT |
| `POST` | `/api/v1/support/reservations/{reservation_id}/seat-correction` | Correct reservation seat through safe seat-change workflow | JWT |

## جستجوی بلیط

پارامترها:

```text
q, sport, team, city_id, venue_id, category, section,
date_from, date_to, price_min, price_max, min_available,
numbered, ordering, page, page_size
```

مقادیر مرتب‌سازی:

```text
starts_at, -starts_at, price, -price, demand, availability
```

`date_from` و `date_to` باید ISO-8601 همراه Offset زمانی باشند؛ نمونه:

```text
2026-08-10T18:00:00+03:30
```

## مستندات API

- `openapi.json`: قرارداد OpenAPI 3.1 برای تمام ۶۶ عملیات
- `ELASTICSEARCH.md`: راه‌اندازی، Sync، Fallback و امنیت موتور جستجو
- `ArenaPass.postman_collection.json`: Collection آماده با متغیرها و Scriptهای ثبت Token/ID
- متغیرهای اصلی Postman: `base_url`, `access_token`, `refresh_token`, `otp_code`, `ticket_id`, `reservation_id`

## تست

تست‌های سریع و غیرزنده:

```bash
pip install -r requirements-dev.txt
pytest
python -m compileall -q *.py
python preflight.py --skip-services
```

Smoke Test غیرمخرب بعد از بالا آمدن سرویس:

```bash
python smoke_test.py
```

Integration Test کامل و داده‌نویس فقط روی دیتابیس Local/CI ایزوله:

```bash
python integration_test.py --yes-destructive
```

جزئیات کامل در `TESTING.md` است.

## تنظیمات Production

حداقل موارد ضروری:

```text
DEBUG=false
OTP_DEBUG_RETURN_CODE=false
ALLOW_LOCAL_WALLET_TOP_UP=false
CORS_ALLOW_ALL=false
DJANGO_SECRET_KEY=<strong unique secret>
JWT_SECRET=<different strong secret>
OTP_HMAC_SECRET=<another different strong secret>
ALLOWED_HOSTS=<exact hosts>
CORS_ALLOWED_ORIGINS=<exact origins>
```

`config.py` تنظیم ناامن Production را در Startup رد می‌کند. چک‌لیست کامل در `SECURITY.md` آمده است.

## فایل‌های مهم تحویل

- داک رسمی جدید: `پروژه پایانی درس(15).pdf`
- نسخه قبلی داک که در بسته اولیه وجود داشت: `پروژه پایانی درس(14).pdf`
- فرانت‌اند: `index.html`, `styles.css`, `i18n.js`, `app.js`, `FRONTEND_README.md`
- دیتابیس: `00_schema.sql` تا `06_backend_extensions.sql`
- هسته Django: `settings.py`, `urls.py`, `views.py`, `services_*.py`
- Infra: `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `worker.py`, `search_engine.py`, `sync_search_index.py`
- کیفیت: `test_*.py`, `smoke_test.py`, `integration_test.py`, `preflight.py`
- گزارش ممیزی: `BACKEND_REVIEW_REPORT.md`, `API_COVERAGE_MATRIX.md`, `VERIFICATION_REPORT.txt`
- راهنمای اجرای نهایی: `FINAL_DELIVERY_CHECKLIST.md`
- راهنمای الزامات Git داک: `GIT_DELIVERY_GUIDE.md`
- صحت فایل‌ها: `SHA256SUMS.txt`

## چت پشتیبانی و موشن دکمه

دکمه تغییر زبان با برچسب زبان فعلی (`FA` یا `EN`) کنار دکمه روشن/تیره قرار دارد. با هر کلیک، متن‌های ثابت و پویا، عنوان‌ها، منوها، دکمه‌ها و فرم‌ها ترجمه می‌شوند و جهت صفحه بین RTL و LTR تغییر می‌کند. انتخاب زبان در مرورگر ذخیره می‌شود. دکمه چت همچنان روی Dock ثابت قرار دارد تا با باز و بسته‌شدن پنجره، موقعیت صفحه یا Scroll تغییر نکند.

موشن کششی دکمه هنگام Scroll در فایل `app.js` و داخل ثابت `SUPPORT_CHAT_MOTION_CONFIG` تنظیم می‌شود. مهم‌ترین گزینه‌ها:

- `MAX_OFFSET`: حداکثر جابه‌جایی کششی دکمه بر حسب پیکسل.
- `IMPULSE_FACTOR`: شدت واکنش دکمه به سرعت Scroll.
- `DAMPING`: مدت و نرمی برگشت فنری؛ مقدار بزرگ‌تر بازگشت را طولانی‌تر می‌کند و بهتر است کمتر از `0.90` بماند.
- `MAX_STRETCH`: حداکثر کشیدگی عمودی خود دکمه.


## محدودیت‌های آگاهانه

- درگاه بانکی واقعی طبق داک لازم نیست؛ `local_gateway` شبیه‌ساز محلی است.
- ارسال واقعی SMS به Provider خاص وابسته نشده؛ یک JSON Webhook عمومی ارائه شده است.
- Elasticsearch در حالت پیش‌فرض خاموش است تا فاز سوم سبک اجرا شود؛ با Profile `search` کل بخش Backend جستجوی فاز چهارم فعال می‌شود.
- ساختار اصلی دیتابیس و داده‌های Seed حفظ شده‌اند؛ در `00_schema.sql` فقط Visibility کاتالوگ برای Active بودن وابستگی‌ها کامل‌تر شده و در `04_business_functions.sql` رفتار Retry پرداخت موفق صریحاً Idempotent شده است. `06_backend_extensions.sql` نیازهای Backend مانند Audit و Version نشست را اضافه می‌کند.


## Mailpit UI fallback

رابط Mailpit فقط از مسیر هم‌مبدأ `/mailpit/` روی همان آدرس فرانت‌اند در دسترس است؛ برای نمونه `http://localhost:8080/mailpit/`. این روش از تداخل پورت و بازشدن نمونه اشتباه Mailpit جلوگیری می‌کند.
