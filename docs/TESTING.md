# راهنمای تست ArenaPass Backend

## 1. تست‌های Static و Unit

```bash
pip install -r requirements-dev.txt
pytest
python -m compileall -q *.py
python preflight.py --skip-services
```

مجموعه تست قراردادی موارد زیر را کنترل می‌کند:

- Parseشدن تمام فایل‌های Python
- نبود Django ORM در کد اجرایی
- وجود همه فایل‌های SQL و مستندات الزامی
- وجود توابع تراکنشی رزرو، پرداخت، کنسلی، تغییر صندلی و غیرفعال‌سازی کاربر
- وجود `session_version`، Audit Log و Transactional Search Outbox در Extension دیتابیس
- تطبیق دقیق ۶۶ عملیات میان Django URLها، دکوراتورها، OpenAPI و Postman
- نام صحیح فایل‌های SQL در Docker Compose
- Schema سخت‌گیرانه ورودی و ردکردن فیلدهای ناشناخته
- Validatorهای ایمیل، تلفن، رمز، Boolean، Integer و URL
- Serialization امن Decimal، UUID و Datetime
- وجود Elasticsearch Search Gateway، ۱۱ Trigger همگام‌سازی، Advisory Lock و Search Profile در Compose
- کنترل فعال‌بودن Sport/Team/Category و پنجره فروش در مسیرهای تراکنشی
- کنترل Holdهای رزرو/تغییر صندلی هنگام غیرفعال‌سازی Ticket
- کنترل Retry-After واقعی، Refresh Family Index و HTTPS اجباری برای Credentialهای Elasticsearch

## 2. اعتبارسنجی دیتابیس

روی دیتابیس PostgreSQL تازه، ترتیب اجرا:

1. `00_schema.sql`
2. `01_seed_data.sql`
3. `02_required_queries.sql`
4. `03_required_functions.sql`
5. `04_business_functions.sql`
6. `06_backend_extensions.sql`
7. `05_validation_tests.sql`

فایل Validation در صورت شکست ساختار، داده، محدودیت، Counter موجودی، Wallet، Payment، Refund، Role، Seat Change یا رفتار تراکنشی Exception می‌دهد. تغییرات سناریوهای رفتاری داخل Transaction اجرا و Rollback می‌شوند.

## 3. Preflight زنده

```bash
python preflight.py
```

این دستور علاوه بر فایل‌ها، اتصال PostgreSQL/Redis و وجود Schema/Functionهای ضروری را کنترل می‌کند. اگر Elasticsearch فعال باشد، دسترسی سرویس و وجود Alias جستجو نیز اجباری است.

## 4. Smoke Test غیرمخرب

بعد از Healthyشدن Stack:

```bash
python smoke_test.py
```

پوشش:

- Health
- Readiness
- ورود کاربر Seed
- Profile
- Ticket Search
- Reservation History

## 5. Integration Test کامل

این تست عمداً رکورد ایجاد و تغییر می‌دهد؛ فقط روی Local/CI ایزوله اجرا شود:

```bash
# Integration test از debug code استفاده می‌کند؛ فقط در محیط ایزوله، ابتدا در .env:
# OTP_DEBUG_RETURN_CODE=true
# سپس Backend را بازسازی کنید:
docker compose up -d --force-recreate backend
python integration_test.py --yes-destructive
```

پوشش End-to-End:

- Signup دومرحله‌ای، تأیید/ارسال مجدد OTP و رد Mass Assignment
- OTP و مصرف یک‌باره
- Refresh Rotation و Replay Detection
- تغییر پروفایل، OTP تغییر رمز و ابطال نشست پس از تغییر رمز
- Lookupها و Ticket Search
- Hold اتمیک، Payment، Issued Ticket
- Review رزرو و اصلاح اختیاری صندلی توسط پشتیبان
- Cancellation Quote، درخواست، تأیید پشتیبان و Refund
- Wallet Ledger و Booking History
- Report و پاسخ پشتیبان
- RBAC و Logout

پس از تست، برای بازگشت به Seed خالص:

```bash
docker compose down -v
docker compose up --build -d
```

## 6. تست هم‌زمانی پیشنهادی

دو Session مستقل PostgreSQL به طور هم‌زمان `reserve_ticket()` را برای آخرین صندلی شماره‌دار فراخوانی کنند. فقط یک Transaction باید Commit شود؛ دیگری باید خطای موجودی دریافت کند. تابع، ردیف بلیط را Lock می‌کند و Deferred Constraintها Counter نهایی را اعتبارسنجی می‌کنند.

برای تست API سطح بالا نیز می‌توان چند Process هم‌زمان به `POST /api/v1/reservations` برای همان بلیط فرستاد و سپس کنترل کرد:

```sql
SELECT id,total_capacity,held_quantity,sold_quantity,change_held_quantity,available_quantity
FROM tickets
WHERE id=<ticket_id>;
```

همواره باید برقرار باشد:

```text
available_quantity = total_capacity - held_quantity - sold_quantity - change_held_quantity
available_quantity >= 0
```

## 7. تست Elasticsearch اختیاری

در `.env` مقدار `ELASTICSEARCH_ENABLED=true` بگذارید و Stack را با Profile جستجو بالا بیاورید:

```bash
docker compose --profile search down -v
docker compose --profile search up --build -d
```

Full Sync، Readiness و Query:

```bash
docker compose --profile search exec backend python sync_search_index.py --full
curl -fsS http://127.0.0.1:8000/api/v1/ready
curl -fsS "http://127.0.0.1:8000/api/v1/tickets?q=tehran&page=1&page_size=10"
```

برای تست Outbox، یک Ticket را از API پشتیبان تغییر دهید، سپس Log Worker و خالی‌شدن Pendingهای Outbox را بررسی کنید:

```sql
SELECT id,ticket_id,revision,attempts,available_at,last_error
FROM search_sync_outbox
WHERE processed_at IS NULL
ORDER BY id;
```

قطع موقت Elasticsearch با `ELASTICSEARCH_FALLBACK_TO_SQL=true` نباید API جستجو را از کار بیندازد؛ ولی Readiness باید وابستگی Search را ناآماده گزارش کند. جزئیات در `ELASTICSEARCH.md` است.

## 8. کنترل Docker

```bash
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs --no-color backend worker db redis
# حالت Search:
docker compose --profile search logs --no-color backend worker db redis elasticsearch
```

سپس:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/ready
```

## تست واقعی ثبت‌نام و Mailpit

پس از بالا آمدن Docker، مسیر کامل ثبت‌نام، خواندن OTP از پیام دقیق Mailpit، تأیید حساب، ورود با رمز و ورود OTP را اجرا کنید:

```powershell
docker compose --profile test run --rm auth-smoke
```

خروجی مورد انتظار:

```text
AUTH_MAILPIT_SMOKE=PASS
```

این تست از `delivery_message_id` همان پاسخ ثبت‌نام استفاده می‌کند و به «آخرین ایمیل» متکی نیست؛ بنابراین با اجرای هم‌زمان یا پیام‌های قدیمی اشتباه نمی‌شود.
