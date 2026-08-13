# راهنمای احراز هویت و OTP ایمیل ArenaPass

این نسخه مسیر ثبت‌نام و ورود را به‌صورت واقعی و دومرحله‌ای اجرا می‌کند. حساب کاربر تا قبل از تأیید OTP ساخته نمی‌شود. PostgreSQL منبع حساب‌ها و Redis محل Pending Signup و OTPهای HMAC‌شده است. ارسال پیش‌فرض ایمیل از طریق SMTP واقعی Gmail انجام می‌شود و Mailpit فقط حالت آزمایشی اختیاری است.

بک‌اند فقط زمانی پاسخ موفق ارسال OTP را برمی‌گرداند که ارائه‌دهنده ایمیل پیام را پذیرفته باشد. در حالت Gmail، کد به Inbox واقعی کاربر می‌رود؛ در حالت Mailpit، شناسه پیام ذخیره‌شده نیز بررسی و به فرانت‌اند برگردانده می‌شود.

## 1. اجرای تمیز

این دستور Volume دیتابیس و Redis محلی را حذف می‌کند؛ برای شروع این نسخه لازم است:

```powershell
python configure_gmail.py
docker compose down -v --remove-orphans
docker compose pull
docker compose up --build -d
docker compose ps
```

وضعیت مورد انتظار:

```text
db         healthy
redis      healthy
mailpit    healthy
backend    healthy
worker     running
frontend   healthy
```

آدرس‌ها، با پورت پیش‌فرض:

```text
وب‌سایت:       http://127.0.0.1:8080
صندوق واقعی:   Inbox آدرس ایمیل واردشده
Mailpit اختیاری: http://127.0.0.1:8080/mailpit/
API:           http://127.0.0.1:8000/api/v1
Readiness:     http://127.0.0.1:8080/api/v1/ready
```

اگر در `.env` مقدار `FRONTEND_HOST_PORT=8081` است، هر دو رابط از همان پورت باز می‌شوند:

```text
http://127.0.0.1:8081
http://127.0.0.1:8081/mailpit/
```

پورت 8025 دیگر مستقیماً روی ویندوز منتشر نمی‌شود. این کار جلوی بازشدن یک Mailpit قدیمی یا کانتینر اشتباه را می‌گیرد؛ Mailpit فقط از مسیر همان Nginx پروژه باز می‌شود.

## 2. تست قطعی خودکار

بعد از Healthy شدن سرویس‌ها اجرا کنید:

```powershell
docker compose --profile test run --rm auth-smoke
```

خروجی موفق:

```text
AUTH_MAILPIT_SMOKE=PASS
verified_email=auth-smoke-...@example.test
```

این تست به‌ترتیب کارهای زیر را واقعاً انجام می‌دهد:

1. بررسی آمادگی Mailpit و بک‌اند
2. شروع ثبت‌نام با یک ایمیل منحصربه‌فرد
3. دریافت شناسه دقیق پیام ذخیره‌شده در Mailpit
4. خواندن OTP از همان پیام
5. تأیید ثبت‌نام و ساخت حساب
6. ورود با رمز
7. درخواست OTP ورود، خواندن ایمیل دوم و ورود با OTP

اگر این تست Fail شود، پیام آخر آن دقیقاً مرحله خراب را مشخص می‌کند.

## 3. تست دستی ثبت‌نام

1. وب‌سایت را باز کنید و وارد «ورود / ثبت‌نام» شوید.
2. تب «ثبت‌نام» را انتخاب کنید.
3. نام، نام خانوادگی، یک ایمیل جدید و رمز قوی مانند `TestPass123` وارد کنید.
4. روش تأیید را روی «ایمیل» بگذارید.
5. «ارسال کد تأیید و ادامه» را بزنید.
6. پس از پذیرش ایمیل توسط SMTP، مرحله دوم همان Dialog باز می‌شود و فیلد کد شش‌رقمی نمایش داده می‌شود.
7. Inbox یا Spam ایمیل واقعی را باز کنید. دکمه بازکردن صندوق فقط در حالت اختیاری Mailpit نمایش داده می‌شود.
8. کد شش‌رقمی داخل ایمیل «تأیید ثبت‌نام ArenaPass» را وارد کنید.
9. بعد از تأیید، حساب در PostgreSQL ساخته می‌شود و کاربر خودکار وارد سایت می‌شود.

تا قبل از مرحله 8، فقط Pending Signup در Redis وجود دارد و رمز خام ذخیره نمی‌شود.

## 4. ورود با OTP ایمیل

پس از ساخت حساب:

1. خارج شوید.
2. تب «ورود با کد یکبار مصرف» را باز کنید.
3. ایمیل تأییدشده را وارد کنید.
4. بعد از پذیرش پیام توسط SMTP، فرم ورود کد نمایش داده می‌شود.
5. Inbox یا Spam ایمیل را بررسی و کد پیام جدید را وارد کنید.

