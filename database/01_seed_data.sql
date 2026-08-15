
BEGIN;
-- 10+ rows per table


CREATE TEMP TABLE seed_clock ON COMMIT DROP AS
SELECT
    CURRENT_TIMESTAMP AS now_ts,
    date_trunc('day', CURRENT_TIMESTAMP) AS today_start,
    date_trunc('day', CURRENT_TIMESTAMP) - INTERVAL '1 day' AS yesterday_start;

INSERT INTO provinces (name) VALUES
('تهران'),
('اصفهان'),
('فارس'),
('البرز'),
('آذربایجان شرقی'),
('یزد'),
('کرمان'),
('خراسان رضوی'),
('خوزستان'),
('مازندران'),
('مرکزی'),
('گیلان'),
('آذربایجان غربی'),
('کرمانشاه'),
('سیستان و بلوچستان'),
('کردستان'),
('همدان'),
('چهارمحال و بختیاری'),
('لرستان'),
('ایلام'),
('کهگیلویه و بویراحمد'),
('بوشهر'),
('زنجان'),
('سمنان'),
('هرمزگان'),
('اردبیل'),
('قم'),
('قزوین'),
('گلستان'),
('خراسان شمالی'),
('خراسان جنوبی');

INSERT INTO cities (province_id, name) VALUES
(1, 'تهران'),
(1, 'ری'),
(1, 'شمیرانات'),
(2, 'اصفهان'),
(2, 'کاشان'),
(2, 'نجف‌آباد'),
(3, 'شیراز'),
(3, 'مرودشت'),
(3, 'جهرم'),
(4, 'کرج'),
(5, 'تبریز'),
(6, 'یزد'),
(7, 'کرمان'),
(8, 'مشهد'),
(9, 'اهواز'),
(9, 'آبادان'),
(10, 'ساری'),
(10, 'بابل'),
(2, 'لنجان'),
(1, 'قدس');

