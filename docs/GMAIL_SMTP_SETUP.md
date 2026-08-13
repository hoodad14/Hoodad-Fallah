# راه‌اندازی ایمیل واقعی Gmail برای OTP

نسخه فعلی ArenaPass ارسال کد یکبارمصرف را با SMTP واقعی Gmail انجام می‌دهد. کد در Redis با TTL نگهداری می‌شود و فقط در صورت پذیرش ایمیل توسط SMTP، API پاسخ موفق می‌دهد. Mailpit همچنان فقط به‌عنوان حالت آزمایشی اختیاری باقی مانده است.

## ۱. آماده‌کردن حساب Google

برای حساب فرستنده، تأیید دومرحله‌ای را فعال و یک **App Password** مخصوص ArenaPass ایجاد کنید. رمز عادی Gmail را در پروژه قرار ندهید. App Password را فقط در فایل `.env` محلی نگه دارید و آن را در GitHub قرار ندهید.

## ۲. تنظیم خودکار پروژه

در پوشه پروژه اجرا کنید:

```bash
python configure_gmail.py
```

سپس آدرس Gmail فرستنده و App Password را وارد کنید. هنگام واردکردن رمز چیزی روی صفحه نشان داده نمی‌شود. اگر Google رمز را با فاصله نمایش داده باشد، اسکریپت فاصله‌ها را حذف می‌کند.

روش غیرتعاملی فقط برای محیط امن قابل استفاده است:

```bash
python configure_gmail.py --email your-address@gmail.com
```

App Password را بهتر است از طریق Prompt وارد کنید و در آرگومان خط فرمان ننویسید تا وارد History ترمینال نشود.

## ۳. اجرای پروژه

```bash
docker compose down
docker compose up --build -d
```

وضعیت سرویس‌ها:

```bash
docker compose ps
docker compose logs backend --tail=100
```

در خروجی آمادگی باید SMTP آماده باشد و Backend در وضعیت Healthy قرار بگیرد.

## ۴. تست مستقل ایمیل واقعی

```bash
docker compose exec backend python smtp_smoke.py --to recipient@example.com
```

این دستور یک ایمیل تست بدون OTP ارسال می‌کند. بعد از دریافت آن، ثبت‌نام یا ورود با OTP را از رابط سایت آزمایش کنید.

## ۵. تنظیمات Gmail که در `.env` نوشته می‌شوند

```env
OTP_DEBUG_RETURN_CODE=false
OTP_EMAIL_ENABLED=true
OTP_EMAIL_REQUIRED=true
EMAIL_DELIVERY_MODE=smtp
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=ArenaPass <your-address@gmail.com>
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-address@gmail.com
EMAIL_HOST_PASSWORD=YOUR_GOOGLE_APP_PASSWORD
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_TIMEOUT=10
EMAIL_DELIVERY_RETRIES=4
EMAIL_HEALTHCHECK_CACHE_SECONDS=300
PUBLIC_MAILPIT_URL=
```

`EMAIL_HOST_PASSWORD` باید App Password باشد، نه رمز معمولی حساب.

## ۶. بازگشت به Mailpit محلی

```bash
python configure_gmail.py --mailpit
docker compose up --build -d
```

در این حالت ایمیل‌ها از مسیر `/mailpit/` همان سایت دیده می‌شوند.

## خطاهای متداول

- `Gmail app password is missing`: فایل `.env` هنوز مقدار نمونه دارد یا App Password وارد نشده است.
- `SMTPAuthenticationError`: معمولاً آدرس فرستنده یا App Password اشتباه است.
- `SMTPConnectError` یا Timeout: اتصال اینترنت، فایروال، VPN یا دسترسی Docker به `smtp.gmail.com:587` را بررسی کنید.
- Backend پس از تغییر `.env` همچنان تنظیم قبلی را دارد: کانتینرها را با `docker compose up --build -d --force-recreate` دوباره بسازید.
- ایمیل در Inbox نیست: پوشه Spam را بررسی کنید و چند دقیقه برای تحویل نهایی فرصت بدهید.

## نکات امنیتی

- فایل `.env` در `.gitignore` قرار دارد؛ آن را از حالت Ignore خارج نکنید.
- App Password را در اسکرین‌شات، README، Commit یا فایل ZIP عمومی قرار ندهید.
- در صورت افشای رمز، App Password را از حساب Google حذف و یک رمز جدید ایجاد کنید.
