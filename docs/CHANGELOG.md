## 3.1.0 — Real Gmail SMTP OTP delivery

- Changed Docker email wiring from forced Mailpit delivery to environment-driven real SMTP, with Gmail (`smtp.gmail.com:587`, STARTTLS) as the default provider.
- Added `configure_gmail.py` for securely writing the Gmail address and Google App Password to a local ignored `.env`.
- Added `smtp_smoke.py` to send a harmless real-email test before exercising OTP flows.
- Kept Mailpit as an optional fallback via `python configure_gmail.py --mailpit`.
- Added provider-aware frontend messages: Gmail mode directs users to Inbox/Spam and hides Mailpit-only controls.
- Added Gmail configuration validation, app-password whitespace normalization, SMTP retry handling and cached transport health checks to avoid repeated provider authentication.
- Bumped Backend to 3.1.0 and Frontend to 1.7.0.

## 2026-08-04 — Wallet amount and searchable county controls

- Fixed manual wallet top-up values by removing the conflicting browser step constraint.
- Wallet amounts now accept Persian or English digits, with or without thousands separators.
- County fields in ticket filters, signup, and profile are now searchable by typing and support Arrow keys, Enter, and Escape.

## 2026-08-04 — Frontend 1.6.0: FA/EN language toggle restored


## 1.6.1 — Functional language toggle hotfix

- Fixed the Docker frontend image so `i18n.js` is actually copied into Nginx.
- Added a dedicated no-cache Nginx rule for `i18n.js`.
- Bumped the frontend image tag to `arenapass-frontend:1.6.1` to prevent reuse of the stale image.
- Bumped the translation runtime cache key in `index.html`.

- دکمه زبان در هدر، دقیقاً کنار دکمه روشن/تیره، دوباره اضافه شد.
- برچسب دکمه زبان فعلی را نشان می‌دهد: `FA` در رابط فارسی و `EN` در رابط انگلیسی.
- با هر کلیک، تمام منوها، عنوان‌ها، دکمه‌ها، فرم‌ها، پیام‌ها و محتوای پویای رابط بین فارسی و انگلیسی تغییر می‌کنند.
- جهت صفحه، عنوان مرورگر، Meta Description، فونت و چیدمان‌های وابسته به RTL/LTR هم‌زمان تغییر می‌کنند.
- زبان انتخاب‌شده در `localStorage` ذخیره می‌شود و پس از Refresh باقی می‌ماند.
- Runtime ترجمه `i18n.js` دوباره به `index.html` متصل و کنترل‌های LTR دسکتاپ و موبایل بهینه شدند.

## 2026-08-04 — Support reply UI refresh fix

- پاسخ پشتیبان بلافاصله پس از ارسال داخل همان رشته گفتگو نمایش داده می‌شود.
- حذف بازسازی کامل پنل پشتیبانی بعد از ارسال که باعث ناپدید شدن ظاهری پاسخ می‌شد.
- همگام‌سازی آرام پیام‌ها با سرور پس از ارسال، بدون حذف فرم پاسخ یا متن‌های در حال تایپ.
- به‌روزرسانی پیش‌نمایش آخرین پیام در فهرست گفتگوها.

## Frontend v1.5.4 — 2026-08-04

- دکمه تغییر زبان و بارگذاری Runtime ترجمه از رابط حذف شد.
- موشن فنری دکمه چت محسوس‌تر شد، بدون تغییر Scroll صفحه هنگام بستن چت.
- تنظیمات موشن در `SUPPORT_CHAT_MOTION_CONFIG` متمرکز شد تا شدت، دامنه، کشیدگی و زمان برگشت به‌سادگی قابل تغییر باشد.

## 1.5.3 - Language switch reliability fix
- Connected the FA/EN control directly inside `i18n.js`, independent of application initialization.
- Prevented duplicate language toggles by removing the secondary listener from `app.js`.
- Bumped frontend asset versions to force browsers and Docker/Nginx to load the corrected scripts.

# Changelog

## 2026-08-04 — Frontend 1.5.2: subtle chat drag and current-language label

- موشن ملایم و فنری دکمه چت هنگام اسکرول بازگردانده شد؛ افکت فقط با Transform روی خود دکمه اجرا می‌شود و Dock همچنان پایدار است.
- باگ پرش به بالای صفحه هنگام بستن چت همچنان برطرف است و Scroll و Focus بدون جابه‌جایی حفظ می‌شوند.
- کلید زبان اکنون فقط زبان فعلی را نشان می‌دهد: `FA` در حالت فارسی و `EN` در حالت انگلیسی.
- با تغییر زبان، منوها، تیترها، فرم‌ها، فیلترها، پنل کاربر، پنل پشتیبانی، چت، تاریخ‌ها و اعداد دوباره رندر و ترجمه می‌شوند.
- عنوان صفحه، توضیحات متا، جهت RTL/LTR و فونت رابط نیز هم‌زمان با زبان به‌روزرسانی می‌شوند.