INSERT INTO cities (id, province_id, name) VALUES
(1000001, 11, 'اراک'),
(1000002, 11, 'آشتیان'),
(1000003, 11, 'تفرش'),
(1000004, 11, 'خمین'),
(1000005, 11, 'دلیجان'),
(1000006, 11, 'ساوه'),
(1000007, 11, 'شازند'),
(1000009, 11, 'محلات'),
(1010001, 12, 'آستارا'),
(1010002, 12, 'آستانه اشرفیه'),
(1010003, 12, 'بندرانزلی'),
(1010004, 12, 'طوالش'),
(1010005, 12, 'رشت'),
(1010006, 12, 'رودبار'),
(1010007, 12, 'رودسر'),
(1010008, 12, 'صومعه سرا'),
(1010009, 12, 'فومن'),
(1020001, 10, 'آمل'),
(1020004, 10, 'بهشهر'),
(1020005, 10, 'تنکابن'),
(1020006, 10, 'رامسر'),
(1020008, 10, 'سوادکوه'),
(1030002, 5, 'اهر'),
(1030005, 5, 'سراب'),
(1030006, 5, 'مراغه'),
(1030007, 5, 'مرند'),
(1040001, 13, 'ارومیه'),
(1040002, 13, 'پیرانشهر'),
(1040003, 13, 'خوی'),
(1040004, 13, 'سردشت'),
(1040005, 13, 'سلماس'),
(1040006, 13, 'ماکو'),
(1040007, 13, 'مهاباد'),
(1040008, 13, 'میاندوآب'),
(1040009, 13, 'نقده'),
(1050001, 14, 'اسلام آبادغرب'),
(1050002, 14, 'کرمانشاه'),
(1050003, 14, 'پاوه'),
(1050004, 14, 'سرپل ذهاب'),
(1050005, 14, 'سنقر'),
(1050006, 14, 'قصرشیرین'),
(1050007, 14, 'کنگاور'),
(1050008, 14, 'گیلانغرب'),
(1050009, 14, 'جوانرود'),
(1060002, 9, 'اندیمشک'),
(1060004, 9, 'ایذه'),
(1060005, 9, 'بندرماهشهر'),
(1060006, 9, 'بهبهان'),
(1060007, 9, 'خرمشهر'),
(1060008, 9, 'دزفول'),
(1060009, 9, 'دشت آزادگان'),
(1070001, 3, 'آباده'),
(1070002, 3, 'استهبان'),
(1070003, 3, 'اقلید'),
(1070005, 3, 'داراب'),
(1070006, 3, 'سپیدان'),
(1070008, 3, 'فسا'),
(1070009, 3, 'فیروزآباد'),
(1080001, 7, 'بافت'),
(1080002, 7, 'بم'),
(1080003, 7, 'جیرفت'),
(1080004, 7, 'رفسنجان'),
(1080005, 7, 'زرند'),
(1080006, 7, 'سیرجان'),
(1080007, 7, 'شهربابک'),
(1080009, 7, 'کهنوج'),
(1090004, 8, 'تایباد'),
(1090005, 8, 'تربت حیدریه'),
(1090006, 8, 'تربت جام'),
(1090007, 8, 'درگز'),
(1090008, 8, 'سبزوار'),
(1100001, 2, 'اردستان'),
(1100003, 2, 'خمینی شهر'),
(1100004, 2, 'خوانسار'),
(1100005, 2, 'سمیرم'),
(1100006, 2, 'فریدن'),
(1100007, 2, 'فریدونشهر'),
(1100008, 2, 'فلاورجان'),
(1100009, 2, 'شهرضا'),
(1110001, 15, 'ایرانشهر'),
(1110002, 15, 'چاه بهار'),
(1110003, 15, 'خاش'),
(1110004, 15, 'زابل'),
(1110005, 15, 'زاهدان'),
(1110006, 15, 'سراوان'),
(1110007, 15, 'نیک شهر'),
(1110008, 15, 'راسک'),
(1110009, 15, 'کنارک'),
(1120001, 16, 'بانه'),
(1120002, 16, 'بیجار'),
(1120003, 16, 'سقز'),
(1120004, 16, 'سنندج'),
(1120005, 16, 'قروه'),
(1120006, 16, 'مریوان'),
(1120007, 16, 'دیواندره'),
(1120008, 16, 'کامیاران'),
(1120009, 16, 'سروآباد'),
(1130001, 17, 'تویسرکان'),
(1130002, 17, 'ملایر'),
(1130003, 17, 'نهاوند'),
(1130004, 17, 'همدان'),
(1130005, 17, 'کبودرآهنگ'),
(1130006, 17, 'اسدآباد'),
(1130007, 17, 'بهار'),
(1130008, 17, 'رزن'),
(1130009, 17, 'فامنین'),
(1140001, 18, 'بروجن'),
(1140002, 18, 'شهرکرد'),
(1140003, 18, 'فارسان'),
(1140004, 18, 'لردگان'),
(1140005, 18, 'اردل'),
(1140006, 18, 'کوهرنگ'),
(1140007, 18, 'کیار'),
(1140008, 18, 'سامان'),
(1140009, 18, 'بن'),
(1150001, 19, 'الیگودرز'),
(1150002, 19, 'بروجرد'),
(1150003, 19, 'خرم آباد'),
(1150004, 19, 'دلفان'),
(1150005, 19, 'دورود'),
(1150006, 19, 'کوهدشت'),
(1150007, 19, 'ازنا'),
(1150008, 19, 'پلدختر'),
(1150009, 19, 'سلسله'),
(1160001, 20, 'ایلام'),
(1160002, 20, 'دره شهر'),
(1160003, 20, 'دهلران'),
(1160004, 20, 'چرداول'),
(1160005, 20, 'مهران'),
(1160006, 20, 'آبدانان'),
(1160007, 20, 'ایوان'),
(1160008, 20, 'ملکشاهی'),
(1160009, 20, 'سیروان'),
(1170001, 21, 'بویراحمد'),
(1170002, 21, 'کهگیلویه'),
(1170003, 21, 'گچساران'),
(1170004, 21, 'دنا'),
(1170005, 21, 'بهمیی'),
(1170006, 21, 'چرام'),
(1170007, 21, 'باشت'),
(1170008, 21, 'لنده'),
(1170009, 21, 'مارگون'),
(1180001, 22, 'بوشهر'),
(1180002, 22, 'تنگستان'),
(1180003, 22, 'دشتستان'),
(1180004, 22, 'دشتی'),
(1180005, 22, 'دیر'),
(1180006, 22, 'کنگان'),
(1180007, 22, 'گناوه'),
(1180008, 22, 'دیلم'),
(1180009, 22, 'جم'),
(1190001, 23, 'ابهر'),
(1190003, 23, 'خدابنده'),
(1190004, 23, 'زنجان'),
(1190006, 23, 'ایجرود'),
(1190007, 23, 'خرمدره'),
(1190008, 23, 'طارم'),
(1190009, 23, 'ماهنشان'),
(1200001, 24, 'دامغان'),
(1200002, 24, 'سمنان'),
(1200003, 24, 'شاهرود'),
(1200004, 24, 'گرمسار'),
(1200005, 24, 'مهدی شهر'),
(1200006, 24, 'آرادان'),
(1200007, 24, 'میامی'),
(1200008, 24, 'سرخه'),
(1210001, 6, 'اردکان'),
(1210002, 6, 'بافق'),
(1210003, 6, 'تفت'),
(1210004, 6, 'مهریز'),
(1210006, 6, 'میبد'),
(1210007, 6, 'ابرکوه'),
(1210008, 6, 'اشکذر'),
(1210009, 6, 'خاتم'),
(1220001, 25, 'ابوموسی'),
(1220002, 25, 'بندر عباس'),
(1220003, 25, 'بندر لنگه'),
(1220004, 25, 'قشم'),
(1220005, 25, 'میناب'),
(1220006, 25, 'جاسک'),
(1220007, 25, 'رودان'),
(1220008, 25, 'حاجی آباد'),
(1220009, 25, 'بستک'),
(1230002, 1, 'دماوند'),
(1230006, 1, 'ورامین'),
(1230009, 1, 'شهریار'),
(1240001, 26, 'اردبیل'),
(1240002, 26, 'بیله سوار'),
(1240003, 26, 'خلخال'),
(1240004, 26, 'مشگین شهر'),
(1240005, 26, 'گرمی'),
(1240006, 26, 'پارس آباد'),
(1240007, 26, 'کوثر'),
(1240008, 26, 'نمین'),
(1240009, 26, 'نیر'),
(1250001, 27, 'قم'),
(1250002, 27, 'جعفرآباد'),
(1250003, 27, 'کهک'),
(1260001, 28, 'بویین زهرا'),
(1260002, 28, 'تاکستان'),
(1260003, 28, 'قزوین'),
(1260004, 28, 'آبیک'),
(1260005, 28, 'البرز'),
(1260006, 28, 'آوج'),
(1270001, 29, 'بندرگز'),
(1270002, 29, 'ترکمن'),
(1270003, 29, 'علی آباد کتول'),
(1270004, 29, 'کردکوی'),
(1270005, 29, 'گرگان'),
(1270006, 29, 'گنبدکاووس'),
(1270007, 29, 'مینودشت'),
(1270008, 29, 'آق قلا'),
(1270009, 29, 'کلاله'),
(1280001, 30, 'اسفراین'),
(1280002, 30, 'بجنورد'),
(1280003, 30, 'جاجرم'),
(1280004, 30, 'شیروان'),
(1280005, 30, 'فاروج'),
(1280006, 30, 'سملقان'),
(1280007, 30, 'گرمه'),
(1280008, 30, 'راز و جرگلان'),
(1280009, 30, 'بام و صفی آباد'),
(1290001, 31, 'بیرجند'),
(1290002, 31, 'درمیان'),
(1290003, 31, 'سربیشه'),
(1290004, 31, 'قاینات'),
(1290005, 31, 'نهبندان'),
(1290006, 31, 'سرایان'),
(1290007, 31, 'فردوس'),
(1290008, 31, 'بشرویه'),
(1290009, 31, 'زیرکوه'),
(1300002, 4, 'ساوجبلاغ'),
(1300003, 4, 'نظرآباد'),
(1300004, 4, 'طالقان'),
(1300005, 4, 'اشتهارد'),
(1300006, 4, 'فردیس'),
(1300007, 4, 'چهارباغ'),
(10000010, 11, 'زرندیه'),
(10000011, 11, 'کمیجان'),
(10000012, 11, 'خنداب'),
(10000013, 11, 'فراهان'),
(10100010, 12, 'لنگرود'),
(10100011, 12, 'لاهیجان'),
(10100012, 12, 'شفت'),
(10100013, 12, 'املش'),
(10100014, 12, 'رضوانشهر'),
(10100015, 12, 'سیاهکل'),
(10100016, 12, 'ماسال'),
(10100017, 12, 'خمام'),
(10200010, 10, 'قایم شهر'),
(10200014, 10, 'نور'),
(10200015, 10, 'نوشهر'),
(10200016, 10, 'بابلسر'),
(10200018, 10, 'محمودآباد'),
(10200019, 10, 'نکا'),
(10200020, 10, 'چالوس'),
(10200021, 10, 'جویبار'),
(10200022, 10, 'گلوگاه'),
(10200023, 10, 'فریدونکنار'),
(10200024, 10, 'عباس آباد'),
(10200025, 10, 'میاندورود'),
(10200026, 10, 'سیمرغ'),
(10200027, 10, 'سوادکوه شمالی'),
(10200028, 10, 'کلاردشت'),
(10300010, 5, 'میانه'),
(10300011, 5, 'هشترود'),
(10300012, 5, 'بناب'),
(10300013, 5, 'بستان آباد'),
(10300014, 5, 'شبستر'),
(10300015, 5, 'کلیبر'),
(10300016, 5, 'هریس'),
(10300019, 5, 'جلفا'),
(10300020, 5, 'ملکان'),
(10300021, 5, 'آذرشهر'),
(10300022, 5, 'اسکو'),
(10300023, 5, 'چاراویماق'),
(10300024, 5, 'ورزقان'),
(10300025, 5, 'عجب شیر'),
(10300026, 5, 'خداآفرین'),
(10300027, 5, 'هوراند'),
(10300028, 5, 'لیلان'),
(10400010, 13, 'بوکان'),
(10400011, 13, 'شاهین دژ'),
(10400012, 13, 'تکاب'),
(10400013, 13, 'اشنویه'),
(10400014, 13, 'چالدران'),
(10400015, 13, 'پلدشت'),
(10400016, 13, 'چایپاره'),
(10400017, 13, 'شوط'),
(10400018, 13, 'چهاربرج'),
(10400019, 13, 'باروق'),
(10400020, 13, 'میرآباد'),
(10500010, 14, 'صحنه'),
(10500011, 14, 'هرسین'),
(10500012, 14, 'ثلاث باباجانی'),
(10500013, 14, 'دالاهو'),
(10500014, 14, 'روانسر'),
(10600010, 9, 'رامهرمز'),
(10600011, 9, 'شادگان'),
(10600012, 9, 'شوشتر'),
(10600013, 9, 'مسجدسلیمان'),
(10600014, 9, 'شوش'),
(10600015, 9, 'باغ ملک'),
(10600016, 9, 'امیدیه'),
(10600017, 9, 'لالی'),
(10600018, 9, 'هندیجان'),
(10600019, 9, 'رامشیر'),
(10600020, 9, 'گتوند'),
(10600021, 9, 'اندیکا'),
(10600022, 9, 'هفتکل'),
(10600023, 9, 'هویزه'),
(10600024, 9, 'باوی'),
(10600025, 9, 'حمیدیه'),
(10600026, 9, 'آغاجاری'),
(10600027, 9, 'کارون'),
(10600028, 9, 'کرخه'),
(10600029, 9, 'دزپارت'),
(10600030, 9, 'صیدون'),
(10700010, 3, 'کازرون'),
(10700011, 3, 'لارستان'),
(10700013, 3, 'ممسنی'),
(10700014, 3, 'نی ریز'),
(10700015, 3, 'لامرد'),
(10700016, 3, 'بوانات'),
(10700017, 3, 'ارسنجان'),
(10700018, 3, 'خرم بید'),
(10700019, 3, 'زرین دشت'),
(10700020, 3, 'قیروکارزین'),
(10700021, 3, 'مهر'),
(10700022, 3, 'فراشبند'),
(10700023, 3, 'پاسارگاد'),
(10700024, 3, 'خنج'),
(10700025, 3, 'سروستان'),
(10700026, 3, 'رستم'),
(10700027, 3, 'گراش'),
(10700028, 3, 'کوار'),
(10700029, 3, 'خرامه'),
(10700030, 3, 'زرقان'),
(10700031, 3, 'بیضا'),
(10700032, 3, 'سرچهان'),
(10700033, 3, 'کوه چنار'),
(10700034, 3, 'خفر'),
(10700035, 3, 'بختگان'),
(10700036, 3, 'اوز'),
(10700037, 3, 'جویم'),
(10800010, 7, 'بردسیر'),
(10800011, 7, 'راور'),
(10800012, 7, 'عنبرآباد'),
(10800013, 7, 'منوجان'),
(10800014, 7, 'کوهبنان'),
(10800015, 7, 'رودبارجنوب'),
(10800016, 7, 'قلعه گنج'),
(10800017, 7, 'ریگان'),
(10800018, 7, 'رابر'),
(10800019, 7, 'فهرج'),
(10800020, 7, 'انار'),
(10800021, 7, 'نرماشیر'),
(10800022, 7, 'فاریاب'),
(10800023, 7, 'ارزوییه'),
(10800024, 7, 'گنبکی'),
(10800025, 7, 'جازموریان'),
(10900013, 8, 'قوچان'),
(10900014, 8, 'کاشمر'),
(10900015, 8, 'گناباد'),
(10900017, 8, 'نیشابور'),
(10900018, 8, 'چناران'),
(10900019, 8, 'خواف'),
(10900020, 8, 'سرخس'),
(10900022, 8, 'فریمان'),
(10900023, 8, 'بردسکن'),
(10900027, 8, 'رشتخوار'),
(10900028, 8, 'کلات'),
(10900029, 8, 'خلیل آباد'),
(10900030, 8, 'مه ولات'),
(10900031, 8, 'بجستان'),
(10900032, 8, 'طرقبه شاندیز'),
(10900033, 8, 'فیروزه'),
(10900034, 8, 'جغتای'),
(10900035, 8, 'زاوه'),
(10900036, 8, 'جوین'),
(10900037, 8, 'باخرز'),
(10900038, 8, 'خوشاب'),
(10900039, 8, 'داورزن'),
(10900040, 8, 'صالح آباد'),
(10900041, 8, 'کوهسرخ'),
(10900042, 8, 'زبرخان'),
(10900043, 8, 'ششتمد'),
(10900044, 8, 'گلبهار'),
(10900045, 8, 'میان جلگه'),
(11000011, 2, 'گلپایگان'),
(11000013, 2, 'نایین'),
(11000015, 2, 'نطنز'),
(11000016, 2, 'شاهین شهرو میمه'),
(11000017, 2, 'مبارکه'),
(11000018, 2, 'آران و بیدگل'),
(11000019, 2, 'تیران وکرون'),
(11000020, 2, 'چادگان'),
(11000021, 2, 'دهاقان'),
(11000022, 2, 'برخوار'),
(11000023, 2, 'خور و بیابانک'),
(11000024, 2, 'بویین و میاندشت'),
(11000025, 2, 'کوهپایه'),
(11000026, 2, 'جرقویه'),
(11000027, 2, 'ورزنه'),
(11000028, 2, 'هرند'),
(11100010, 15, 'زهک'),
(11100011, 15, 'هیرمند'),
(11100012, 15, 'دلگان'),
(11100013, 15, 'مهرستان'),
(11100014, 15, 'سیب و سوران'),
(11100015, 15, 'نیمروز'),
(11100016, 15, 'هامون'),
(11100017, 15, 'میرجاوه'),
(11100018, 15, 'قصرقند'),
(11100019, 15, 'فنوج'),
(11100020, 15, 'بمپور'),
(11100021, 15, 'تفتان'),
(11100022, 15, 'دشتیاری'),
(11100023, 15, 'سرباز'),
(11100024, 15, 'گلشن'),
(11100025, 15, 'لاشار'),
(11100026, 15, 'زرآباد'),
(11200010, 16, 'دهگلان'),
(11300010, 17, 'درگزین'),
(11400010, 18, 'خانمیرزا'),
(11400011, 18, 'فلارد'),
(11400012, 18, 'فرخ شهر'),
(11500010, 19, 'چگنی'),
(11500011, 19, 'رومشکان'),
(11500012, 19, 'معمولان'),
(11600010, 20, 'بدره'),
(11600011, 20, 'هلیلان'),
(11600012, 20, 'چوار'),
(11800010, 22, 'عسلویه'),
(11900010, 23, 'سلطانیه'),
(12100011, 6, 'بهاباد'),
(12100012, 6, 'مروست'),
(12100013, 6, 'زارچ'),
(12200010, 25, 'خمیر'),
(12200011, 25, 'پارسیان'),
(12200012, 25, 'سیریک'),
(12200013, 25, 'بشاگرد'),
(12300010, 1, 'اسلامشهر'),
(12300012, 1, 'رباط کریم'),
(12300013, 1, 'پاکدشت'),
(12300014, 1, 'فیروزکوه'),
(12300017, 1, 'ملارد'),
(12300018, 1, 'پیشوا'),
(12300019, 1, 'بهارستان'),
(12300020, 1, 'پردیس'),
(12300021, 1, 'قرچک'),
(12400010, 26, 'سرعین'),
(12400011, 26, 'اصلاندوز'),
(12400012, 26, 'انگوت'),
(12700010, 29, 'آزادشهر'),
(12700011, 29, 'رامیان'),
(12700012, 29, 'مراوه تپه'),
(12700013, 29, 'گمیشان'),
(12700014, 29, 'گالیکش'),
(12800010, 30, 'مانه'),
(12900010, 31, 'خوسف'),
(12900011, 31, 'طبس'),
(20000001, 5, 'ترکمانچای'),
(20000002, 31, 'عشق‌آباد'),
(20000003, 2, 'میمه و وزوان');

