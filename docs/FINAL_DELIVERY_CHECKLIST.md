# چک‌لیست نهایی تحویل MahTicket

## ۱. ساخت فایل محیطی محلی

فایل `.env` عمداً داخل ZIP نیست. در همان پوشه پروژه اجرا کنید:

```bash
python setup_env.py
```

برای Production تمام Secretهای نمونه را عوض کنید و `.env` را Commit نکنید.

## ۲. اجرای تمیز Docker

حالت استاندارد فاز بک‌اند:

```bash
docker compose down -v
docker compose up --build -d
```

حالت کامل Elasticsearch:

```bash
docker compose --profile search down -v
docker compose --profile search up --build -d
```

## ۳. بررسی سلامت

```bash
docker compose ps
docker compose logs --tail=200 db redis backend worker
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/ready
```

در Readiness باید `database=true` و `redis=true` باشد. در حالت Search، `elasticsearch=true` و `elasticsearch_index_ready=true` نیز لازم است.

## ۴. اجرای تست‌ها

```bash
python delivery_audit.py
docker compose exec backend python -m pytest -q
docker compose exec backend python preflight.py
docker compose exec backend python smoke_test.py
python integration_test.py --base-url http://127.0.0.1:8000 --yes-destructive
```

Integration Test داده‌نویس است و فقط روی دیتابیس Local/CI تمیز اجرا شود.

## ۵. تست Postman و شواهد ارائه

فایل `ArenaPass.postman_collection.json` را Import کنید و حداقل این مسیرها را اجرا و از Response JSON اسکرین‌شات بگیرید: Signup، OTP، Login، Search، Ticket Detail، Reserve، Pay، Bookings، Cancellation/Refund، Report و Support Management.

برای نشان‌دادن انقضای رزرو، یک Hold بسازید و آزادشدن موجودی توسط Worker را در Log و API نمایش دهید.

## ۶. نکات دفاع در ارائه

- Django فقط لایه HTTP است؛ ORM استفاده نشده و SQLها مستقیم و پارامتری‌اند.
- رزرو، پرداخت، کنسلی و تغییر صندلی در PostgreSQL و داخل Transaction/Lock انجام می‌شوند.
- Redis برای OTP، Cache، Rate Limit و وضعیت Token استفاده می‌شود.
- PostgreSQL منبع حقیقت است؛ Elasticsearch فقط Index جستجو و اختیاری است.
- پرداخت بانکی واقعی طبق داک لازم نیست و `local_gateway` شبیه‌ساز محلی است.
- فایل `05_validation_tests.sql` حداقل 10 رکورد برای جداول پایدار و سازگاری موجودی/مالی را هنگام Init بررسی می‌کند.

## ۷. الزام Git که ZIP جایگزین آن نیست

تاریخچه واقعی Branch، Pull Request و حداقل Commitهای معنادار هر فاز باید در GitHub موجود باشد. ZIP نمی‌تواند این بخش نمره را ثابت کند. راهنمای عملی در `GIT_DELIVERY_GUIDE.md` قرار دارد.

## ۸. کنترل سلامت فایل تحویلی

```bash
python delivery_audit.py
```

`SHA256SUMS.txt` و `PROJECT_MANIFEST.txt` را همراه بسته نگه دارید.