## 2026-08-04 — Frontend 1.5.1: stable support chat and EN/FA interface

- حرکت دنبال‌کننده اسکرول از دکمه چت کاربر حذف شد و دکمه در موقعیتی ثابت و بدون موشن مزاحم قرار گرفت.
- باگ جابه‌جایی دکمه به بالای صفحه پس از بستن پنجره چت برطرف شد؛ موقعیت صفحه نیز هنگام بستن حفظ می‌شود.
- کلید دوحالته `EN / FA` کنار کلید روشن/تیره اضافه شد و انتخاب زبان در مرورگر ذخیره می‌شود.
- تمام متن‌های ثابت و پویا، فرم‌ها، خطاها، فیلترها، پنل کاربر، پنل پشتیبان و چت برای فارسی و انگلیسی پوشش داده شدند.
- جهت صفحه، فونت، تاریخ، ساعت، اعداد و چیدمان به‌صورت خودکار بین RTL و LTR تغییر می‌کند.
- نام شهرها و داده‌های فارسی ناشناخته در حالت انگلیسی به خط لاتین تبدیل می‌شوند تا هیچ بخش رابط کاربری فارسی باقی نماند.
- محتوای واقعی پیام‌های کاربران در چت ترجمه یا دست‌کاری نمی‌شود.
- چیدمان هدر در موبایل برای حضور هم‌زمان برند، `EN / FA`، پوسته، ورود و منوی موبایل بهینه شد.

## 2026-08-04 — Direct support chat

- چت خصوصی میان تماشاگر و پشتیبان با جداول `support_conversations` و `support_messages`، کنترل نقش در Trigger و Audit Log اضافه شد.
- پنل پشتیبان دارای صف گفتگوها، شمارنده پیام خوانده‌نشده، پاسخ، بستن و بازگشایی مکالمه شد.
- هفت عملیات جدید به Django، OpenAPI و Postman اضافه و تطابق قرارداد به ۶۶ عملیات ارتقا یافت.


## 2026-08-04 — Deterministic Mailpit OTP and signup UX fix

- Replaced local SMTP-only delivery with Mailpit HTTP Send API and message-ID persistence verification.
- Added fail-closed behavior: signup does not advance and OTP/cooldown are removed when email persistence fails.
- Moved Mailpit behind the same-origin Nginx path `/mailpit/` to eliminate stale host-port instances and port conflicts.
- Fixed signup UI transition so the verification form renders before Session Storage is touched; unavailable storage no longer blocks registration.
- Added safe same-origin mailbox URL handling and removed the stale `127.0.0.1:8025` frontend fallback.
- Added exact-message end-to-end smoke testing for signup, email OTP, password login and OTP login.
- Added exact-message buttons for both signup and OTP login, plus frontend cache-busting (`app.js?v=1.2.2`).
- Updated Mailpit to `v1.30.6` and refreshed authentication documentation and contract tests.

## 2026-08-03 — Authentication and Email OTP rebuild

- Rebuilt registration as a two-step verified flow; pending data lives in Redis and stores only a bcrypt hash, never plaintext password.
- Added signup OTP verification and resend endpoints, visible six-digit OTP forms, cooldown/countdown UI and Mailpit SMTP testing.
- Fixed frontend API discovery on custom host ports such as 8081 by always preferring the same-origin Nginx proxy.
- Added verified-contact metadata, password-login lockout, login timestamps, OTP HMAC/TTL/attempt limits and generic anti-enumeration responses.
- Kept rotating refresh-token families, session-version invalidation and role checks on every protected API.
- Added production SMTP validation, real SMTP examples, OpenAPI/Postman parity and authentication-specific contract tests.

## 2026-08-03 — Frontend integration hardening

- Added Dockerized Nginx frontend and same-origin `/api/v1` reverse proxy.
- Replaced hard-coded API base with runtime auto-discovery and readiness checks.
- Fixed mobile filter drawer, help routing, role-based account tabs, stale search races, and filter reset behavior.
- Synchronized support ticket form validation and amenity IDs with backend ticket invariants.
- Removed incompatible Compose `env_file` long syntax and made local defaults usable without shipping `.env`.
- Expanded CORS development origins and added frontend security headers.


