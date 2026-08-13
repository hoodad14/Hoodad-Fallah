# گزارش ممیزی و تکمیل بک‌اند ArenaPass

## دامنه بررسی

مبنای ممیزی شامل داک ۲۴صفحه‌ای پروژه، هفت فایل SQL شامل Schema، Seed، Query، Function، Validation و Extension بک‌اند، ۵۱ Route Django، ۶۶ عملیات HTTP، Redis، Docker، مستندات و تست‌ها بوده است.

## نتیجه کلی

معماری اولیه از نظر انتخاب Django بدون ORM، PostgreSQL Raw SQL، Redis و تفکیک Serviceها مناسب بود؛ اما چند نقص می‌توانست در تحویل عملی موجب ایراد جدی شود. نسخه 3.0.0 این موارد را اصلاح کرده و بسته را به یک تحویل Flat، قابل‌اجرا، قابل‌ممیزی و مستند تبدیل می‌کند.

## سخت‌سازی نهایی نسخه 3.0.0

در ممیزی نهایی، چند مسیر دورزدن منطق فروش و موجودی اصلاح شد: فعال‌بودن Sport، تیم میزبان/میهمان و Ticket Category اکنون در رزرو، پرداخت، تغییر صندلی و Trigger دفاعی دیتابیس بررسی می‌شود؛ پنجره فروش مقصد تغییر صندلی نیز رعایت می‌شود. غیرفعال‌سازی Ticket دیگر با PATCH یا در حضور Hold رزرو/تغییر صندلی قابل دورزدن نیست. علاوه بر آن، Rate Limit دارای Retry-After دقیق، Refresh Family دارای Redis Index، چرخه Report همگام با Trigger و پیکربندی Elasticsearch دارای الزام HTTPS هنگام استفاده از Credential است.

این ممیزی تضمین ریاضی «بی‌خطایی مطلق» نیست؛ تأیید نهایی اجرای زنده باید با Docker، PostgreSQL، Redis و در صورت فعال‌بودن Search با Elasticsearch روی سیستم مقصد انجام شود. جزئیات کنترل‌های انجام‌شده و محدودیت محیط در `VERIFICATION_REPORT.txt` ثبت شده است.


## جمع‌بندی ممیزی نهایی v3.0.0

در آخرین پاس، علاوه بر کنترل‌های قبلی، سه ایراد تحویلی و چند شکاف اعتبارسنجی بسته شد: فایل Secret محلی از ZIP حذف شد، داک داخل بسته با نسخه `(14)` همگام شد، Visibility مسابقات و مقصد تغییر صندلی سخت‌گیرانه‌تر شد، بازه تاریخ جستجو اعتبارسنجی شد و Invariantهای Ticket شماره‌دار/آزاد و ظرفیت در سطح API نیز پیش از Constraint دیتابیس کنترل می‌شوند.

ارزیابی مبتنی بر فایل نشان می‌دهد پوشش فاز بک‌اند بسیار بالا است. بااین‌حال نمره کامل نهایی همچنان به اجرای موفق Stack روی لپ‌تاپ، ارائه Responseهای واقعی، اسکرین‌شات‌ها و سابقه Git خواسته‌شده در داک وابسته است؛ این موارد را ZIP به‌تنهایی اثبات نمی‌کند.

## ایرادهای مهم شناسایی‌شده و اصلاح‌شده

### 1. عدم تطابق نام فایل‌های SQL

فایل‌های SQL دارای پسوند آپلودی `(6)` بودند و ظاهر تحویل، Mountهای Docker و ارجاعات تست را شکننده می‌کردند. نام‌ها به `00_schema.sql` تا `05_validation_tests.sql` استاندارد شدند و همه Mountها، مستندات، تست‌ها و Manifest با آن‌ها همگام شدند.

### 2. نشست‌های معتبر پس از تغییر رمز