SELECT setval(pg_get_serial_sequence('cities','id'), (SELECT MAX(id) FROM cities), TRUE);

INSERT INTO venues (city_id, name, address, capacity, latitude, longitude) VALUES
(1,  'Azadi Stadium',            'Azadi Sports Complex, Tehran',      78000, 35.7247, 51.2753),
(1,  'Takhti Stadium',           'Takhti Complex, Tehran',            25000, 35.6671, 51.4510),
(1,  'Shahid Shiroudi Arena',    'Mofatteh Street, Tehran',           15000, 35.7117, 51.4294),
(4,  'Naghsh-e Jahan Stadium',   'Naghsh-e Jahan Complex, Isfahan',   75000, 32.6653, 51.7184),
(19, 'Fooladshahr Stadium',      'Fooladshahr, Isfahan',              20000, 32.4833, 51.4167),
(5,  'Kashan Municipal Arena',   'Sports Boulevard, Kashan',           5000, 33.9850, 51.4100),
(7,  'Pars Stadium',             'Shiraz Sports Complex',             50000, 29.5918, 52.5837),
(7,  'Hafezieh Arena',           'Hafez Avenue, Shiraz',              20000, 29.6210, 52.5340),
(10, 'Karaj Enghelab Stadium',   'Enghelab Boulevard, Karaj',         18000, 35.8400, 50.9391),
(6,  'Najafabad Sports Hall',    'Imam Square, Najafabad',             4000, 32.6344, 51.3653);

INSERT INTO venues (id, city_id, name, address, capacity, latitude, longitude) VALUES
(11,11,'Yadegar-e Emam Stadium','Tabriz Sports Complex',66000,38.0800,46.2960),
(12,15,'Ghadir Stadium','Ahvaz Sports Boulevard',51000,31.3183,48.6706),
(13,14,'Imam Reza Stadium','Mashhad Sports Complex',27000,36.2972,59.6067),
(14,13,'Shahid Bahonar Stadium','Kerman Sports Complex',15000,30.2839,57.0834),
(15,17,'Vatani Stadium','Sari Central Sports Complex',15000,36.5633,53.0601),
(16,1000001,'Imam Khomeini Stadium','Arak Sports Boulevard',15000,34.0954,49.7013),
(17,1080006,'Gol Gohar Stadium','Sirjan Gol Gohar Complex',12000,29.4514,55.6809),
(18,16,'Takhti Stadium Abadan','Abadan Sports Complex',22000,30.3473,48.2934),
(19,1010003,'Sirous Ghayeghran Stadium','Bandar Anzali Coastal Complex',10000,37.4724,49.4581),
(20,1270005,'Imam Khomeini Basketball Hall','Gorgan Sports Campus',6000,36.8417,54.4436),
(21,1040001,'Ghadir Volleyball Hall','Urmia Ghadir Complex',6000,37.5527,45.0761),
(22,1250001,'Shahid Heydarian Sports Hall','Qom Sports Complex',5000,34.6416,50.8746),
(23,1020001,'Payambar Azam Sports Hall','Amol Sports Campus',4500,36.4696,52.3507),
(24,1010005,'Rasht 6000 Seats Sports Hall','Rasht Sports Boulevard',6000,37.2808,49.5832),
(25,11,'Poursharifi Sports Hall','Tabriz Central Sports Campus',6000,38.0800,46.2919),
(26,14,'Shahid Beheshti Sports Hall','Mashhad Sports Boulevard',6500,36.2605,59.6168),
(27,13,'Kerman 6000 Seats Sports Hall','Kerman Sports Campus',6000,30.2832,57.0788),
(28,17,'Seyyed Rasoul Hosseini Sports Hall','Sari Sports Boulevard',6000,36.5659,53.0586),
(29,12,'Shahid Nassiri Stadium','Yazd Sports Complex',12000,31.8974,54.3675),
(30,1150003,'Takhti Stadium Khorramabad','Khorramabad Sports Complex',10000,33.4878,48.3558),
(31,1270006,'Olympic Sports Hall Gonbad','Gonbad-e Kavus Sports Campus',5000,37.2500,55.1672),
(32,12,'Shahid Sadoughi Sports Hall','Yazd Indoor Sports Campus',5500,31.8977,54.3565),
(33,1080006,'Imam Ali Sports Hall Sirjan','Sirjan Indoor Sports Complex',5000,29.4518,55.6818),
(34,1080004,'9 Dey Sports Hall Rafsanjan','Rafsanjan Sports Campus',5000,30.4067,55.9939),
(35,18,'Azadi Sports Hall Babol','Babol Sports Boulevard',4500,36.5449,52.6760),
(36,16,'17 Shahrivar Sports Hall','Abadan Indoor Sports Complex',5500,30.3478,48.2941),
(37,15,'Ghadir Sports Hall Ahvaz','Ahvaz Indoor Sports Campus',6000,31.3191,48.6715),
(38,4,'25 Aban Sports Hall Isfahan','Isfahan Indoor Sports Campus',6500,32.6546,51.6680);

SELECT setval(pg_get_serial_sequence('venues','id'),(SELECT MAX(id) FROM venues),TRUE);

INSERT INTO users
(city_id, first_name, last_name, email, phone, password_hash, role, preferred_login, is_active, created_at)
VALUES
(1,'Sara','Ahmadi','sara.ahmadi@support.ir','09121000001',crypt('Demo@123', gen_salt('bf', 10)),'support','email',TRUE,NOW()-INTERVAL '240 days'),
(4,'Ali','Rezaei','ali.rezaei@support.ir','09121000002',crypt('Demo@123', gen_salt('bf', 10)),'support','email',TRUE,NOW()-INTERVAL '230 days'),
(7,'Maryam','Hosseini','maryam.h@support.ir','09121000003',crypt('Demo@123', gen_salt('bf', 10)),'support','phone',TRUE,NOW()-INTERVAL '220 days'),
(1,'Reza','Karimi','reza.karimi@support.ir','09121000004',crypt('Demo@123', gen_salt('bf', 10)),'support','email',TRUE,NOW()-INTERVAL '210 days'),
(10,'Fatemeh','Mohammadi','fatemeh.m@support.ir','09121000005',crypt('Demo@123', gen_salt('bf', 10)),'support','phone',TRUE,NOW()-INTERVAL '200 days'),
(1,'Hossein','Moradi','hossein.m@gmail.com','09131000006',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '190 days'),
(4,'Zahra','Nazari','zahra.n@gmail.com','09131000007',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '180 days'),
(7,'Amir','Sadeghian','amir.s@yahoo.com','09131000008',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '170 days'),
(10,'Parisa','Ghorbani','parisa.g@outlook.com','09131000009',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '160 days'),
(5,'Mehdi','Jafari','mehdi.j@gmail.com','09131000010',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '150 days'),
(1,'Nasrin','Bagheri','nasrin.b@gmail.com','09141000011',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '140 days'),
(3,'Kamran','Tavakoli','kamran.t@gmail.com','09141000012',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '130 days'),
(6,'Leila','Esmaili','leila.e@gmail.com','09141000013',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '120 days'),
(4,'Dariush','Mansouri','dariush.m@gmail.com','09141000014',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '110 days'),
(7,'Shirin','Rostami','shirin.r@gmail.com','09151000015',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '100 days'),
(8,'Babak','Zareei','babak.z@gmail.com','09151000016',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '90 days'),
(1,'Mina','Khosravi','mina.k@gmail.com','09151000017',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '80 days'),
(7,'Arash','Shirazi','arash.sh@gmail.com','09151000018',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '70 days'),
(4,'Golnaz','Rahimi','golnaz.r@gmail.com','09161000019',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '60 days'),
(10,'Omid','Pourali','omid.p@gmail.com','09161000020',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '50 days'),
(11,'Nima','Azizi','nima.a@gmail.com','09161000021',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '40 days'),
(12,'Elham','Yazdani','elham.y@gmail.com','09161000022',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '30 days'),
(13,'Sina','Kermani','sina.k@gmail.com','09161000023',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '20 days'),
(14,'Mahsa','Razavi','mahsa.r@gmail.com','09161000024',crypt('Demo@123', gen_salt('bf', 10)),'spectator','email',TRUE,NOW()-INTERVAL '10 days'),
(15,'Pouya','Ahvazi','pouya.a@gmail.com','09161000025',crypt('Demo@123', gen_salt('bf', 10)),'spectator','phone',TRUE,NOW()-INTERVAL '5 days');


INSERT INTO sport_types (code, name) VALUES
('football','Football'), ('volleyball','Volleyball'), ('basketball','Basketball'),
('futsal','Futsal'), ('handball','Handball'), ('wrestling','Wrestling'),
('tennis','Tennis'), ('table_tennis','Table Tennis'), ('swimming','Swimming'),
('athletics','Athletics');