## Frontend 1.0.0 - Complete vanilla client delivery

- Added a complete Persian RTL responsive SPA using only `index.html`, `styles.css`, and `app.js`.
- Added password/OTP/signup authentication, automatic JWT refresh, advanced ticket search, ticket detail and reservation flows.
- Added spectator account pages for reservations, bookings, payments, wallet, reports, profile, password and contact updates.
- Added support dashboards for reservation review, cancellations, seat changes, reports, suspicious payments, users and ticket administration.
- Added offline preview data, theme switching, API configuration, loaders, dialogs, toasts, error states and mobile filter drawer.
- Verified JavaScript syntax, OpenAPI path coverage, query-string routing, ticket quantity behavior, desktop rendering and mobile rendering.
- Added `FRONTEND_README.md`, `FRONTEND_VERIFICATION_REPORT.md` and preview images while preserving the flat delivery layout.
- Included the latest assignment revision `پروژه پایانی درس(15).pdf` without deleting files from the received backend package.

## 3.0.0 - Final audit hardening

- Removed runtime `.env` and duplicate environment sample from the delivery artifact.
- Replaced the bundled assignment PDF with the current provided revision.
- Hardened public match and seat-change visibility against inactive dependencies and canceled/completed match states.
- Added date-range validation to ticket search.
- Added API-level cross-field validation for numbered/general-admission tickets, sale windows, and capacity reductions.
- Made support ticket deletion reject unexpected query/body input.
- Regenerated delivery metadata and verification evidence.


## 3.0.0 — Final flat-delivery and zero-friction environment audit

- در نسخه‌های قبل فایل داک قدیمی‌تری بسته‌بندی شده بود؛ نسخه 3.0.0 آن را با `پروژه پایانی درس(14).pdf` جایگزین کرد.
- این تصمیم نسخه قدیمی در 3.0.0 لغو شد؛ فایل Runtime `.env` دیگر در تحویل قرار نمی‌گیرد.
- `env_file` در Docker Compose اختیاری شد؛ بنابراین نبود تصادفی `.env` باعث شکست مرحله Parse/Config نمی‌شود.
- ابزارهای مستقل `setup_env.py` و `delivery_audit.py` برای تولید امن تنظیمات و ممیزی Flat بودن، JSONها، Python، نسخه‌ها و Syntax محیط افزوده شدند.
- فایل‌های موقت `__pycache__` از تحویل حذف و آزمون‌های Contract برای پاکیزگی بسته و الزام حداقل ده رکورد در جداول تقویت شدند.
- نسخه سرویس، OpenAPI، Postman و Imageهای Docker روی `3.0.0` همگام شدند.

## 2.4.0 — Security, inventory and delivery audit hardening

- کنترل فروش مستقیم در توابع رزرو، پرداخت و تغییر صندلی برای Sport، هر دو Team و Ticket Category غیرفعال تکمیل شد؛ Trigger دیتابیس نیز همین قاعده را به‌صورت دفاع چندلایه اعمال می‌کند.
- غیرفعال‌کردن بلیط اکنون علاوه بر رزروهای موقت، Holdهای مقصد تغییر صندلی و Counterهای موجودی را قفل و بررسی می‌کند.
- چرخه وضعیت Report در Service با Trigger دیتابیس یکسان شد و بازگشت نامعتبر از `in_review` به `pending` پیش از رسیدن به دیتابیس رد می‌شود.
- Rate Limit مقدار واقعی TTL را در `Retry-After` برمی‌گرداند.
- Refresh Token Family دارای Redis Index مستقل شد تا Replay Response بدون Scan کامل Keyspace انجام شود؛ Fallback سازگار با نسخه‌های قدیمی حفظ شده است.
- Amenity IDها محدود، اعتبارسنجی و Deduplicate می‌شوند.
- احراز هویت Elasticsearch در Production فقط روی HTTPS مجاز است.
- Dependencyهای توسعه و Parser امن‌سازی شدند: `pytest==9.1.1` و `sqlparse==0.5.5`؛ Image جستجو به Elasticsearch `9.4.4` ارتقا یافت.
- داک رسمی تحویل با فایل `پروژه پایانی درس(12).pdf` همگام و نسخه بسته به 2.4.0 ارتقا یافت.


## 2.3.0 — Elasticsearch search backend and final synchronization hardening

