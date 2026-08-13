# کنترل‌های امنیتی ArenaPass Backend

## Database و Query

- هیچ Django ORM استفاده نشده است؛ عملیات پایدار از طریق SQL پارامتری `psycopg` انجام می‌شود.
- Dynamic SQL فقط برای Column و Orderingهای Allow-listشده سمت سرور ساخته می‌شود.
- رمزها با `pgcrypto` و bcrypt (`crypt`/`gen_salt`) ذخیره می‌شوند.
- عملیات موجودی و مالی در Stored Functionهای تراکنشی و Isolation مناسب اجرا می‌شوند.
- Constraintها، Triggerهای Deferred و Counterهای کنترل‌شده مانع Overselling و Drift می‌شوند.

## Authentication و Session

- Access Token کوتاه‌عمر و Refresh Token چرخشی با `iss`, `aud`, `jti`, `type`, `role`, `sv`.
- Refresh Tokenها در Redis ثبت و پس از Rotation مصرف می‌شوند.
- استفاده مجدد از Refresh Token باعث ابطال Family می‌شود.
- تغییر رمز نیازمند Access Token، رمز فعلی و OTP است؛ سپس `session_version` افزایش یافته و تمام نشست‌ها/Refresh Tokenهای قبلی باطل می‌شوند.
- تغییر Contact نیز OTP دارد و تمام نشست‌های قبلی را باطل می‌کند.
- نقش و فعال‌بودن حساب در هر درخواست احراز‌شده از دیتابیس زنده کنترل می‌شود.
- Logout، Access Token را تا پایان عمر در Blacklist قرار می‌دهد و Refresh Token را حذف می‌کند.

## OTP

- کد شش‌رقمی با مولد رمزنگاری امن ساخته می‌شود.
- فقط HMAC کد در Redis ذخیره می‌شود؛ Secret OTP از JWT جداست.
- TTL، Rate Limit بر Contact/IP، محدودیت تلاش و مصرف اتمیک یک‌باره اعمال می‌شود.
- در Production بازگرداندن Debug Code ممنوع است؛ SMTP باید TLS/SSL داشته باشد و تنظیم هم‌زمان TLS و SSL رد می‌شود.
- Email از Backend استاندارد Django و SMS از Webhook عمومی HTTPS پشتیبانی می‌شود. اجرای Local از Mailpit استفاده می‌کند و Email واقعی از محیط توسعه خارج نمی‌شود.
- ورود با رمز دارای Rate Limit و قفل موقت حساب بر اساس Fingerprint راه ارتباطی است؛ پیام خطا Contact موجود و ناموجود را تفکیک نمی‌کند.
- Refresh Token چرخشی و یک‌بارمصرف است، استفاده مجدد باعث ابطال Token Family می‌شود و Role/Session Version در هر درخواست دوباره کنترل می‌گردد.

## HTTP و Input

- فقط JSON Object پذیرفته می‌شود؛ Duplicate Key و Field ناشناخته رد می‌شود.
- محدودیت اندازه Body پیش‌فرض ۲ MiB است.
- Type/Range/Length/Date/URLها اعتبارسنجی می‌شوند.
- پاسخ خطا جزئیات داخلی Stack یا SQL را افشا نمی‌کند.
- Request ID، CORS Allow-list، Security Headers، Referrer Policy و Rate Limit فعال‌اند.
- IP Forwarded فقط زمانی پذیرفته می‌شود که `TRUST_PROXY_HEADERS=true` باشد.

## Audit و Cache

- تغییرات حساس در `api_audit_log` با Actor، Resource، IP، Request ID و Metadata ثبت می‌شوند.
- Profile Cache پس از تغییر پاک می‌شود.
- Ticket Cache با Version Invalidation پس از رزرو، پرداخت، انقضا، Refund یا تغییر Catalog باطل می‌شود.
- JSON خراب Redis حذف و از دیتابیس بازسازی می‌شود.

## Elasticsearch و همگام‌سازی جستجو

- PostgreSQL منبع حقیقت است و Triggerها فقط Outbox تراکنشی ایجاد می‌کنند؛ هیچ HTTP خارجی داخل Transaction اصلی اجرا نمی‌شود.
- Worker با Revision، Lock منقضی‌شونده، `SKIP LOCKED` و Retry نمایی از گم‌شدن یا پردازش هم‌زمان تغییرات جلوگیری می‌کند.
- Full Rebuild روی Concrete Index جدید انجام و Alias اتمیک جابه‌جا می‌شود؛ Advisory Lock مانع Race چند Rebuild است.
- Mapping به‌صورت `dynamic: strict` است تا فیلد ناخواسته وارد Index نشود.
- Container محلی Elasticsearch احراز هویت داخلی را فقط برای Development خاموش می‌کند و پورت آن روی `127.0.0.1` Bind است. در Production باید TLS و Authentication یا سرویس مدیریت‌شده فعال باشد.
- API Key و Basic Auth هم‌زمان پذیرفته نمی‌شوند و Secretها نباید در Git ثبت شوند.

## Container

- Backend/Worker با User غیر Root اجرا می‌شوند.
- Filesystem آن‌ها Read-only، Capabilityها حذف و `no-new-privileges` فعال است.
- PostgreSQL و Redis فقط روی `127.0.0.1` Host Bind می‌شوند.
- Healthcheck و Graceful Shutdown برای سرویس‌ها تعریف شده است.

## چک‌لیست Production

1. `DEBUG=false`
2. سه Secret مستقل و تصادفی حداقل ۳۲ کاراکتری تنظیم شود.
3. `OTP_DEBUG_RETURN_CODE=false`
4. `ALLOW_LOCAL_WALLET_TOP_UP=false`
5. Email/SMS واقعی و TLS فعال شود.
6. TLS Termination و شبکه خصوصی PostgreSQL/Redis/Elasticsearch استفاده شود.
7. `ALLOWED_HOSTS` و `CORS_ALLOWED_ORIGINS` دقیق محدود شوند.
8. Backup، Rotation لاگ و Monitoring سرویس‌ها فعال شود.
9. `TRUST_PROXY_HEADERS=true` فقط پشت Proxy مورد اعتماد که Headerها را بازنویسی می‌کند.
10. `.env` هرگز Commit نشود.
11. کاربر دیتابیس Production حداقل دسترسی لازم را داشته باشد.
12. Secretها در Secret Manager نگهداری و دوره‌ای Rotate شوند.
13. Rate Limit لبه شبکه/WAF نیز در کنار Rate Limit برنامه فعال شود.
14. Integration Test روی محیط Staging و نه Production اجرا شود.
15. در صورت فعال‌بودن Elasticsearch، TLS/Auth، محدودسازی شبکه، Alert برای Outbox معوق و اجرای دائمی Worker کنترل شود.