INSERT INTO teams (sport_type_id, city_id, name, short_name) VALUES
(1,1,'Persepolis FC','PER'), (1,1,'Esteghlal FC','EST'), (1,4,'Sepahan FC','SEP'),
(1,7,'Fajr Sepasi','FAJ'), (1,10,'Paykan FC','PAY'), (1,11,'Tractor FC','TRA'),
(2,1,'Peykan Volleyball','PVK'), (2,1,'Saipa Volleyball','SVK'),
(2,12,'Shahdab Yazd','SHY'), (2,13,'Foolad Sirjan','FSJ'),
(3,1,'Tehran Basketball','TEH'), (3,7,'Shiraz Basketball','SHB'),
(3,1,'Mahram Basketball','MAH'), (3,4,'Zob Ahan Basketball','ZAB'),
(4,4,'Giti Pasand Futsal','GPF'), (4,11,'Mes Sungun Futsal','MSF'),
(5,4,'Foolad Handball','FHB'), (5,7,'Shahid Chamran Handball','SCH'),
(6,1,'Iran Wrestling A','IWA'), (6,4,'Iran Wrestling B','IWB'),
(7,1,'Tehran Tennis Club','TTC'), (7,7,'Shiraz Tennis Club','STC'),
(8,1,'Noshad Table Tennis','NTT'), (8,4,'Keshavarz Table Tennis','KTT'),
(9,1,'Tehran Swimming','TSW'), (9,4,'Isfahan Swimming','ISW'),
(10,1,'Tehran Athletics','TAT'), (10,7,'Shiraz Athletics','SAT'),
(1,10,'Karaj Football','KRF'), (2,5,'Kashan Volleyball','KSV');

INSERT INTO teams (id,sport_type_id,city_id,name,short_name) VALUES
(31,1,15,'Foolad Khuzestan FC','FOO'),
(32,1,17,'Nassaji Mazandaran FC','NAS'),
(33,1,1010003,'Malavan Bandar Anzali FC','MAL'),
(34,1,1000001,'Aluminium Arak FC','ALU'),
(35,1,1080006,'Gol Gohar Sirjan FC','GGS'),
(36,1,13,'Mes Kerman FC','MSK'),
(37,1,4,'Zob Ahan FC','ZOB'),
(38,1,15,'Esteghlal Khuzestan FC','ESK'),
(39,1,1,'Havadar FC','HAV'),
(40,1,1150003,'Kheybar Khorramabad FC','KHE'),
(41,1,12,'Chadormalu Ardakan FC','CHA'),
(42,1,16,'Sanat Naft Abadan FC','SNA'),
(43,2,1040001,'Urmia Volleyball','URV'),
(44,2,1270005,'Gorgan Volleyball','GOV'),
(45,2,1270006,'Gonbad Volleyball','GNV'),
(46,2,1080004,'Rafsanjan Volleyball','RAV'),
(47,2,14,'Mashhad Volleyball','MHV'),
(48,2,17,'Sari Volleyball','SRV'),
(49,2,11,'Tabriz Volleyball','TBV'),
(50,2,1250001,'Qom Volleyball','QMV'),
(51,2,1020001,'Amol Volleyball','AMV'),
(52,2,18,'Babol Volleyball','BAV'),
(53,3,16,'Abadan Basketball','ABB'),
(54,3,1270005,'Gorgan Basketball','GOB'),
(55,3,14,'Mashhad Basketball','MHB'),
(56,3,11,'Tabriz Basketball','TBB'),
(57,3,1250001,'Qom Basketball','QMB'),
(58,3,13,'Kerman Basketball','KRB'),
(59,3,17,'Sari Basketball','SRB'),
(60,3,4,'Isfahan Basketball','ISB'),
(61,3,15,'Ahvaz Basketball','AHB'),
(62,3,1010005,'Rasht Basketball','RSB');

SELECT setval(pg_get_serial_sequence('teams','id'),(SELECT MAX(id) FROM teams),TRUE);

INSERT INTO organizers (name, support_email, support_phone) VALUES
('Iran Football League Organization','football@organizer.ir','02144000001'),
('Tehran Sports Board','tehran@organizer.ir','02144000002'),
('Isfahan Sports Board','isfahan@organizer.ir','03134000003'),
('Fars Sports Board','fars@organizer.ir','07134000004'),
('Iran Volleyball Federation','volleyball@organizer.ir','02144000005'),
('Iran Basketball Federation','basketball@organizer.ir','02144000006'),
('Karaj Sports Board','karaj@organizer.ir','02634000007'),
('National Indoor Sports Org','indoor@organizer.ir','02144000008'),
('University Sports Association','university@organizer.ir','02144000009'),
('Private Events Company','events@organizer.ir','02144000010');

INSERT INTO matches
(sport_type_id, home_team_id, away_team_id, venue_id, organizer_id,
 tournament_name, starts_at, ends_at, status)
VALUES
(1,1,2,1,1,'Persian Gulf Pro League',NOW()+INTERVAL '10 days',NOW()+INTERVAL '10 days 2 hours','scheduled'),
(1,3,1,4,3,'Persian Gulf Pro League',NOW()+INTERVAL '15 days',NOW()+INTERVAL '15 days 2 hours','scheduled'),
(1,2,3,1,1,'Persian Gulf Pro League',NOW()+INTERVAL '20 days',NOW()+INTERVAL '20 days 2 hours','scheduled'),
(1,4,5,7,4,'Azadegan League',NOW()+INTERVAL '5 days',NOW()+INTERVAL '5 days 2 hours','scheduled'),
(1,5,4,9,7,'Azadegan League',NOW()-INTERVAL '2 days',NOW()-INTERVAL '2 days'+INTERVAL '2 hours','completed'),
(1,1,3,1,1,'Persian Gulf Pro League',
 (SELECT yesterday_start+INTERVAL '18 hours' FROM seed_clock),
 (SELECT yesterday_start+INTERVAL '20 hours' FROM seed_clock),'completed'),
(1,6,2,2,2,'Persian Gulf Pro League',NOW()+INTERVAL '30 days',NOW()+INTERVAL '30 days 2 hours','scheduled'),
(1,1,6,1,1,'National Cup',NOW()+INTERVAL '40 days',NOW()+INTERVAL '40 days 2 hours','scheduled'),
(2,7,8,3,5,'Volleyball Super League',NOW()+INTERVAL '7 days',NOW()+INTERVAL '7 days 2 hours','scheduled'),
(2,9,7,4,5,'Volleyball Super League',NOW()+INTERVAL '12 days',NOW()+INTERVAL '12 days 2 hours','scheduled'),
(2,8,9,6,5,'Volleyball Super League',NOW()+INTERVAL '18 days',NOW()+INTERVAL '18 days 2 hours','scheduled'),
(2,30,7,10,5,'Volleyball Super League',NOW()+INTERVAL '25 days',NOW()+INTERVAL '25 days 2 hours','scheduled'),
(2,8,7,3,5,'Volleyball Super League',NOW()-INTERVAL '3 days',NOW()-INTERVAL '3 days'+INTERVAL '2 hours','completed'),
(2,7,30,2,5,'Volleyball National Cup',NOW()+INTERVAL '35 days',NOW()+INTERVAL '35 days 2 hours','scheduled'),
(3,11,12,2,6,'Basketball Super League',NOW()+INTERVAL '8 days',NOW()+INTERVAL '8 days 2 hours','scheduled'),
(3,12,13,8,6,'Basketball Super League',NOW()+INTERVAL '14 days',NOW()+INTERVAL '14 days 2 hours','scheduled'),
(3,13,14,2,6,'Basketball Super League',NOW()+INTERVAL '22 days',NOW()+INTERVAL '22 days 2 hours','scheduled'),
(3,14,11,8,6,'Basketball Super League',NOW()+INTERVAL '30 days',NOW()+INTERVAL '30 days 2 hours','scheduled'),
(3,11,13,2,6,'Basketball Super League',NOW()-INTERVAL '1 day',NOW()-INTERVAL '1 day'+INTERVAL '2 hours','completed'),
(3,12,14,3,6,'Basketball National Cup',NOW()+INTERVAL '45 days',NOW()+INTERVAL '45 days 2 hours','scheduled');

WITH match_seed
(id,sport_type_id,home_team_id,away_team_id,venue_id,organizer_id,tournament_name,day_offset,start_hour,duration_minutes) AS (
VALUES
(21,1,31,32,12,1,'Persian Gulf Pro League',3,18,120),
(22,1,33,34,19,1,'Persian Gulf Pro League',6,19,120),
(23,1,35,36,17,1,'National Cup',9,20,120),
(24,1,37,38,5,3,'Persian Gulf Pro League',13,18,120),
(25,1,39,40,2,2,'Azadegan League',17,19,120),
(26,1,41,42,29,1,'National Cup',21,18,120),
(27,1,1,31,1,1,'Persian Gulf Pro League',24,20,120),
(28,1,2,33,1,1,'Persian Gulf Pro League',27,18,120),
(29,1,3,35,4,3,'Persian Gulf Pro League',31,19,120),
(30,1,6,37,11,1,'Persian Gulf Pro League',34,17,120),
(31,1,32,39,15,1,'National Cup',38,19,120),
(32,1,34,41,16,1,'Persian Gulf Pro League',42,18,120),
(33,1,40,36,30,1,'Azadegan League',46,20,120),
(34,1,38,42,12,1,'Khuzestan Derby Cup',50,19,120),
(35,1,4,29,7,4,'Azadegan League',54,18,120),
(36,1,5,1,9,1,'National Cup',58,20,120),
(37,2,43,44,21,5,'Volleyball Super League',4,17,120),
(38,2,45,46,31,5,'Iran Club Volleyball Championship',6,18,120),
(39,2,47,48,26,5,'Volleyball Super League',9,17,120),
(40,2,49,50,25,5,'Volleyball National Cup',11,18,120),
(41,2,51,52,23,5,'Mazandaran Volleyball Cup',13,17,120),
(42,2,7,43,3,5,'Volleyball Super League',16,18,120),
(43,2,8,45,3,5,'Volleyball Super League',19,17,120),
(44,2,9,47,32,5,'Volleyball Super League',23,18,120),
(45,2,10,49,33,5,'Volleyball National Cup',27,17,120),
(46,2,30,51,6,5,'Iran Club Volleyball Championship',30,18,120),
(47,2,44,7,20,5,'Volleyball Super League',34,17,120),
(48,2,46,8,34,5,'Volleyball Super League',37,18,120),
(49,2,48,9,28,5,'Volleyball Super League',41,17,120),
(50,2,50,10,22,5,'Volleyball National Cup',45,18,120),
(51,2,52,30,35,5,'Iran Club Volleyball Championship',49,17,120),
(52,2,43,49,21,5,'Volleyball Super League',53,18,120),
(53,3,53,54,36,6,'Basketball Super League',4,20,120),
(54,3,55,56,26,6,'Basketball Super League',7,19,120),
(55,3,57,58,22,6,'Basketball National Cup',10,18,120),
(56,3,59,60,28,6,'Basketball Super League',12,20,120),
(57,3,61,62,37,6,'Iran Basketball Championship',15,19,120),
(58,3,11,53,3,6,'Basketball Super League',18,20,120),
(59,3,12,55,8,6,'Basketball Super League',21,19,120),
(60,3,13,57,3,6,'Basketball National Cup',24,18,120),
(61,3,14,59,38,6,'Basketball Super League',28,20,120),
(62,3,54,11,20,6,'Basketball Super League',32,19,120),
(63,3,56,12,25,6,'Iran Basketball Championship',36,18,120),
(64,3,58,13,27,6,'Basketball Super League',40,20,120),
(65,3,60,61,38,6,'Basketball Super League',44,19,120),
(66,3,62,14,24,6,'Basketball National Cup',48,18,120),
(67,3,53,55,36,6,'Basketball Super League',52,20,120),
(68,3,57,54,22,6,'Iran Basketball Championship',56,19,120)
)
INSERT INTO matches
(id,sport_type_id,home_team_id,away_team_id,venue_id,organizer_id,tournament_name,starts_at,ends_at,status)
SELECT id,sport_type_id,home_team_id,away_team_id,venue_id,organizer_id,tournament_name,
       date_trunc('day',CURRENT_TIMESTAMP)+make_interval(days=>day_offset,hours=>start_hour),
       date_trunc('day',CURRENT_TIMESTAMP)+make_interval(days=>day_offset,hours=>start_hour,mins=>duration_minutes),
       'scheduled'