- Backend اختیاری Elasticsearch برای API جستجوی بلیط اضافه شد؛ حالت PostgreSQL-only بدون تغییر مسیرهای API همچنان قابل اجراست.
- Strict Mapping، Full Rebuild دسته‌ای، Concrete Index و جابه‌جایی اتمیک Alias پیاده‌سازی شد.
- جدول `search_sync_outbox` با Revision، Retry نمایی، Claim مبتنی بر `FOR UPDATE SKIP LOCKED` و بازیابی Lock منقضی اضافه شد.
- یازده Trigger، تمام تغییرات مؤثر بر `v_ticket_catalog` را برای Sync صف می‌کنند؛ حذف Ticket نیز به حذف سند Search تبدیل می‌شود.
- Advisory Lock PostgreSQL از Race هم‌زمان Backend/Worker هنگام ساخت یا Rebuild Index جلوگیری می‌کند.
- Worker علاوه بر انقضای رزرو، Outbox جستجو و Full Reconciliation دوره‌ای را انجام می‌دهد.
- `docker-compose.yml` دارای Profile اختیاری `search` با Elasticsearch Pin‌شده و Volume/Healthcheck مستقل شد.
- Readiness و Preflight در حالت فعال، علاوه بر Reachability وجود Alias آماده را کنترل می‌کنند.
- SQL Fallback قابل تنظیم، Sync دستی، راهنمای کامل `ELASTICSEARCH.md` و تست‌های قراردادی Search اضافه شد.
- اعتبارسنجی Production برای URL، نام Index و تعارض روش‌های احراز هویت Elasticsearch سخت‌گیرانه شد.

## 2.2.0 — Final audited flat delivery

- نام شش اسکریپت اصلی SQL به نام‌های استاندارد و بدون پسوند آپلودی تغییر کرد و تمام ارجاعات Docker، تست و مستندات همگام شد.
- داک رسمی جدید پروژه با نام `پروژه پایانی درس(12).pdf` جایگزین نسخه قدیمی شد.
- وضعیت Readiness اکنون تنظیم `REDIS_REQUIRED` را دقیق رعایت می‌کند و اجباری/اختیاری‌بودن Redis را در پاسخ اعلام می‌کند.
- پارامترهای Query ناشناخته یا تکراری در تمام Endpointهای GET رد می‌شوند تا قرارداد API مبهم نباشد.
- پاسخ‌های 401 دارای `WWW-Authenticate: Bearer` و پاسخ‌های 429 دارای `Retry-After` شدند.
- هدر `X-API-Version` به همه پاسخ‌ها اضافه و نسخه سرویس در `version.py` متمرکز شد.
- `django.middleware.security.SecurityMiddleware` فعال شد تا `SECURE_SSL_REDIRECT` و تنظیمات HSTS واقعاً اجرا شوند.
- تغییر Contact پیش از مصرف OTP بررسی می‌کند که Login ترجیحی پس از تغییر واقعاً قابل استفاده باشد.
- جزئیات عمومی بلیط دیگر بلیط/مسابقه/تیم/برگزارکننده/ورزشگاه/رده غیرفعال یا مسابقه گذشته را نمایش نمی‌دهد؛ پشتیبان همچنان دید مدیریتی کامل دارد.
- View کاتالوگ، وضعیت فعال Sport، دو تیم، Organizer و Ticket Category را نیز حمل می‌کند تا Search و Detail از داده غیرفعال عبور نکنند.
- تکرار Payment موفق حتی پس از غیرفعال‌شدن روش پرداخت قبلی، همچنان Idempotent باقی می‌ماند.
- تست‌های Contract و Validator برای نام‌های استاندارد، نسخه، Query Contract و کنترل‌های جدید به‌روزرسانی شدند.

## 2.1.0

- JWT session versioning، Refresh rotation/replay detection، OTP HMAC، Audit Log، Support review/correction، Docker hardening، OpenAPI/Postman parity و Integration Test تکمیل شد.

## 2026-08-03 — PostgreSQL bootstrap correction

- Assigned explicit deterministic IDs to the 47 reservation seed rows before dependent seed records are inserted.
- Fixed the `Seat-change requester must own reservation` failure caused by non-deterministic `INSERT ... SELECT ... JOIN` row order.
- Added `99_bootstrap_complete.sql` and changed the PostgreSQL healthcheck to require its completion marker.
- Prevented backend, worker, and frontend services from starting against a partially initialized database.
## 2026-08-04 — Ticket team-name readability

- Reworked ticket-card team rows into balanced home / versus / away columns.
- Added two-line wrapping and automatic font scaling for long team names.
- Increased the card header space and repositioned the availability badge.
- Added English-specific typography, mobile adjustments, and full-name tooltips.
- Prevented long tournament names from displacing the matchup row.