در نسخه قبلی، تغییر رمز الزاماً Access/Refresh Tokenهای قبلی را بی‌اعتبار نمی‌کرد. ستون `session_version` اضافه شد، Claim `sv` وارد JWT شد و تغییر رمز/Contact تمام Sessionهای قدیمی را باطل می‌کند.

### 3. مدیریت Refresh Token

Rotation، ثبت JTI، Index کاربر، تشخیص Replay، ابطال Family و Logout کامل‌تر شد. Refresh Token مصرف‌شده دیگر قابل استفاده نیست.

### 4. Cache موجودی پس از انقضا

اگر انقضا توسط مسیرهای API انجام می‌شد، ممکن بود Ticket Search برای مدت TTL موجودی قدیمی نشان دهد. اکنون هر آزادسازی موجودی، Version Cache را افزایش می‌دهد.

### 5. OTP و ارسال واقعی

OTP از JWT Secret جدا شد، HMAC-only Storage، مصرف اتمیک، Rate Limit و حذف OTP در شکست ارسال اعمال شد. Email و Webhook عمومی SMS پشتیبانی می‌شوند.

### 6. Input Contract و Mass Assignment

Bodyهای JSON اکنون Fieldهای ناشناخته را رد می‌کنند. URL، Boolean، DateTime دارای Timezone، Range و Length سخت‌گیرانه بررسی می‌شوند.

### 7. مستندات API

OpenAPI قبلی Status Codeهای `201/202` را عمدتاً `200` مستند کرده و Schemaهای ورودی آزاد داشت. OpenAPI 3.1 با رفتار واقعی همگام شد. Postman نیز متغیرها، Placeholderها و Scriptهای Capture Token/ID را دریافت کرد.

### 8. Startup مبهم

Entrypoint و `preflight.py` اکنون اتصال سرویس‌ها، جدول‌ها، ستون امنیت نشست و Functionهای ضروری را Fail-fast بررسی می‌کنند. Volume قدیمی با پیام مشخص قابل تشخیص است.

### 9. Docker Hardening

اجرای Non-root، Read-only Filesystem، Cap Drop، no-new-privileges، Healthcheck، Graceful Shutdown و Worker مستقل اعمال شد.

### 10. پوشش ناقص تأیید/اصلاح رزرو توسط پشتیبان

داک صریحاً تأیید، لغو و اصلاح رزرو را برای پشتیبان الزام کرده بود. لغو وجود داشت، اما تأیید پایدار و اصلاح مستقیم امن وجود نداشت. فیلدهای Review به Extension افزوده شد و دو API مجزا برای تأیید/Flag و Seat Correction از طریق Workflow تراکنشی Seat Change ایجاد شد.

### 11. تغییر رمز بدون عامل دوم

تغییر رمز اکنون علاوه بر JWT و رمز فعلی، OTP یک‌بارمصرف Contact ترجیحی را نیز نیاز دارد و سپس همه Sessionهای قدیمی را باطل می‌کند.

### 12. تست ناکافی

تست قراردادی اکنون تطبیق دقیق ۶۶ عملیات Django/OpenAPI/Postman، نبود ORM، فایل‌ها، Functionها و Security Contract را بررسی می‌کند. Integration Test کامل نیز اضافه شده است.

### 13. قرارداد سخت‌گیرانه Query String

علاوه بر Body، پارامترهای Query ناشناخته و کلیدهای تکراری نیز رد می‌شوند. این کار از رفتار مبهم میان Proxy، مرورگر و Django جلوگیری می‌کند و اشتباه تایپی در فیلترها را بی‌صدا نادیده نمی‌گیرد.

### 14. Visibility صحیح کاتالوگ

View کاتالوگ اکنون Active بودن Sport، دو تیم، Organizer، Venue، Match و Ticket Category را مستقل نگه می‌دارد. Search و Ticket Detail عمومی داده غیرفعال یا مسابقه گذشته را نمایش نمی‌دهند، در حالی که API پشتیبان همچنان دید مدیریتی کامل دارد.

### 15. Readiness و استانداردهای HTTP

