# گزارش بازبینی احراز هویت ArenaPass

## دامنه اصلاح

مسیرهای ثبت‌نام دومرحله‌ای، OTP ایمیل، ورود با رمز، ورود OTP، Refresh Token و RBAC بررسی و اصلاح شدند. تمرکز این نسخه رفع دو خطای عملی بود: ثبت نشدن ایمیل در Mailpit و باز نشدن مرحله ورود کد در رابط ثبت‌نام.

## اصلاحات کلیدی

- Local Docker از `EMAIL_DELIVERY_MODE=mailpit_api` استفاده می‌کند.
- بک‌اند پیام را با `POST /api/v1/send` در Mailpit ثبت می‌کند.
- شناسه پیام برگشتی گرفته و با `GET /api/v1/message/{ID}` دوباره بررسی می‌شود.
- در صورت شکست تحویل، OTP و Cooldown پاک می‌شوند و پاسخ 503 ساختاریافته برمی‌گردد.
- مرحله Verification فرانت‌اند قبل از هر عملیات Session Storage نمایش داده می‌شود؛ خرابی Storage دیگر UI را متوقف نمی‌کند.
- پاسخ ارسال شامل Message ID واقعی Mailpit است و دکمه‌های ثبت‌نام و ورود مستقیماً همان ایمیل را باز می‌کنند.
- فایل JavaScript با نسخه `1.2.2` Cache-bust شده و Nginx برای فایل‌های احراز هویت `no-store` برمی‌گرداند تا UI قدیمی در مرورگر باقی نماند.
- Mailpit از مسیر Same-Origin `/mailpit/` پشت Nginx ارائه می‌شود و پورت مستقیم 8025 میزبان حذف شده است.
- اسکریپت `auth_mailpit_smoke.py` مسیر کامل ثبت‌نام، خواندن OTP از همان Message ID، تأیید حساب، ورود با رمز و ورود OTP را اجرا می‌کند.
- نسخه Mailpit روی `v1.30.6` پین شده است.

## تست‌های انجام‌شده در بسته

- Compile و AST تمام فایل‌های Python
- `node --check app.js`
- Parse فایل Docker Compose با PyYAML
- Parse و تطابق OpenAPI/Postman با 66 عملیات ثبت‌شده
- تست استاتیک قرارداد Mailpit، Nginx و Transition فرم ثبت‌نام
- ممیزی ساختار تخت فایل‌ها و Checksum

اجرای واقعی Docker در محیط تولید بسته ممکن نبود. معیار نهایی روی سیستم مقصد این دستور است:

```powershell
docker compose --profile test run --rm auth-smoke
```

خروجی موفق باید `AUTH_MAILPIT_SMOKE=PASS` باشد.