FROM match_seed
ORDER BY id;

SELECT setval(pg_get_serial_sequence('matches','id'),(SELECT MAX(id) FROM matches),TRUE);

DO $$
DECLARE v_conflicts INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_conflicts
    FROM matches a
    JOIN matches b ON a.id<b.id AND a.starts_at::date=b.starts_at::date
    WHERE a.home_team_id IN (b.home_team_id,b.away_team_id)
       OR a.away_team_id IN (b.home_team_id,b.away_team_id);
    IF v_conflicts>0 THEN
        RAISE EXCEPTION 'Seed schedule contains % same-day team conflict(s).',v_conflicts;
    END IF;
END;
$$;

INSERT INTO ticket_categories (code, name, sort_order) VALUES
('regular','Regular',10), ('special','Special',20), ('vip','VIP',30),
('premium','Premium',40), ('family','Family',50), ('student','Student',60),
('accessible','Accessible',70), ('hospitality','Hospitality',80),
('fan_zone','Fan Zone',90), ('early_bird','Early Bird',100);

INSERT INTO tickets
(match_id,ticket_category_id,section_code,row_code,seat_code,is_numbered,price,total_capacity,sale_starts_at,sale_ends_at)
VALUES
(1,1,'EAST',NULL,NULL,FALSE,150000,500,NOW()-INTERVAL '30 days',NOW()+INTERVAL '9 days'),
(1,3,'VIP-A','1','1',TRUE,300000,1,NOW()-INTERVAL '30 days',NOW()+INTERVAL '9 days'),
(1,3,'VIP-A','1','2',TRUE,300000,1,NOW()-INTERVAL '30 days',NOW()+INTERVAL '9 days'),
(2,1,'WEST',NULL,NULL,FALSE,120000,400,NOW()-INTERVAL '25 days',NOW()+INTERVAL '14 days'),
(2,2,'SPECIAL',NULL,NULL,FALSE,200000,100,NOW()-INTERVAL '25 days',NOW()+INTERVAL '14 days'),
(3,1,'EAST',NULL,NULL,FALSE,130000,450,NOW()-INTERVAL '20 days',NOW()+INTERVAL '19 days'),
(4,1,'MAIN',NULL,NULL,FALSE,100000,300,NOW()-INTERVAL '15 days',NOW()+INTERVAL '4 days'),
(5,1,'MAIN',NULL,NULL,FALSE,90000,200,NOW()-INTERVAL '30 days',NOW()-INTERVAL '3 days'),
(6,1,'EAST',NULL,NULL,FALSE,110000,300,NOW()-INTERVAL '30 days',
 (SELECT yesterday_start+INTERVAL '17 hours' FROM seed_clock)),
(7,1,'MAIN',NULL,NULL,FALSE,100000,250,NOW()-INTERVAL '10 days',NOW()+INTERVAL '29 days'),
(8,3,'VIP-V','1','1',TRUE,260000,1,NOW()-INTERVAL '5 days',NOW()+INTERVAL '39 days'),
(9,1,'A',NULL,NULL,FALSE,80000,200,NOW()-INTERVAL '20 days',NOW()+INTERVAL '6 days'),
(9,3,'COURTSIDE','1','1',TRUE,180000,1,NOW()-INTERVAL '20 days',NOW()+INTERVAL '6 days'),
(10,1,'A',NULL,NULL,FALSE,75000,180,NOW()-INTERVAL '15 days',NOW()+INTERVAL '11 days'),
(11,2,'B',NULL,NULL,FALSE,70000,160,NOW()-INTERVAL '15 days',NOW()+INTERVAL '17 days'),
(12,1,'A',NULL,NULL,FALSE,65000,140,NOW()-INTERVAL '10 days',NOW()+INTERVAL '24 days'),
(13,3,'COURTSIDE','2','1',TRUE,160000,1,NOW()-INTERVAL '30 days',NOW()-INTERVAL '4 days'),
(14,1,'A',NULL,NULL,FALSE,60000,120,NOW()-INTERVAL '5 days',NOW()+INTERVAL '34 days'),
(15,1,'A',NULL,NULL,FALSE,55000,200,NOW()-INTERVAL '20 days',NOW()+INTERVAL '7 days'),
(15,3,'COURTSIDE','1','1',TRUE,150000,1,NOW()-INTERVAL '20 days',NOW()+INTERVAL '7 days'),
(16,1,'A',NULL,NULL,FALSE,60000,180,NOW()-INTERVAL '15 days',NOW()+INTERVAL '13 days'),
(17,2,'B',NULL,NULL,FALSE,65000,150,NOW()-INTERVAL '15 days',NOW()+INTERVAL '21 days'),
(18,1,'A',NULL,NULL,FALSE,50000,160,NOW()-INTERVAL '10 days',NOW()+INTERVAL '29 days'),
(19,3,'COURTSIDE','2','1',TRUE,140000,1,NOW()-INTERVAL '30 days',NOW()-INTERVAL '2 days'),
(20,1,'A',NULL,NULL,FALSE,55000,130,NOW()-INTERVAL '5 days',NOW()+INTERVAL '44 days'),
(9,3,'COURTSIDE','1','2',TRUE,180000,1,NOW()-INTERVAL '20 days',NOW()+INTERVAL '6 days'),
(15,3,'COURTSIDE','1','2',TRUE,150000,1,NOW()-INTERVAL '20 days',NOW()+INTERVAL '7 days'),
(8,3,'VIP-V','1','2',TRUE,260000,1,NOW()-INTERVAL '5 days',NOW()+INTERVAL '39 days'),
(13,3,'COURTSIDE','2','2',TRUE,160000,1,NOW()-INTERVAL '30 days',NOW()-INTERVAL '4 days'),
(19,3,'COURTSIDE','2','2',TRUE,140000,1,NOW()-INTERVAL '30 days',NOW()-INTERVAL '2 days'),
(2,3,'VIP-A','1','1',TRUE,250000,1,NOW()-INTERVAL '25 days',NOW()+INTERVAL '14 days'),
(2,3,'VIP-A','1','2',TRUE,250000,1,NOW()-INTERVAL '25 days',NOW()+INTERVAL '14 days'),
(3,3,'VIP-A','1','1',TRUE,270000,1,NOW()-INTERVAL '20 days',NOW()+INTERVAL '19 days'),
(3,3,'VIP-A','1','2',TRUE,270000,1,NOW()-INTERVAL '20 days',NOW()+INTERVAL '19 days'),
(16,3,'VIP-C','1','1',TRUE,130000,1,NOW()-INTERVAL '15 days',NOW()+INTERVAL '13 days'),
(16,3,'VIP-C','1','2',TRUE,130000,1,NOW()-INTERVAL '15 days',NOW()+INTERVAL '13 days'),
(17,3,'VIP-C','1','1',TRUE,135000,1,NOW()-INTERVAL '15 days',NOW()+INTERVAL '21 days'),
(17,3,'VIP-C','1','2',TRUE,135000,1,NOW()-INTERVAL '15 days',NOW()+INTERVAL '21 days'),
(20,3,'VIP-D','1','1',TRUE,120000,1,NOW()-INTERVAL '5 days',NOW()+INTERVAL '44 days'),
(20,3,'VIP-D','1','2',TRUE,120000,1,NOW()-INTERVAL '5 days',NOW()+INTERVAL '44 days');

INSERT INTO tickets
(id,match_id,ticket_category_id,section_code,row_code,seat_code,is_numbered,price,total_capacity,sale_starts_at,sale_ends_at)
SELECT 20+m.id,
       m.id,
       CASE WHEN m.id%7=0 THEN 5 WHEN m.id%5=0 THEN 6 WHEN m.id%4=0 THEN 2 ELSE 1 END,
       CASE m.sport_type_id
           WHEN 1 THEN CASE m.id%3 WHEN 0 THEN 'EAST' WHEN 1 THEN 'WEST' ELSE 'MAIN' END
           WHEN 2 THEN CASE m.id%3 WHEN 0 THEN 'A' WHEN 1 THEN 'B' ELSE 'C' END
           ELSE CASE m.id%3 WHEN 0 THEN 'LOWER' WHEN 1 THEN 'UPPER' ELSE 'COURTSIDE' END
       END,
       NULL,NULL,FALSE,
       CASE m.sport_type_id
           WHEN 1 THEN 90000+(m.id%6)*15000
           WHEN 2 THEN 60000+(m.id%6)*10000
           ELSE 55000+(m.id%6)*10000
       END,
       120+(m.id%5)*40,
       CURRENT_TIMESTAMP-INTERVAL '7 days',
       m.starts_at-INTERVAL '2 hours'