Readiness تنظیم `REDIS_REQUIRED` را رعایت می‌کند. پاسخ‌های 401 دارای `WWW-Authenticate`، پاسخ‌های 429 دارای `Retry-After` و همه پاسخ‌ها دارای `X-API-Version` هستند. همچنین `SecurityMiddleware` رسمی Django فعال شده تا `SECURE_SSL_REDIRECT` و HSTS برخلاف قبل صرفاً تنظیمات بی‌اثر نباشند.

### 16. Idempotency پرداخت

نتیجه Payment موفق قبل از بررسی فعال‌بودن روش پرداخت بازگردانده می‌شود؛ بنابراین Retry معتبر حتی اگر روش پرداخت اولیه بعداً غیرفعال شده باشد، نتیجه موفق قبلی را از دست نمی‌دهد.

### 17. ایمنی تغییر Contact

پیش از مصرف OTP بررسی می‌شود که `preferred_login` انتخاب‌شده پس از تغییر واقعاً Contact متناظر داشته باشد؛ خطای Constraint مبهم به Validation روشن تبدیل شده است.

### 18. نبود موتور جستجوی فاز چهارم و خطر ناسازگاری SQL/Elastic

داک تصریح کرده بود که API جستجو در فاز چهارم به Elasticsearch متصل شود و داده‌های SQL و Search Engine همگام بمانند. نسخه نهایی یک حالت اختیاری کامل اضافه می‌کند: Strict Mapping، جستجوی متنی/Prefix/Fuzzy، Alias اتمیک، Full Rebuild Batch شده، Transactional Outbox، Revision، Claim با `SKIP LOCKED`، Retry نمایی و SQL Fallback. Triggerهای تمام موجودیت‌های مؤثر بر `v_ticket_catalog`، شناسه بلیط را Queue می‌کنند و Advisory Lock از Race دو Rebuild هم‌زمان جلوگیری می‌کند.

## پوشش نیازمندی‌های داک

| نیازمندی | وضعیت | محل اصلی |
|---|---|---|
| Django Backend | کامل | `views.py`, `services_*.py` |
| عدم استفاده از ORM | کامل | `database.py`, تست Contract |
| PostgreSQL مستقیم | کامل | `database.py`, SQL Functionها |
| Redis OTP/Cache | کامل | `cache.py`, `authentication.py` |
| JWT + Role | کامل | `authentication.py` |
| Signup/Login/OTP | کامل | `services_auth.py` |
| Profile | کامل | `views.py`, `services_auth.py` |
| City/Venue Lookup | کامل | `services_catalog.py` |
| Advanced Search | کامل | PostgreSQL + `search_engine.py` |
| Ticket Detail | کامل | `services_catalog.ticket_detail` |
| Hold محدود و انقضا | کامل | `reserve_ticket`, `worker.py` |
| Payment محلی | کامل | `process_payment` |
| History/Bookings | کامل | `services_reservations.py` |
| Cancellation/Refund | کامل | SQL + Support API |
| Seat Change | کامل | SQL + User/Support API |
| Reports | کامل | User/Support API |
| Support Management | کامل | `services_support.py` |
| API Documentation | کامل | OpenAPI + Postman |
| Elasticsearch Backend | کامل و اختیاری | Search Profile + Outbox + Worker |
| Docker | کامل | Compose + Dockerfile |
| تست | کامل در بسته | Unit/Contract/Smoke/Integration |

## مرز ادعا

در محیط ساخت این خروجی، Docker daemon، PostgreSQL، Redis، Elasticsearch و Package Index قابل استفاده نبودند؛ بنابراین اجرای واقعی Containerها و Integration Test در همان محیط انجام نشد. در عوض Parse/Compile، Preflight Static، JSON، Shell، Route/API parity و کنترل‌های قراردادی اجرا شده‌اند. اجرای زنده نهایی باید روی سیستم مقصد با دستورهای `TESTING.md` انجام شود.