کد یک‌بارمصرف است، TTL دارد، بعد از مصرف حذف می‌شود و تعداد تلاش اشتباه محدود است.

## 5. حساب‌های نمونه

تماشاگر:

```text
Email:    hossein.m@gmail.com
Password: Demo@123
```

پشتیبان:

```text
Email:    sara.ahmadi@support.ir
Password: Demo@123
```

هر دو حساب Seed با رمز کار می‌کنند. برای ورود OTP نیز ایمیل حساب باید تأییدشده و سرویس SMTP واقعی آماده باشد.

## 6. بررسی API

شروع ثبت‌نام:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"User","email":"test-unique@example.com","password":"TestPass123","preferred_login":"email"}'
```

پاسخ موفق با وضعیت 202 شامل این اطلاعات است:

```json
{
  "registration_id": "...",
  "destination": "te***@example.com",
  "channel": "email",
  "delivery_message_id": "...",
  "mailbox_url": "/mailpit/",
  "expires_in": 300,
  "resend_after": 45
}
```

وجود `delivery_message_id` یعنی Mailpit پیام را ذخیره کرده است. OTP عمداً در پاسخ API برنمی‌گردد.

تأیید ثبت‌نام:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup/verify \
  -H "Content-Type: application/json" \
  -d '{"registration_id":"REGISTRATION_ID","code":"123456"}'
```

## 7. عیب‌یابی

وضعیت همه سرویس‌ها:

```powershell
docker compose ps
```

بررسی Email transport:

```powershell
curl http://127.0.0.1:8000/api/v1/auth/capabilities
curl http://127.0.0.1:8000/api/v1/ready
```

در پاسخ باید موارد زیر دیده شوند:

```json
{
  "otp": {"email": true},
  "email_transport": {
    "configured": true,
    "ready": true,
    "mode": "mailpit_api"
  },
  "local_mailbox_url": "/mailpit/"
}
```

لاگ‌های مرتبط:

```powershell
docker compose logs --tail=250 backend mailpit redis
docker compose logs -f backend mailpit
```

در ارسال موفق، لاگ بک‌اند دارای عبارتی مشابه زیر است:

```text
OTP email persisted in Mailpit ... message_id=...
```

اگر `otp_delivery_failed` برگردد، بک‌اند OTP و Cooldown همان درخواست را پاک می‌کند؛ حساب نیمه‌کاره ساخته نمی‌شود و می‌توانید پس از رفع سرویس دوباره تلاش کنید.

## 8. SMTP واقعی Gmail

SMTP واقعی اکنون در اجرای Docker نیز از `.env` خوانده می‌شود و Compose دیگر Mailpit را اجبار نمی‌کند. راه ساده:

```bash
python configure_gmail.py
docker compose up --build -d
docker compose exec backend python smtp_smoke.py --to recipient@example.com
```

تنظیمات اصلی:

```env
OTP_EMAIL_ENABLED=true
OTP_EMAIL_REQUIRED=true
OTP_DEBUG_RETURN_CODE=false
EMAIL_DELIVERY_MODE=smtp
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-address@gmail.com
EMAIL_HOST_PASSWORD=YOUR_GOOGLE_APP_PASSWORD
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=ArenaPass <your-address@gmail.com>
PUBLIC_MAILPIT_URL=
```

از App Password اختصاصی استفاده کنید و رمز عادی Gmail را در پروژه ننویسید. راهنمای کامل و رفع خطاها در `GMAIL_SMTP_SETUP.md` است. برای بازگشت به حالت محلی:

```bash
python configure_gmail.py --mailpit
```

## 9. کنترل‌های امنیتی

- Bcrypt با cost مناسب برای رمز حساب
- عدم ذخیره رمز خام در Pending Signup، Redis یا Log
- OTP شش‌رقمی تصادفی با HMAC، TTL، مصرف یک‌باره و سقف تلاش
- Rate Limit مستقل بر اساس Contact و IP و Cooldown ارسال مجدد
- ساخت حساب فقط بعد از OTP صحیح
- Access Token کوتاه‌عمر و Refresh Token چرخشی با Replay Detection
- ابطال نشست‌ها با `session_version` پس از تغییر رمز یا Contact
- RBAC سمت سرور برای نقش تماشاگر و پشتیبان
- پاسخ عمومی در OTP ورود برای کاهش Account Enumeration
- اتصال Same-Origin فرانت، API و Mailpit در محیط Local


## Mailpit UI fallback

رابط Mailpit فقط از مسیر هم‌مبدأ `/mailpit/` روی همان آدرس فرانت‌اند در دسترس است؛ برای نمونه `http://localhost:8080/mailpit/`. این روش از تداخل پورت و بازشدن نمونه اشتباه Mailpit جلوگیری می‌کند.