FROM matches m
WHERE m.id BETWEEN 21 AND 68
ORDER BY m.id;

SELECT setval(pg_get_serial_sequence('tickets','id'),(SELECT MAX(id) FROM tickets),TRUE);

INSERT INTO amenities (code,name,description) VALUES
('covered_seating','Covered Seating','Protected seating area'),
('parking','Parking','Parking access included'),
('catering','Catering','Food and beverage service'),
('vip_lounge','VIP Lounge','Access to VIP lounge'),
('dedicated_entrance','Dedicated Entrance','Separate entrance gate'),
('near_field','Near Field','Seat close to the playing area'),
('accessible_seating','Accessible Seating','Wheelchair-friendly access'),
('family_area','Family Area','Family-only seating area'),
('merchandise','Merchandise Pack','Official merchandise pack'),
('priority_support','Priority Support','Priority customer support');

INSERT INTO ticket_amenities (ticket_id, amenity_id, details)
SELECT t.id, a.id,
       CASE a.code WHEN 'parking' THEN 'Gate P1' WHEN 'dedicated_entrance' THEN 'Gate VIP' ELSE NULL END
FROM tickets t
JOIN amenities a ON
    (a.id = 2)
 OR (a.id = 1 AND t.ticket_category_id IN (2,3,4,8))
 OR (a.id = 3 AND t.ticket_category_id IN (3,4,8))
 OR (a.id = 4 AND t.ticket_category_id = 3)
 OR (a.id = 5 AND t.is_numbered)
 OR (a.id = 6 AND t.is_numbered)
 OR (a.id = 7 AND t.ticket_category_id = 7)
 OR (a.id = 8 AND t.ticket_category_id = 5)
 OR (a.id = 9 AND t.ticket_category_id IN (3,8))
 OR (a.id = 10 AND t.ticket_category_id IN (3,4,8));

INSERT INTO payment_methods (code,name) VALUES
('bank_card','Bank Card'), ('wallet','Wallet'), ('local_gateway','Local Mock Gateway'),
('pos','POS'), ('bank_transfer','Bank Transfer'), ('gift_credit','Gift Credit'),
('corporate_credit','Corporate Credit'), ('voucher','Voucher'),
('crypto_demo','Demo Cryptocurrency'), ('cash_office','Cash at Office');

INSERT INTO cancellation_policies (organizer_id,hours_before_match,penalty_percentage,description)
SELECT o.id, x.hours_before, x.penalty, x.description
FROM organizers o
CROSS JOIN (
    VALUES
        (72, 0.00::NUMERIC,  '72 hours or more before match'),
        (24, 20.00::NUMERIC, '24 to less than 72 hours before match'),
        (0,  50.00::NUMERIC, 'Less than 24 hours before match')
) AS x(hours_before,penalty,description);

WITH seed(id,user_id,ticket_id,status,quantity,reserved_at,expires_at,paid_at,canceled_at,canceled_by,reason) AS (
VALUES
(1,6,1,'paid',2,NOW()-INTERVAL '20 days',NOW()-INTERVAL '20 days'+INTERVAL '10 minutes',NOW()-INTERVAL '20 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(2,7,4,'paid',1,NOW()-INTERVAL '18 days',NOW()-INTERVAL '18 days'+INTERVAL '10 minutes',NOW()-INTERVAL '18 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(3,8,6,'paid',3,NOW()-INTERVAL '15 days',NOW()-INTERVAL '15 days'+INTERVAL '10 minutes',NOW()-INTERVAL '15 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(4,9,7,'paid',1,NOW()-INTERVAL '12 days',NOW()-INTERVAL '12 days'+INTERVAL '10 minutes',NOW()-INTERVAL '12 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(5,10,8,'paid',2,NOW()-INTERVAL '10 days',NOW()-INTERVAL '10 days'+INTERVAL '10 minutes',NOW()-INTERVAL '10 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(6,11,12,'paid',1,NOW()-INTERVAL '8 days',NOW()-INTERVAL '8 days'+INTERVAL '10 minutes',NOW()-INTERVAL '8 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(7,12,14,'paid',2,NOW()-INTERVAL '7 days',NOW()-INTERVAL '7 days'+INTERVAL '10 minutes',NOW()-INTERVAL '7 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(8,13,15,'paid',1,NOW()-INTERVAL '6 days',NOW()-INTERVAL '6 days'+INTERVAL '10 minutes',NOW()-INTERVAL '6 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(9,14,16,'held',1,NOW()-INTERVAL '5 minutes',NOW()+INTERVAL '5 minutes',NULL,NULL,NULL,NULL),
(10,15,18,'paid',2,NOW()-INTERVAL '4 days',NOW()-INTERVAL '4 days'+INTERVAL '10 minutes',NOW()-INTERVAL '4 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(11,16,19,'paid',1,NOW()-INTERVAL '3 days',NOW()-INTERVAL '3 days'+INTERVAL '10 minutes',NOW()-INTERVAL '3 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(12,17,21,'paid',2,NOW()-INTERVAL '2 days',NOW()-INTERVAL '2 days'+INTERVAL '10 minutes',NOW()-INTERVAL '2 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(13,18,22,'expired',1,NOW()-INTERVAL '20 minutes',NOW()-INTERVAL '10 minutes',NULL,NOW()-INTERVAL '10 minutes',NULL,'Automatic expiration after payment timeout'),
(14,19,23,'held',3,NOW()-INTERVAL '2 minutes',NOW()+INTERVAL '8 minutes',NULL,NULL,NULL,NULL),
(15,20,25,'paid',1,NOW()-INTERVAL '6 hours',NOW()-INTERVAL '6 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '6 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(16,6,12,'refunded',1,NOW()-INTERVAL '9 days',NOW()-INTERVAL '9 days'+INTERVAL '10 minutes',NOW()-INTERVAL '9 days'+INTERVAL '2 minutes',NOW()-INTERVAL '8 days',1,'Approved cancellation'),
(17,6,1,'refunded',3,NOW()-INTERVAL '11 days',NOW()-INTERVAL '11 days'+INTERVAL '10 minutes',NOW()-INTERVAL '11 days'+INTERVAL '2 minutes',NOW()-INTERVAL '10 days',1,'Approved cancellation'),
(18,8,19,'paid',1,NOW()-INTERVAL '5 days',NOW()-INTERVAL '5 days'+INTERVAL '10 minutes',NOW()-INTERVAL '5 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(19,9,4,'paid',1,NOW()-INTERVAL '1 day 3 hours',NOW()-INTERVAL '1 day 3 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '1 day 3 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(20,6,19,'paid',1,NOW()-INTERVAL '2 hours',NOW()-INTERVAL '2 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '2 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(21,6,12,'paid',1,NOW()-INTERVAL '1 day 2 hours',NOW()-INTERVAL '1 day 2 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '1 day 2 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(22,7,9,'paid',1,
 (SELECT yesterday_start+INTERVAL '10 hours' FROM seed_clock),
 (SELECT yesterday_start+INTERVAL '10 hours 10 minutes' FROM seed_clock),
 (SELECT yesterday_start+INTERVAL '10 hours 2 minutes' FROM seed_clock),NULL,NULL,NULL),
(23,7,13,'refunded',1,NOW()-INTERVAL '6 days',NOW()-INTERVAL '6 days'+INTERVAL '10 minutes',NOW()-INTERVAL '6 days'+INTERVAL '2 minutes',NOW()-INTERVAL '5 days',1,'Seat was unavailable'),
(24,8,20,'refunded',1,NOW()-INTERVAL '5 days',NOW()-INTERVAL '5 days'+INTERVAL '10 minutes',NOW()-INTERVAL '5 days'+INTERVAL '2 minutes',NOW()-INTERVAL '4 days',2,'User cancellation'),
(25,6,2,'refunded',1,NOW()-INTERVAL '4 days',NOW()-INTERVAL '4 days'+INTERVAL '10 minutes',NOW()-INTERVAL '4 days'+INTERVAL '2 minutes',NOW()-INTERVAL '3 days',1,'User cancellation'),
(26,10,17,'refunded',1,NOW()-INTERVAL '4 days',NOW()-INTERVAL '4 days'+INTERVAL '10 minutes',NOW()-INTERVAL '4 days'+INTERVAL '2 minutes',NOW()-INTERVAL '3 days',2,'Event issue'),
(27,11,24,'refunded',1,NOW()-INTERVAL '3 days',NOW()-INTERVAL '3 days'+INTERVAL '10 minutes',NOW()-INTERVAL '3 days'+INTERVAL '2 minutes',NOW()-INTERVAL '2 days',3,'Seat issue'),
(28,12,10,'paid',4,
 (SELECT today_start+(now_ts-today_start)*0.20-INTERVAL '2 minutes' FROM seed_clock),
 (SELECT today_start+(now_ts-today_start)*0.20+INTERVAL '8 minutes' FROM seed_clock),
 (SELECT today_start+(now_ts-today_start)*0.20 FROM seed_clock),NULL,NULL,NULL),
(29,13,5,'paid',2,
 (SELECT today_start+(now_ts-today_start)*0.45-INTERVAL '2 minutes' FROM seed_clock),
 (SELECT today_start+(now_ts-today_start)*0.45+INTERVAL '8 minutes' FROM seed_clock),
 (SELECT today_start+(now_ts-today_start)*0.45 FROM seed_clock),NULL,NULL,NULL),
(30,14,10,'paid',1,
 (SELECT today_start+(now_ts-today_start)*0.70-INTERVAL '2 minutes' FROM seed_clock),
 (SELECT today_start+(now_ts-today_start)*0.70+INTERVAL '8 minutes' FROM seed_clock),
 (SELECT today_start+(now_ts-today_start)*0.70 FROM seed_clock),NULL,NULL,NULL),
(31,15,11,'refunded',1,NOW()-INTERVAL '7 days',NOW()-INTERVAL '7 days'+INTERVAL '10 minutes',NOW()-INTERVAL '7 days'+INTERVAL '2 minutes',NOW()-INTERVAL '6 days',4,'VIP service unavailable'),
(32,16,13,'refunded',1,NOW()-INTERVAL '8 days',NOW()-INTERVAL '8 days'+INTERVAL '10 minutes',NOW()-INTERVAL '8 days'+INTERVAL '2 minutes',NOW()-INTERVAL '7 days',4,'Seat problem'),
(33,17,20,'refunded',1,NOW()-INTERVAL '9 days',NOW()-INTERVAL '9 days'+INTERVAL '10 minutes',NOW()-INTERVAL '9 days'+INTERVAL '2 minutes',NOW()-INTERVAL '8 days',5,'Match rescheduled'),
(34,18,3,'paid',1,NOW()-INTERVAL '3 days',NOW()-INTERVAL '3 days'+INTERVAL '10 minutes',NOW()-INTERVAL '3 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(35,19,11,'paid',1,NOW()-INTERVAL '3 days',NOW()-INTERVAL '3 days'+INTERVAL '10 minutes',NOW()-INTERVAL '3 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(36,20,13,'paid',1,NOW()-INTERVAL '2 days',NOW()-INTERVAL '2 days'+INTERVAL '10 minutes',NOW()-INTERVAL '2 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(37,21,29,'paid',1,NOW()-INTERVAL '2 days',NOW()-INTERVAL '2 days'+INTERVAL '10 minutes',NOW()-INTERVAL '2 days'+INTERVAL '2 minutes',NULL,NULL,NULL),
(38,22,20,'paid',1,NOW()-INTERVAL '1 day',NOW()-INTERVAL '1 day'+INTERVAL '10 minutes',NOW()-INTERVAL '1 day'+INTERVAL '2 minutes',NULL,NULL,NULL),
(39,23,30,'paid',1,NOW()-INTERVAL '1 day',NOW()-INTERVAL '1 day'+INTERVAL '10 minutes',NOW()-INTERVAL '1 day'+INTERVAL '2 minutes',NULL,NULL,NULL),
(40,24,31,'paid',1,NOW()-INTERVAL '12 hours',NOW()-INTERVAL '12 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '12 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(41,25,34,'paid',1,NOW()-INTERVAL '10 hours',NOW()-INTERVAL '10 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '10 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(42,18,35,'paid',1,NOW()-INTERVAL '8 hours',NOW()-INTERVAL '8 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '8 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(43,19,38,'paid',1,NOW()-INTERVAL '6 hours',NOW()-INTERVAL '6 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '6 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(44,20,39,'paid',1,NOW()-INTERVAL '4 hours',NOW()-INTERVAL '4 hours'+INTERVAL '10 minutes',NOW()-INTERVAL '4 hours'+INTERVAL '2 minutes',NULL,NULL,NULL),
(45,6,7,'canceled',1,NOW()-INTERVAL '13 days',NOW()-INTERVAL '13 days'+INTERVAL '10 minutes',NULL,NOW()-INTERVAL '13 days'+INTERVAL '5 minutes',1,'Canceled by support before payment'),
(46,7,14,'canceled',1,NOW()-INTERVAL '12 days',NOW()-INTERVAL '12 days'+INTERVAL '10 minutes',NULL,NOW()-INTERVAL '12 days'+INTERVAL '5 minutes',2,'Canceled by support before payment'),
(47,8,21,'canceled',1,NOW()-INTERVAL '11 days',NOW()-INTERVAL '11 days'+INTERVAL '10 minutes',NULL,NOW()-INTERVAL '11 days'+INTERVAL '5 minutes',3,'Canceled by support before payment')
)
INSERT INTO reservations
(id,user_id,ticket_id,status,quantity,unit_price,reserved_at,expires_at,paid_at,canceled_at,canceled_by,cancellation_reason)
SELECT s.id,s.user_id,s.ticket_id,s.status,s.quantity,t.price,s.reserved_at,s.expires_at,
       s.paid_at,s.canceled_at,s.canceled_by,s.reason
FROM seed s
JOIN tickets t ON t.id=s.ticket_id
ORDER BY s.id;

SELECT setval(
    pg_get_serial_sequence('reservations','id'),
    (SELECT MAX(id) FROM reservations),
    TRUE
);

UPDATE tickets SET held_quantity=0, sold_quantity=0, change_held_quantity=0;
WITH counts AS (
    SELECT ticket_id,
           SUM(quantity) FILTER (WHERE status='held') AS held,
           SUM(quantity) FILTER (WHERE status='paid') AS sold
    FROM reservations
    GROUP BY ticket_id
)
UPDATE tickets t
SET held_quantity=COALESCE(c.held,0),
    sold_quantity=COALESCE(c.sold,0)
FROM counts c
WHERE c.ticket_id=t.id;

DELETE FROM reservation_status_history;

INSERT INTO reservation_status_history
(reservation_id,old_status,new_status,changed_by,note,changed_at)
SELECT id,NULL,'held',NULL,'Reservation created',reserved_at
FROM reservations;

INSERT INTO reservation_status_history
(reservation_id,old_status,new_status,changed_by,note,changed_at)
SELECT id,'held','paid',NULL,'Payment completed',paid_at
FROM reservations
WHERE status IN ('paid','refunded');

INSERT INTO reservation_status_history
(reservation_id,old_status,new_status,changed_by,note,changed_at)
SELECT id,
       CASE WHEN status='refunded' THEN 'paid' ELSE 'held' END,
       status,
       canceled_by,
       cancellation_reason,
       canceled_at
FROM reservations
WHERE status IN ('canceled','expired','refunded');

INSERT INTO payments
(reservation_id,payment_method_id,amount,status,transaction_ref,created_at,paid_at)
SELECT
    r.id,
    CASE WHEN r.id IN (1,6,10,12,15) THEN 2 ELSE 1 END,
    r.total_amount,
    'successful',
    'PAY-S-'||lpad(r.id::TEXT,5,'0'),
    r.paid_at - INTERVAL '30 seconds',
    r.paid_at
FROM reservations r
WHERE r.status IN ('paid','refunded');

INSERT INTO payments
(reservation_id,payment_method_id,amount,status,transaction_ref,failure_reason,created_at,paid_at)
SELECT
    r.id,
    3,
    r.total_amount,
    'failed',
    'PAY-F-'||lpad(r.id::TEXT,5,'0'),
    'Local gateway simulation failure',
    r.reserved_at + INTERVAL '1 minute',
    NULL
FROM reservations r
WHERE r.id IN (9,13,14,16,17,23,24,25,26,27);

DO $$
DECLARE
    rec RECORD;
    v_balance NUMERIC(16,2);
BEGIN
    FOR rec IN SELECT id FROM wallets ORDER BY id LOOP
        UPDATE wallets
        SET balance=5000000
        WHERE id=rec.id
        RETURNING balance INTO v_balance;

        INSERT INTO wallet_transactions
            (wallet_id,transaction_type,amount,balance_after,reference_code,description)
        VALUES
            (rec.id,'top_up',5000000,v_balance,'WALLET-OPEN-'||lpad(rec.id::TEXT,4,'0'),'Initial demo balance');
    END LOOP;
END;
$$;

DO $$
DECLARE
    rec RECORD;
    v_balance NUMERIC(16,2);
BEGIN
    FOR rec IN
        SELECT p.id AS payment_id,p.amount,r.user_id
        FROM payments p
        JOIN reservations r ON r.id=p.reservation_id
        WHERE p.status='successful' AND p.payment_method_id=2
        ORDER BY p.paid_at,p.id
    LOOP
        UPDATE wallets
        SET balance=balance-rec.amount
        WHERE user_id=rec.user_id
        RETURNING balance INTO v_balance;

        INSERT INTO wallet_transactions
            (wallet_id,payment_id,transaction_type,amount,balance_after,reference_code,description)
        SELECT id,rec.payment_id,'purchase',-rec.amount,v_balance,
               'WALLET-PAY-'||lpad(rec.payment_id::TEXT,5,'0'),'Ticket purchase'
        FROM wallets WHERE user_id=rec.user_id;
    END LOOP;
END;
$$;

WITH refundable AS (
    SELECT r.*,m.organizer_id,m.starts_at,
           CASE WHEN m.starts_at<=r.canceled_at THEN 100.00::NUMERIC(5,2)
                ELSE COALESCE((
                    SELECT cp.penalty_percentage
                    FROM cancellation_policies cp
                    WHERE cp.organizer_id=m.organizer_id
                      AND cp.hours_before_match <= EXTRACT(EPOCH FROM (m.starts_at-r.canceled_at))/3600.0
                    ORDER BY cp.hours_before_match DESC LIMIT 1
                ),0.00::NUMERIC(5,2)) END AS penalty_pct
    FROM reservations r
    JOIN tickets t ON t.id=r.ticket_id
    JOIN matches m ON m.id=t.match_id
    WHERE r.status = 'refunded'
            AND r.canceled_at IS NOT NULL
            AND r.canceled_by IS NOT NULL
)
INSERT INTO cancellation_requests
(reservation_id,requested_by,reason,status,estimated_penalty_pct,estimated_refund,reviewed_by,review_note,requested_at,reviewed_at)
SELECT r.id,r.user_id,COALESCE(r.cancellation_reason,'Cancellation request'),'processed',
       r.penalty_pct,ROUND(r.total_amount*(100-r.penalty_pct)/100,2),r.canceled_by,
       'Approved according to organizer policy',r.canceled_at-INTERVAL '2 hours',r.canceled_at
FROM refundable r ORDER BY r.id;

INSERT INTO refunds
(cancellation_request_id,payment_id,wallet_id,amount,penalty_amount,status,transaction_ref,created_at,completed_at)
SELECT cr.id,p.id,w.id,cr.estimated_refund,p.amount-cr.estimated_refund,'completed',
       'REF-'||lpad(cr.id::TEXT,5,'0'),cr.reviewed_at,cr.reviewed_at+INTERVAL '1 minute'
FROM cancellation_requests cr
JOIN reservations r ON r.id=cr.reservation_id
JOIN payments p ON p.reservation_id=r.id AND p.status='successful'
JOIN wallets w ON w.user_id=r.user_id
ORDER BY cr.id;

DO $$
DECLARE rec RECORD; v_balance NUMERIC(16,2);
BEGIN
    FOR rec IN
        SELECT rf.id,rf.wallet_id,rf.payment_id,rf.amount,rf.transaction_ref
        FROM refunds rf WHERE rf.status='completed' ORDER BY rf.completed_at,rf.id
    LOOP
        UPDATE wallets SET balance=balance+rec.amount WHERE id=rec.wallet_id RETURNING balance INTO v_balance;
        IF rec.amount>0 THEN
            INSERT INTO wallet_transactions
                (wallet_id,payment_id,transaction_type,amount,balance_after,reference_code,description)
            VALUES(rec.wallet_id,rec.payment_id,'refund',rec.amount,v_balance,
                   'WALLET-'||rec.transaction_ref,'Cancellation refund');
        END IF;
    END LOOP;
END;
$$;

WITH change_seed
(reservation_id,requested_by,old_ticket_id,requested_ticket_id,status,reviewed_by,
 review_note,requested_at,reviewed_at,target_hold_expires_at) AS (
VALUES
(34,18,2,3,'processed',1,'Equivalent seat approved',NOW()-INTERVAL '2 days',NOW()-INTERVAL '1 day 23 hours',NOW()-INTERVAL '1 day 23 hours'),
(35,19,11,28,'pending',NULL,NULL,NOW()-INTERVAL '1 day',NULL,NOW()+INTERVAL '25 minutes'),
(36,20,13,26,'rejected',2,'Requested seat was unavailable',NOW()-INTERVAL '1 day',NOW()-INTERVAL '20 hours',NOW()-INTERVAL '20 hours'),
(37,21,17,29,'processed',3,'Equivalent seat approved',NOW()-INTERVAL '30 hours',NOW()-INTERVAL '28 hours',NOW()-INTERVAL '28 hours'),
(38,22,20,27,'pending',NULL,NULL,NOW()-INTERVAL '20 hours',NULL,NOW()+INTERVAL '30 minutes'),
(39,23,24,30,'processed',4,'Equivalent seat approved',NOW()-INTERVAL '18 hours',NOW()-INTERVAL '16 hours',NOW()-INTERVAL '16 hours'),
(40,24,31,32,'rejected',5,'Seat blocked by organizer',NOW()-INTERVAL '10 hours',NOW()-INTERVAL '8 hours',NOW()-INTERVAL '8 hours'),
(41,25,33,34,'processed',1,'Equivalent seat approved',NOW()-INTERVAL '8 hours',NOW()-INTERVAL '6 hours',NOW()-INTERVAL '6 hours'),
(42,18,35,36,'pending',NULL,NULL,NOW()-INTERVAL '6 hours',NULL,NOW()+INTERVAL '35 minutes'),
(43,19,37,38,'processed',2,'Equivalent seat approved',NOW()-INTERVAL '5 hours',NOW()-INTERVAL '4 hours',NOW()-INTERVAL '4 hours')
)
INSERT INTO seat_change_requests
(reservation_id,requested_by,old_ticket_id,requested_ticket_id,quantity,
 old_unit_price,new_unit_price,target_hold_expires_at,status,reviewed_by,
 review_note,requested_at,reviewed_at)
SELECT cs.reservation_id,cs.requested_by,cs.old_ticket_id,cs.requested_ticket_id,
       r.quantity,ot.price,nt.price,cs.target_hold_expires_at,cs.status,
       cs.reviewed_by,cs.review_note,cs.requested_at,cs.reviewed_at
FROM change_seed cs
JOIN reservations r ON r.id=cs.reservation_id
JOIN tickets ot ON ot.id=cs.old_ticket_id
JOIN tickets nt ON nt.id=cs.requested_ticket_id
ORDER BY cs.reservation_id;

WITH pending_change_holds AS (
    SELECT requested_ticket_id,SUM(quantity)::INTEGER AS qty
    FROM seat_change_requests
    WHERE status='pending'
    GROUP BY requested_ticket_id
)
UPDATE tickets t
SET change_held_quantity=pch.qty
FROM pending_change_holds pch
WHERE t.id=pch.requested_ticket_id;

INSERT INTO issued_tickets (reservation_id,status,issued_at,used_at)
SELECT
    r.id,
    CASE
        WHEN r.status='refunded' THEN 'canceled'
        WHEN m.starts_at < NOW() THEN 'used'
        ELSE 'active'
    END,
    r.paid_at,
    CASE WHEN r.status='paid' AND m.starts_at < NOW() THEN m.starts_at+INTERVAL '30 minutes' ELSE NULL END
FROM reservations r
JOIN tickets t ON t.id=r.ticket_id
JOIN matches m ON m.id=t.match_id
CROSS JOIN LATERAL generate_series(1,r.quantity) AS g(n)
WHERE r.status IN ('paid','refunded');

INSERT INTO report_categories (code,name) VALUES
('payment_issue','Payment Issue'),
('wrong_match_info','Incorrect Match Information'),
('seat_problem','Seat Assignment Problem'),
('unexpected_cancellation','Unexpected Cancellation'),
('price_issue','Pricing Issue'),
('refund_delay','Refund Delay'),
('venue_problem','Venue Problem'),
('accessibility','Accessibility Issue'),
('ticket_delivery','Ticket Delivery Problem'),
('other','Other');

WITH report_seed
(reporter_id,ticket_id,reservation_id,category_id,subject,description,status,assigned_to,support_response,created_at,updated_at,resolved_at)
AS (
VALUES
(6,1,1,1,'Payment deducted twice','The card was charged twice for one reservation.','resolved',1,'Duplicate authorization was released.',NOW()-INTERVAL '19 days',NOW()-INTERVAL '18 days',NOW()-INTERVAL '18 days'),
(7,4,2,2,'Wrong kickoff time','The kickoff time shown in the app was incorrect.','resolved',2,'Match time was corrected.',NOW()-INTERVAL '17 days',NOW()-INTERVAL '16 days',NOW()-INTERVAL '16 days'),
(8,6,3,3,'Seat information missing','The selected section was not visible.','pending',NULL,NULL,NOW()-INTERVAL '14 days',NOW()-INTERVAL '14 days',NULL),
(9,7,4,5,'Price mismatch','Checkout price differed from listing.','in_review',1,NULL,NOW()-INTERVAL '11 days',NOW()-INTERVAL '10 days',NULL),
(10,8,5,7,'Venue gate issue','The gate number was not clear.','resolved',3,'Gate details were updated.',NOW()-INTERVAL '9 days',NOW()-INTERVAL '8 days',NOW()-INTERVAL '8 days'),
(11,12,6,2,'Wrong venue address','The venue address needs correction.','pending',NULL,NULL,NOW()-INTERVAL '7 days',NOW()-INTERVAL '7 days',NULL),
(12,14,7,3,'Section mismatch','The section code did not match the hall map.','pending',NULL,NULL,NOW()-INTERVAL '6 days',NOW()-INTERVAL '6 days',NULL),
(13,15,8,1,'Payment confirmation delay','Payment succeeded but confirmation was delayed.','resolved',4,'Payment was reconciled.',NOW()-INTERVAL '5 days',NOW()-INTERVAL '4 days',NOW()-INTERVAL '4 days'),
(15,18,10,4,'Cancellation rules unclear','The cancellation rules were not visible.','pending',NULL,NULL,NOW()-INTERVAL '3 days',NOW()-INTERVAL '3 days',NULL),
(16,19,11,2,'Wrong sport label','The sport label was incorrect.','pending',NULL,NULL,NOW()-INTERVAL '2 days',NOW()-INTERVAL '2 days',NULL),
(17,21,12,3,'VIP separation issue','VIP seats were not properly separated.','resolved',5,'Organizer was notified.',NOW()-INTERVAL '1 day',NOW()-INTERVAL '12 hours',NOW()-INTERVAL '12 hours'),
(20,25,15,1,'Wallet deduction issue','Wallet balance changed unexpectedly.','pending',NULL,NULL,NOW()-INTERVAL '5 hours',NOW()-INTERVAL '5 hours',NULL),
(8,19,18,6,'Refund delay','Refund has not appeared in the wallet.','in_review',2,NULL,NOW()-INTERVAL '4 days',NOW()-INTERVAL '3 days',NULL),
(9,4,19,2,'Home and away teams swapped','Team order is incorrect.','pending',NULL,NULL,NOW()-INTERVAL '11 hours',NOW()-INTERVAL '11 hours',NULL),
(6,12,16,3,'Seat already occupied','The assigned seat was already occupied.','resolved',1,'A replacement seat was issued.',NOW()-INTERVAL '8 days',NOW()-INTERVAL '7 days',NOW()-INTERVAL '7 days'),
(18,3,34,9,'QR code delivery delay','The QR code arrived late.','resolved',3,'Ticket was reissued.',NOW()-INTERVAL '2 days',NOW()-INTERVAL '1 day',NOW()-INTERVAL '1 day'),
(19,11,35,8,'Accessibility path blocked','Accessible entrance was blocked.','in_review',4,NULL,NOW()-INTERVAL '1 day',NOW()-INTERVAL '20 hours',NULL),
(20,13,36,5,'VIP price not clear','VIP surcharge was not explained.','pending',NULL,NULL,NOW()-INTERVAL '18 hours',NOW()-INTERVAL '18 hours',NULL),
(21,29,37,7,'Parking directions missing','Parking directions were missing.','resolved',5,'Directions were added.',NOW()-INTERVAL '12 hours',NOW()-INTERVAL '8 hours',NOW()-INTERVAL '8 hours'),
(22,20,38,10,'General feedback','Please add a clearer seat map.','pending',NULL,NULL,NOW()-INTERVAL '6 hours',NOW()-INTERVAL '6 hours',NULL)
)
INSERT INTO reports
(reporter_id,ticket_id,reservation_id,payment_id,category_id,subject,description,status,assigned_to,support_response,created_at,updated_at,resolved_at)
SELECT rs.reporter_id,rs.ticket_id,rs.reservation_id,p.id,rs.category_id,rs.subject,rs.description,
       rs.status,rs.assigned_to,rs.support_response,rs.created_at,rs.updated_at,rs.resolved_at
FROM report_seed rs
JOIN payments p ON p.reservation_id=rs.reservation_id AND p.status='successful'
ORDER BY rs.reservation_id;

INSERT INTO reports
(reporter_id,ticket_id,reservation_id,payment_id,category_id,subject,description,status,created_at,updated_at)
VALUES
(7,1,NULL,NULL,2,'Listing time needs confirmation','Please confirm the kickoff time shown on the listing.','pending',NOW()-INTERVAL '3 hours',NOW()-INTERVAL '3 hours'),
(8,1,NULL,NULL,5,'Price display question','The fee breakdown should be clearer before purchase.','pending',NOW()-INTERVAL '2 hours',NOW()-INTERVAL '2 hours'),
(9,1,NULL,NULL,7,'Venue entrance information','Please add the recommended entrance gate.','pending',NOW()-INTERVAL '1 hour',NOW()-INTERVAL '1 hour');

COMMIT;
