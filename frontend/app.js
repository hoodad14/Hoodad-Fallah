/* ArenaPass Frontend v1.7.0
 * Vanilla HTML/CSS/JavaScript client for ArenaPass Backend v3.1.0.
 * No framework and no external runtime dependency.
 */
'use strict';

function resolveDefaultApiBase() {
  // The Docker frontend always proxies /api to the backend, regardless of the
  // host port (8080, 8081, ...). Same-origin avoids CORS and fixes auth on a
  // custom FRONTEND_HOST_PORT.
  if (location.protocol === 'http:' || location.protocol === 'https:') return '/api/v1';
  return 'http://127.0.0.1:8000/api/v1';
}

function normalizeApiBase(value) {
  const base = String(value || '').trim().replace(/\/+$/, '');
  if (!base) throw new Error('آدرس API نمی‌تواند خالی باشد.');
  if (base.startsWith('/')) return base;
  let parsed;
  try { parsed = new URL(base); } catch { throw new Error('آدرس API معتبر نیست.'); }
  if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('آدرس API باید با http یا https شروع شود.');
  return base;
}

function apiBaseCandidates() {
  const saved = localStorage.getItem('arenapass_api_base');
  const candidates = [resolveDefaultApiBase(), saved];
  if (location.protocol === 'http:' || location.protocol === 'https:') {
    candidates.push(`${location.protocol}//${location.hostname}:8000/api/v1`);
  }
  candidates.push('http://127.0.0.1:8000/api/v1');
  return [...new Set(candidates.filter(Boolean).map(value => {
    try { return normalizeApiBase(value); } catch { return null; }
  }).filter(Boolean))];
}

const DEFAULT_API_BASE = resolveDefaultApiBase();
const appState = {
  apiBase: DEFAULT_API_BASE,
  online: false,
  readiness: null,
  previewMode: false,
  user: null,
  profile: null,
  lookups: { cities: [], venues: [], sports: [], categories: [], paymentMethods: [], reportCategories: [], amenities: [], matches: [] },
  tickets: [],
  ticketMeta: { page: 1, page_size: 9, total: 0, pages: 1 },
  currentTicket: null,
  accountTab: 'overview',
  supportTab: 'reservations',
  supportTickets: [],
  requestCount: 0,
  searchSequence: 0,
  timers: new Set(),
  authTimers: { otp: null, signup: null },
  authTimeouts: { otp: null, signup: null },
  pendingSignup: null,
  authCapabilities: { otp: { email: true, phone: false }, local_mailbox_url: '/mailpit/', email_transport: { mode: 'smtp' } },
  authBusy: false,
  chatPollTimer: null,
  chatUnreadTimer: null,
  chatConversation: null,
  supportChatConversationId: null,
};

// Complete county-level geography used in registration, profile and search.
// 485 entries: 482-source snapshot plus verified 1403 additions.
const IRAN_COUNTIES = Object.freeze([{"id":12300010,"name":"اسلامشهر","province_id":1,"province_name":"تهران"},{"id":12300019,"name":"بهارستان","province_id":1,"province_name":"تهران"},{"id":1,"name":"تهران","province_id":1,"province_name":"تهران"},{"id":1230002,"name":"دماوند","province_id":1,"province_name":"تهران"},{"id":12300012,"name":"رباط کریم","province_id":1,"province_name":"تهران"},{"id":2,"name":"ری","province_id":1,"province_name":"تهران"},{"id":3,"name":"شمیرانات","province_id":1,"province_name":"تهران"},{"id":1230009,"name":"شهریار","province_id":1,"province_name":"تهران"},{"id":12300014,"name":"فیروزکوه","province_id":1,"province_name":"تهران"},{"id":20,"name":"قدس","province_id":1,"province_name":"تهران"},{"id":12300021,"name":"قرچک","province_id":1,"province_name":"تهران"},{"id":12300017,"name":"ملارد","province_id":1,"province_name":"تهران"},{"id":1230006,"name":"ورامین","province_id":1,"province_name":"تهران"},{"id":12300013,"name":"پاکدشت","province_id":1,"province_name":"تهران"},{"id":12300020,"name":"پردیس","province_id":1,"province_name":"تهران"},{"id":12300018,"name":"پیشوا","province_id":1,"province_name":"تهران"},{"id":11000018,"name":"آران و بیدگل","province_id":2,"province_name":"اصفهان"},{"id":1100001,"name":"اردستان","province_id":2,"province_name":"اصفهان"},{"id":4,"name":"اصفهان","province_id":2,"province_name":"اصفهان"},{"id":11000022,"name":"برخوار","province_id":2,"province_name":"اصفهان"},{"id":11000024,"name":"بویین و میاندشت","province_id":2,"province_name":"اصفهان"},{"id":11000019,"name":"تیران وکرون","province_id":2,"province_name":"اصفهان"},{"id":11000026,"name":"جرقویه","province_id":2,"province_name":"اصفهان"},{"id":1100003,"name":"خمینی شهر","province_id":2,"province_name":"اصفهان"},{"id":1100004,"name":"خوانسار","province_id":2,"province_name":"اصفهان"},{"id":11000023,"name":"خور و بیابانک","province_id":2,"province_name":"اصفهان"},{"id":11000021,"name":"دهاقان","province_id":2,"province_name":"اصفهان"},{"id":1100005,"name":"سمیرم","province_id":2,"province_name":"اصفهان"},{"id":11000016,"name":"شاهین شهرو میمه","province_id":2,"province_name":"اصفهان"},{"id":1100009,"name":"شهرضا","province_id":2,"province_name":"اصفهان"},{"id":1100006,"name":"فریدن","province_id":2,"province_name":"اصفهان"},{"id":1100007,"name":"فریدونشهر","province_id":2,"province_name":"اصفهان"},{"id":1100008,"name":"فلاورجان","province_id":2,"province_name":"اصفهان"},{"id":19,"name":"لنجان","province_id":2,"province_name":"اصفهان"},{"id":11000017,"name":"مبارکه","province_id":2,"province_name":"اصفهان"},{"id":20000003,"name":"میمه و وزوان","province_id":2,"province_name":"اصفهان"},{"id":11000013,"name":"نایین","province_id":2,"province_name":"اصفهان"},{"id":6,"name":"نجف‌آباد","province_id":2,"province_name":"اصفهان"},{"id":11000015,"name":"نطنز","province_id":2,"province_name":"اصفهان"},{"id":11000028,"name":"هرند","province_id":2,"province_name":"اصفهان"},{"id":11000027,"name":"ورزنه","province_id":2,"province_name":"اصفهان"},{"id":11000020,"name":"چادگان","province_id":2,"province_name":"اصفهان"},{"id":5,"name":"کاشان","province_id":2,"province_name":"اصفهان"},{"id":11000025,"name":"کوهپایه","province_id":2,"province_name":"اصفهان"},{"id":11000011,"name":"گلپایگان","province_id":2,"province_name":"اصفهان"},{"id":1070001,"name":"آباده","province_id":3,"province_name":"فارس"},{"id":10700017,"name":"ارسنجان","province_id":3,"province_name":"فارس"},{"id":1070002,"name":"استهبان","province_id":3,"province_name":"فارس"},{"id":1070003,"name":"اقلید","province_id":3,"province_name":"فارس"},{"id":10700036,"name":"اوز","province_id":3,"province_name":"فارس"},{"id":10700035,"name":"بختگان","province_id":3,"province_name":"فارس"},{"id":10700016,"name":"بوانات","province_id":3,"province_name":"فارس"},{"id":10700031,"name":"بیضا","province_id":3,"province_name":"فارس"},{"id":9,"name":"جهرم","province_id":3,"province_name":"فارس"},{"id":10700037,"name":"جویم","province_id":3,"province_name":"فارس"},{"id":10700029,"name":"خرامه","province_id":3,"province_name":"فارس"},{"id":10700018,"name":"خرم بید","province_id":3,"province_name":"فارس"},{"id":10700034,"name":"خفر","province_id":3,"province_name":"فارس"},{"id":10700024,"name":"خنج","province_id":3,"province_name":"فارس"},{"id":1070005,"name":"داراب","province_id":3,"province_name":"فارس"},{"id":10700026,"name":"رستم","province_id":3,"province_name":"فارس"},{"id":10700030,"name":"زرقان","province_id":3,"province_name":"فارس"},{"id":10700019,"name":"زرین دشت","province_id":3,"province_name":"فارس"},{"id":10700025,"name":"سروستان","province_id":3,"province_name":"فارس"},{"id":10700032,"name":"سرچهان","province_id":3,"province_name":"فارس"},{"id":1070006,"name":"سپیدان","province_id":3,"province_name":"فارس"},{"id":7,"name":"شیراز","province_id":3,"province_name":"فارس"},{"id":10700022,"name":"فراشبند","province_id":3,"province_name":"فارس"},{"id":1070008,"name":"فسا","province_id":3,"province_name":"فارس"},{"id":1070009,"name":"فیروزآباد","province_id":3,"province_name":"فارس"},{"id":10700020,"name":"قیروکارزین","province_id":3,"province_name":"فارس"},{"id":10700011,"name":"لارستان","province_id":3,"province_name":"فارس"},{"id":10700015,"name":"لامرد","province_id":3,"province_name":"فارس"},{"id":8,"name":"مرودشت","province_id":3,"province_name":"فارس"},{"id":10700013,"name":"ممسنی","province_id":3,"province_name":"فارس"},{"id":10700021,"name":"مهر","province_id":3,"province_name":"فارس"},{"id":10700014,"name":"نی ریز","province_id":3,"province_name":"فارس"},{"id":10700023,"name":"پاسارگاد","province_id":3,"province_name":"فارس"},{"id":10700010,"name":"کازرون","province_id":3,"province_name":"فارس"},{"id":10700028,"name":"کوار","province_id":3,"province_name":"فارس"},{"id":10700033,"name":"کوه چنار","province_id":3,"province_name":"فارس"},{"id":10700027,"name":"گراش","province_id":3,"province_name":"فارس"},{"id":1300005,"name":"اشتهارد","province_id":4,"province_name":"البرز"},{"id":1300002,"name":"ساوجبلاغ","province_id":4,"province_name":"البرز"},{"id":1300004,"name":"طالقان","province_id":4,"province_name":"البرز"},{"id":1300006,"name":"فردیس","province_id":4,"province_name":"البرز"},{"id":1300003,"name":"نظرآباد","province_id":4,"province_name":"البرز"},{"id":1300007,"name":"چهارباغ","province_id":4,"province_name":"البرز"},{"id":10,"name":"کرج","province_id":4,"province_name":"البرز"},{"id":10300021,"name":"آذرشهر","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300022,"name":"اسکو","province_id":5,"province_name":"آذربایجان شرقی"},{"id":1030002,"name":"اهر","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300013,"name":"بستان آباد","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300012,"name":"بناب","province_id":5,"province_name":"آذربایجان شرقی"},{"id":11,"name":"تبریز","province_id":5,"province_name":"آذربایجان شرقی"},{"id":20000001,"name":"ترکمانچای","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300019,"name":"جلفا","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300026,"name":"خداآفرین","province_id":5,"province_name":"آذربایجان شرقی"},{"id":1030005,"name":"سراب","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300014,"name":"شبستر","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300025,"name":"عجب شیر","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300028,"name":"لیلان","province_id":5,"province_name":"آذربایجان شرقی"},{"id":1030006,"name":"مراغه","province_id":5,"province_name":"آذربایجان شرقی"},{"id":1030007,"name":"مرند","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300020,"name":"ملکان","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300010,"name":"میانه","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300016,"name":"هریس","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300011,"name":"هشترود","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300027,"name":"هوراند","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300024,"name":"ورزقان","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300023,"name":"چاراویماق","province_id":5,"province_name":"آذربایجان شرقی"},{"id":10300015,"name":"کلیبر","province_id":5,"province_name":"آذربایجان شرقی"},{"id":1210007,"name":"ابرکوه","province_id":6,"province_name":"یزد"},{"id":1210001,"name":"اردکان","province_id":6,"province_name":"یزد"},{"id":1210008,"name":"اشکذر","province_id":6,"province_name":"یزد"},{"id":1210002,"name":"بافق","province_id":6,"province_name":"یزد"},{"id":12100011,"name":"بهاباد","province_id":6,"province_name":"یزد"},{"id":1210003,"name":"تفت","province_id":6,"province_name":"یزد"},{"id":1210009,"name":"خاتم","province_id":6,"province_name":"یزد"},{"id":12100013,"name":"زارچ","province_id":6,"province_name":"یزد"},{"id":12100012,"name":"مروست","province_id":6,"province_name":"یزد"},{"id":1210004,"name":"مهریز","province_id":6,"province_name":"یزد"},{"id":1210006,"name":"میبد","province_id":6,"province_name":"یزد"},{"id":12,"name":"یزد","province_id":6,"province_name":"یزد"},{"id":10800023,"name":"ارزوییه","province_id":7,"province_name":"کرمان"},{"id":10800020,"name":"انار","province_id":7,"province_name":"کرمان"},{"id":1080001,"name":"بافت","province_id":7,"province_name":"کرمان"},{"id":10800010,"name":"بردسیر","province_id":7,"province_name":"کرمان"},{"id":1080002,"name":"بم","province_id":7,"province_name":"کرمان"},{"id":10800025,"name":"جازموریان","province_id":7,"province_name":"کرمان"},{"id":1080003,"name":"جیرفت","province_id":7,"province_name":"کرمان"},{"id":10800018,"name":"رابر","province_id":7,"province_name":"کرمان"},{"id":10800011,"name":"راور","province_id":7,"province_name":"کرمان"},{"id":1080004,"name":"رفسنجان","province_id":7,"province_name":"کرمان"},{"id":10800015,"name":"رودبارجنوب","province_id":7,"province_name":"کرمان"},{"id":10800017,"name":"ریگان","province_id":7,"province_name":"کرمان"},{"id":1080005,"name":"زرند","province_id":7,"province_name":"کرمان"},{"id":1080006,"name":"سیرجان","province_id":7,"province_name":"کرمان"},{"id":1080007,"name":"شهربابک","province_id":7,"province_name":"کرمان"},{"id":10800012,"name":"عنبرآباد","province_id":7,"province_name":"کرمان"},{"id":10800022,"name":"فاریاب","province_id":7,"province_name":"کرمان"},{"id":10800019,"name":"فهرج","province_id":7,"province_name":"کرمان"},{"id":10800016,"name":"قلعه گنج","province_id":7,"province_name":"کرمان"},{"id":10800013,"name":"منوجان","province_id":7,"province_name":"کرمان"},{"id":10800021,"name":"نرماشیر","province_id":7,"province_name":"کرمان"},{"id":13,"name":"کرمان","province_id":7,"province_name":"کرمان"},{"id":1080009,"name":"کهنوج","province_id":7,"province_name":"کرمان"},{"id":10800014,"name":"کوهبنان","province_id":7,"province_name":"کرمان"},{"id":10800024,"name":"گنبکی","province_id":7,"province_name":"کرمان"},{"id":10900037,"name":"باخرز","province_id":8,"province_name":"خراسان رضوی"},{"id":10900031,"name":"بجستان","province_id":8,"province_name":"خراسان رضوی"},{"id":10900023,"name":"بردسکن","province_id":8,"province_name":"خراسان رضوی"},{"id":1090004,"name":"تایباد","province_id":8,"province_name":"خراسان رضوی"},{"id":1090006,"name":"تربت جام","province_id":8,"province_name":"خراسان رضوی"},{"id":1090005,"name":"تربت حیدریه","province_id":8,"province_name":"خراسان رضوی"},{"id":10900034,"name":"جغتای","province_id":8,"province_name":"خراسان رضوی"},{"id":10900036,"name":"جوین","province_id":8,"province_name":"خراسان رضوی"},{"id":10900029,"name":"خلیل آباد","province_id":8,"province_name":"خراسان رضوی"},{"id":10900019,"name":"خواف","province_id":8,"province_name":"خراسان رضوی"},{"id":10900038,"name":"خوشاب","province_id":8,"province_name":"خراسان رضوی"},{"id":10900039,"name":"داورزن","province_id":8,"province_name":"خراسان رضوی"},{"id":1090007,"name":"درگز","province_id":8,"province_name":"خراسان رضوی"},{"id":10900027,"name":"رشتخوار","province_id":8,"province_name":"خراسان رضوی"},{"id":10900035,"name":"زاوه","province_id":8,"province_name":"خراسان رضوی"},{"id":10900042,"name":"زبرخان","province_id":8,"province_name":"خراسان رضوی"},{"id":1090008,"name":"سبزوار","province_id":8,"province_name":"خراسان رضوی"},{"id":10900020,"name":"سرخس","province_id":8,"province_name":"خراسان رضوی"},{"id":10900043,"name":"ششتمد","province_id":8,"province_name":"خراسان رضوی"},{"id":10900040,"name":"صالح آباد","province_id":8,"province_name":"خراسان رضوی"},{"id":10900032,"name":"طرقبه شاندیز","province_id":8,"province_name":"خراسان رضوی"},{"id":10900022,"name":"فریمان","province_id":8,"province_name":"خراسان رضوی"},{"id":10900033,"name":"فیروزه","province_id":8,"province_name":"خراسان رضوی"},{"id":10900013,"name":"قوچان","province_id":8,"province_name":"خراسان رضوی"},{"id":14,"name":"مشهد","province_id":8,"province_name":"خراسان رضوی"},{"id":10900030,"name":"مه ولات","province_id":8,"province_name":"خراسان رضوی"},{"id":10900045,"name":"میان جلگه","province_id":8,"province_name":"خراسان رضوی"},{"id":10900017,"name":"نیشابور","province_id":8,"province_name":"خراسان رضوی"},{"id":10900018,"name":"چناران","province_id":8,"province_name":"خراسان رضوی"},{"id":10900014,"name":"کاشمر","province_id":8,"province_name":"خراسان رضوی"},{"id":10900028,"name":"کلات","province_id":8,"province_name":"خراسان رضوی"},{"id":10900041,"name":"کوهسرخ","province_id":8,"province_name":"خراسان رضوی"},{"id":10900044,"name":"گلبهار","province_id":8,"province_name":"خراسان رضوی"},{"id":10900015,"name":"گناباد","province_id":8,"province_name":"خراسان رضوی"},{"id":16,"name":"آبادان","province_id":9,"province_name":"خوزستان"},{"id":10600026,"name":"آغاجاری","province_id":9,"province_name":"خوزستان"},{"id":10600016,"name":"امیدیه","province_id":9,"province_name":"خوزستان"},{"id":1060002,"name":"اندیمشک","province_id":9,"province_name":"خوزستان"},{"id":10600021,"name":"اندیکا","province_id":9,"province_name":"خوزستان"},{"id":15,"name":"اهواز","province_id":9,"province_name":"خوزستان"},{"id":1060004,"name":"ایذه","province_id":9,"province_name":"خوزستان"},{"id":10600015,"name":"باغ ملک","province_id":9,"province_name":"خوزستان"},{"id":10600024,"name":"باوی","province_id":9,"province_name":"خوزستان"},{"id":1060005,"name":"بندرماهشهر","province_id":9,"province_name":"خوزستان"},{"id":1060006,"name":"بهبهان","province_id":9,"province_name":"خوزستان"},{"id":10600025,"name":"حمیدیه","province_id":9,"province_name":"خوزستان"},{"id":1060007,"name":"خرمشهر","province_id":9,"province_name":"خوزستان"},{"id":1060008,"name":"دزفول","province_id":9,"province_name":"خوزستان"},{"id":10600029,"name":"دزپارت","province_id":9,"province_name":"خوزستان"},{"id":1060009,"name":"دشت آزادگان","province_id":9,"province_name":"خوزستان"},{"id":10600019,"name":"رامشیر","province_id":9,"province_name":"خوزستان"},{"id":10600010,"name":"رامهرمز","province_id":9,"province_name":"خوزستان"},{"id":10600011,"name":"شادگان","province_id":9,"province_name":"خوزستان"},{"id":10600014,"name":"شوش","province_id":9,"province_name":"خوزستان"},{"id":10600012,"name":"شوشتر","province_id":9,"province_name":"خوزستان"},{"id":10600030,"name":"صیدون","province_id":9,"province_name":"خوزستان"},{"id":10600017,"name":"لالی","province_id":9,"province_name":"خوزستان"},{"id":10600013,"name":"مسجدسلیمان","province_id":9,"province_name":"خوزستان"},{"id":10600022,"name":"هفتکل","province_id":9,"province_name":"خوزستان"},{"id":10600018,"name":"هندیجان","province_id":9,"province_name":"خوزستان"},{"id":10600023,"name":"هویزه","province_id":9,"province_name":"خوزستان"},{"id":10600027,"name":"کارون","province_id":9,"province_name":"خوزستان"},{"id":10600028,"name":"کرخه","province_id":9,"province_name":"خوزستان"},{"id":10600020,"name":"گتوند","province_id":9,"province_name":"خوزستان"},{"id":1020001,"name":"آمل","province_id":10,"province_name":"مازندران"},{"id":18,"name":"بابل","province_id":10,"province_name":"مازندران"},{"id":10200016,"name":"بابلسر","province_id":10,"province_name":"مازندران"},{"id":1020004,"name":"بهشهر","province_id":10,"province_name":"مازندران"},{"id":1020005,"name":"تنکابن","province_id":10,"province_name":"مازندران"},{"id":10200021,"name":"جویبار","province_id":10,"province_name":"مازندران"},{"id":1020006,"name":"رامسر","province_id":10,"province_name":"مازندران"},{"id":17,"name":"ساری","province_id":10,"province_name":"مازندران"},{"id":1020008,"name":"سوادکوه","province_id":10,"province_name":"مازندران"},{"id":10200027,"name":"سوادکوه شمالی","province_id":10,"province_name":"مازندران"},{"id":10200026,"name":"سیمرغ","province_id":10,"province_name":"مازندران"},{"id":10200024,"name":"عباس آباد","province_id":10,"province_name":"مازندران"},{"id":10200023,"name":"فریدونکنار","province_id":10,"province_name":"مازندران"},{"id":10200010,"name":"قایم شهر","province_id":10,"province_name":"مازندران"},{"id":10200018,"name":"محمودآباد","province_id":10,"province_name":"مازندران"},{"id":10200025,"name":"میاندورود","province_id":10,"province_name":"مازندران"},{"id":10200014,"name":"نور","province_id":10,"province_name":"مازندران"},{"id":10200015,"name":"نوشهر","province_id":10,"province_name":"مازندران"},{"id":10200019,"name":"نکا","province_id":10,"province_name":"مازندران"},{"id":10200020,"name":"چالوس","province_id":10,"province_name":"مازندران"},{"id":10200028,"name":"کلاردشت","province_id":10,"province_name":"مازندران"},{"id":10200022,"name":"گلوگاه","province_id":10,"province_name":"مازندران"},{"id":1000002,"name":"آشتیان","province_id":11,"province_name":"مرکزی"},{"id":1000001,"name":"اراک","province_id":11,"province_name":"مرکزی"},{"id":1000003,"name":"تفرش","province_id":11,"province_name":"مرکزی"},{"id":1000004,"name":"خمین","province_id":11,"province_name":"مرکزی"},{"id":10000012,"name":"خنداب","province_id":11,"province_name":"مرکزی"},{"id":1000005,"name":"دلیجان","province_id":11,"province_name":"مرکزی"},{"id":10000010,"name":"زرندیه","province_id":11,"province_name":"مرکزی"},{"id":1000006,"name":"ساوه","province_id":11,"province_name":"مرکزی"},{"id":1000007,"name":"شازند","province_id":11,"province_name":"مرکزی"},{"id":10000013,"name":"فراهان","province_id":11,"province_name":"مرکزی"},{"id":1000009,"name":"محلات","province_id":11,"province_name":"مرکزی"},{"id":10000011,"name":"کمیجان","province_id":11,"province_name":"مرکزی"},{"id":1010001,"name":"آستارا","province_id":12,"province_name":"گیلان"},{"id":1010002,"name":"آستانه اشرفیه","province_id":12,"province_name":"گیلان"},{"id":10100013,"name":"املش","province_id":12,"province_name":"گیلان"},{"id":1010003,"name":"بندرانزلی","province_id":12,"province_name":"گیلان"},{"id":10100017,"name":"خمام","province_id":12,"province_name":"گیلان"},{"id":1010005,"name":"رشت","province_id":12,"province_name":"گیلان"},{"id":10100014,"name":"رضوانشهر","province_id":12,"province_name":"گیلان"},{"id":1010006,"name":"رودبار","province_id":12,"province_name":"گیلان"},{"id":1010007,"name":"رودسر","province_id":12,"province_name":"گیلان"},{"id":10100015,"name":"سیاهکل","province_id":12,"province_name":"گیلان"},{"id":10100012,"name":"شفت","province_id":12,"province_name":"گیلان"},{"id":1010008,"name":"صومعه سرا","province_id":12,"province_name":"گیلان"},{"id":1010004,"name":"طوالش","province_id":12,"province_name":"گیلان"},{"id":1010009,"name":"فومن","province_id":12,"province_name":"گیلان"},{"id":10100011,"name":"لاهیجان","province_id":12,"province_name":"گیلان"},{"id":10100010,"name":"لنگرود","province_id":12,"province_name":"گیلان"},{"id":10100016,"name":"ماسال","province_id":12,"province_name":"گیلان"},{"id":1040001,"name":"ارومیه","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400013,"name":"اشنویه","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400019,"name":"باروق","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400010,"name":"بوکان","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400012,"name":"تکاب","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040003,"name":"خوی","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040004,"name":"سردشت","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040005,"name":"سلماس","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400011,"name":"شاهین دژ","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400017,"name":"شوط","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040006,"name":"ماکو","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040007,"name":"مهاباد","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040008,"name":"میاندوآب","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400020,"name":"میرآباد","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040009,"name":"نقده","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400015,"name":"پلدشت","province_id":13,"province_name":"آذربایجان غربی"},{"id":1040002,"name":"پیرانشهر","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400014,"name":"چالدران","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400016,"name":"چایپاره","province_id":13,"province_name":"آذربایجان غربی"},{"id":10400018,"name":"چهاربرج","province_id":13,"province_name":"آذربایجان غربی"},{"id":1050001,"name":"اسلام آبادغرب","province_id":14,"province_name":"کرمانشاه"},{"id":10500012,"name":"ثلاث باباجانی","province_id":14,"province_name":"کرمانشاه"},{"id":1050009,"name":"جوانرود","province_id":14,"province_name":"کرمانشاه"},{"id":10500013,"name":"دالاهو","province_id":14,"province_name":"کرمانشاه"},{"id":10500014,"name":"روانسر","province_id":14,"province_name":"کرمانشاه"},{"id":1050004,"name":"سرپل ذهاب","province_id":14,"province_name":"کرمانشاه"},{"id":1050005,"name":"سنقر","province_id":14,"province_name":"کرمانشاه"},{"id":10500010,"name":"صحنه","province_id":14,"province_name":"کرمانشاه"},{"id":1050006,"name":"قصرشیرین","province_id":14,"province_name":"کرمانشاه"},{"id":10500011,"name":"هرسین","province_id":14,"province_name":"کرمانشاه"},{"id":1050003,"name":"پاوه","province_id":14,"province_name":"کرمانشاه"},{"id":1050002,"name":"کرمانشاه","province_id":14,"province_name":"کرمانشاه"},{"id":1050007,"name":"کنگاور","province_id":14,"province_name":"کرمانشاه"},{"id":1050008,"name":"گیلانغرب","province_id":14,"province_name":"کرمانشاه"},{"id":1110001,"name":"ایرانشهر","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100020,"name":"بمپور","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100021,"name":"تفتان","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110003,"name":"خاش","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100022,"name":"دشتیاری","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100012,"name":"دلگان","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110008,"name":"راسک","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110004,"name":"زابل","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110005,"name":"زاهدان","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100026,"name":"زرآباد","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100010,"name":"زهک","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110006,"name":"سراوان","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100023,"name":"سرباز","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100014,"name":"سیب و سوران","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100019,"name":"فنوج","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100018,"name":"قصرقند","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100025,"name":"لاشار","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100013,"name":"مهرستان","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100017,"name":"میرجاوه","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100015,"name":"نیمروز","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110007,"name":"نیک شهر","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100016,"name":"هامون","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100011,"name":"هیرمند","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110002,"name":"چاه بهار","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1110009,"name":"کنارک","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":11100024,"name":"گلشن","province_id":15,"province_name":"سیستان و بلوچستان"},{"id":1120001,"name":"بانه","province_id":16,"province_name":"کردستان"},{"id":1120002,"name":"بیجار","province_id":16,"province_name":"کردستان"},{"id":11200010,"name":"دهگلان","province_id":16,"province_name":"کردستان"},{"id":1120007,"name":"دیواندره","province_id":16,"province_name":"کردستان"},{"id":1120009,"name":"سروآباد","province_id":16,"province_name":"کردستان"},{"id":1120003,"name":"سقز","province_id":16,"province_name":"کردستان"},{"id":1120004,"name":"سنندج","province_id":16,"province_name":"کردستان"},{"id":1120005,"name":"قروه","province_id":16,"province_name":"کردستان"},{"id":1120006,"name":"مریوان","province_id":16,"province_name":"کردستان"},{"id":1120008,"name":"کامیاران","province_id":16,"province_name":"کردستان"},{"id":1130006,"name":"اسدآباد","province_id":17,"province_name":"همدان"},{"id":1130007,"name":"بهار","province_id":17,"province_name":"همدان"},{"id":1130001,"name":"تویسرکان","province_id":17,"province_name":"همدان"},{"id":11300010,"name":"درگزین","province_id":17,"province_name":"همدان"},{"id":1130008,"name":"رزن","province_id":17,"province_name":"همدان"},{"id":1130009,"name":"فامنین","province_id":17,"province_name":"همدان"},{"id":1130002,"name":"ملایر","province_id":17,"province_name":"همدان"},{"id":1130003,"name":"نهاوند","province_id":17,"province_name":"همدان"},{"id":1130004,"name":"همدان","province_id":17,"province_name":"همدان"},{"id":1130005,"name":"کبودرآهنگ","province_id":17,"province_name":"همدان"},{"id":1140005,"name":"اردل","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140001,"name":"بروجن","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140009,"name":"بن","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":11400010,"name":"خانمیرزا","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140008,"name":"سامان","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140002,"name":"شهرکرد","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140003,"name":"فارسان","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":11400012,"name":"فرخ شهر","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":11400011,"name":"فلارد","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140004,"name":"لردگان","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140006,"name":"کوهرنگ","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1140007,"name":"کیار","province_id":18,"province_name":"چهارمحال و بختیاری"},{"id":1150007,"name":"ازنا","province_id":19,"province_name":"لرستان"},{"id":1150001,"name":"الیگودرز","province_id":19,"province_name":"لرستان"},{"id":1150002,"name":"بروجرد","province_id":19,"province_name":"لرستان"},{"id":1150003,"name":"خرم آباد","province_id":19,"province_name":"لرستان"},{"id":1150004,"name":"دلفان","province_id":19,"province_name":"لرستان"},{"id":1150005,"name":"دورود","province_id":19,"province_name":"لرستان"},{"id":11500011,"name":"رومشکان","province_id":19,"province_name":"لرستان"},{"id":1150009,"name":"سلسله","province_id":19,"province_name":"لرستان"},{"id":11500012,"name":"معمولان","province_id":19,"province_name":"لرستان"},{"id":1150008,"name":"پلدختر","province_id":19,"province_name":"لرستان"},{"id":11500010,"name":"چگنی","province_id":19,"province_name":"لرستان"},{"id":1150006,"name":"کوهدشت","province_id":19,"province_name":"لرستان"},{"id":1160006,"name":"آبدانان","province_id":20,"province_name":"ایلام"},{"id":1160001,"name":"ایلام","province_id":20,"province_name":"ایلام"},{"id":1160007,"name":"ایوان","province_id":20,"province_name":"ایلام"},{"id":11600010,"name":"بدره","province_id":20,"province_name":"ایلام"},{"id":1160002,"name":"دره شهر","province_id":20,"province_name":"ایلام"},{"id":1160003,"name":"دهلران","province_id":20,"province_name":"ایلام"},{"id":1160009,"name":"سیروان","province_id":20,"province_name":"ایلام"},{"id":1160008,"name":"ملکشاهی","province_id":20,"province_name":"ایلام"},{"id":1160005,"name":"مهران","province_id":20,"province_name":"ایلام"},{"id":11600011,"name":"هلیلان","province_id":20,"province_name":"ایلام"},{"id":1160004,"name":"چرداول","province_id":20,"province_name":"ایلام"},{"id":11600012,"name":"چوار","province_id":20,"province_name":"ایلام"},{"id":1170007,"name":"باشت","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170005,"name":"بهمیی","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170001,"name":"بویراحمد","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170004,"name":"دنا","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170008,"name":"لنده","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170009,"name":"مارگون","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170006,"name":"چرام","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170002,"name":"کهگیلویه","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1170003,"name":"گچساران","province_id":21,"province_name":"کهگیلویه و بویراحمد"},{"id":1180001,"name":"بوشهر","province_id":22,"province_name":"بوشهر"},{"id":1180002,"name":"تنگستان","province_id":22,"province_name":"بوشهر"},{"id":1180009,"name":"جم","province_id":22,"province_name":"بوشهر"},{"id":1180003,"name":"دشتستان","province_id":22,"province_name":"بوشهر"},{"id":1180004,"name":"دشتی","province_id":22,"province_name":"بوشهر"},{"id":1180005,"name":"دیر","province_id":22,"province_name":"بوشهر"},{"id":1180008,"name":"دیلم","province_id":22,"province_name":"بوشهر"},{"id":11800010,"name":"عسلویه","province_id":22,"province_name":"بوشهر"},{"id":1180006,"name":"کنگان","province_id":22,"province_name":"بوشهر"},{"id":1180007,"name":"گناوه","province_id":22,"province_name":"بوشهر"},{"id":1190001,"name":"ابهر","province_id":23,"province_name":"زنجان"},{"id":1190006,"name":"ایجرود","province_id":23,"province_name":"زنجان"},{"id":1190003,"name":"خدابنده","province_id":23,"province_name":"زنجان"},{"id":1190007,"name":"خرمدره","province_id":23,"province_name":"زنجان"},{"id":1190004,"name":"زنجان","province_id":23,"province_name":"زنجان"},{"id":11900010,"name":"سلطانیه","province_id":23,"province_name":"زنجان"},{"id":1190008,"name":"طارم","province_id":23,"province_name":"زنجان"},{"id":1190009,"name":"ماهنشان","province_id":23,"province_name":"زنجان"},{"id":1200006,"name":"آرادان","province_id":24,"province_name":"سمنان"},{"id":1200001,"name":"دامغان","province_id":24,"province_name":"سمنان"},{"id":1200008,"name":"سرخه","province_id":24,"province_name":"سمنان"},{"id":1200002,"name":"سمنان","province_id":24,"province_name":"سمنان"},{"id":1200003,"name":"شاهرود","province_id":24,"province_name":"سمنان"},{"id":1200005,"name":"مهدی شهر","province_id":24,"province_name":"سمنان"},{"id":1200007,"name":"میامی","province_id":24,"province_name":"سمنان"},{"id":1200004,"name":"گرمسار","province_id":24,"province_name":"سمنان"},{"id":1220001,"name":"ابوموسی","province_id":25,"province_name":"هرمزگان"},{"id":1220009,"name":"بستک","province_id":25,"province_name":"هرمزگان"},{"id":12200013,"name":"بشاگرد","province_id":25,"province_name":"هرمزگان"},{"id":1220002,"name":"بندر عباس","province_id":25,"province_name":"هرمزگان"},{"id":1220003,"name":"بندر لنگه","province_id":25,"province_name":"هرمزگان"},{"id":1220006,"name":"جاسک","province_id":25,"province_name":"هرمزگان"},{"id":1220008,"name":"حاجی آباد","province_id":25,"province_name":"هرمزگان"},{"id":12200010,"name":"خمیر","province_id":25,"province_name":"هرمزگان"},{"id":1220007,"name":"رودان","province_id":25,"province_name":"هرمزگان"},{"id":12200012,"name":"سیریک","province_id":25,"province_name":"هرمزگان"},{"id":1220004,"name":"قشم","province_id":25,"province_name":"هرمزگان"},{"id":1220005,"name":"میناب","province_id":25,"province_name":"هرمزگان"},{"id":12200011,"name":"پارسیان","province_id":25,"province_name":"هرمزگان"},{"id":1240001,"name":"اردبیل","province_id":26,"province_name":"اردبیل"},{"id":12400011,"name":"اصلاندوز","province_id":26,"province_name":"اردبیل"},{"id":12400012,"name":"انگوت","province_id":26,"province_name":"اردبیل"},{"id":1240002,"name":"بیله سوار","province_id":26,"province_name":"اردبیل"},{"id":1240003,"name":"خلخال","province_id":26,"province_name":"اردبیل"},{"id":12400010,"name":"سرعین","province_id":26,"province_name":"اردبیل"},{"id":1240004,"name":"مشگین شهر","province_id":26,"province_name":"اردبیل"},{"id":1240008,"name":"نمین","province_id":26,"province_name":"اردبیل"},{"id":1240009,"name":"نیر","province_id":26,"province_name":"اردبیل"},{"id":1240006,"name":"پارس آباد","province_id":26,"province_name":"اردبیل"},{"id":1240007,"name":"کوثر","province_id":26,"province_name":"اردبیل"},{"id":1240005,"name":"گرمی","province_id":26,"province_name":"اردبیل"},{"id":1250002,"name":"جعفرآباد","province_id":27,"province_name":"قم"},{"id":1250001,"name":"قم","province_id":27,"province_name":"قم"},{"id":1250003,"name":"کهک","province_id":27,"province_name":"قم"},{"id":1260004,"name":"آبیک","province_id":28,"province_name":"قزوین"},{"id":1260006,"name":"آوج","province_id":28,"province_name":"قزوین"},{"id":1260005,"name":"البرز","province_id":28,"province_name":"قزوین"},{"id":1260001,"name":"بویین زهرا","province_id":28,"province_name":"قزوین"},{"id":1260002,"name":"تاکستان","province_id":28,"province_name":"قزوین"},{"id":1260003,"name":"قزوین","province_id":28,"province_name":"قزوین"},{"id":12700010,"name":"آزادشهر","province_id":29,"province_name":"گلستان"},{"id":1270008,"name":"آق قلا","province_id":29,"province_name":"گلستان"},{"id":1270001,"name":"بندرگز","province_id":29,"province_name":"گلستان"},{"id":1270002,"name":"ترکمن","province_id":29,"province_name":"گلستان"},{"id":12700011,"name":"رامیان","province_id":29,"province_name":"گلستان"},{"id":1270003,"name":"علی آباد کتول","province_id":29,"province_name":"گلستان"},{"id":12700012,"name":"مراوه تپه","province_id":29,"province_name":"گلستان"},{"id":1270007,"name":"مینودشت","province_id":29,"province_name":"گلستان"},{"id":1270004,"name":"کردکوی","province_id":29,"province_name":"گلستان"},{"id":1270009,"name":"کلاله","province_id":29,"province_name":"گلستان"},{"id":12700014,"name":"گالیکش","province_id":29,"province_name":"گلستان"},{"id":1270005,"name":"گرگان","province_id":29,"province_name":"گلستان"},{"id":12700013,"name":"گمیشان","province_id":29,"province_name":"گلستان"},{"id":1270006,"name":"گنبدکاووس","province_id":29,"province_name":"گلستان"},{"id":1280001,"name":"اسفراین","province_id":30,"province_name":"خراسان شمالی"},{"id":1280009,"name":"بام و صفی آباد","province_id":30,"province_name":"خراسان شمالی"},{"id":1280002,"name":"بجنورد","province_id":30,"province_name":"خراسان شمالی"},{"id":1280003,"name":"جاجرم","province_id":30,"province_name":"خراسان شمالی"},{"id":1280008,"name":"راز و جرگلان","province_id":30,"province_name":"خراسان شمالی"},{"id":1280006,"name":"سملقان","province_id":30,"province_name":"خراسان شمالی"},{"id":1280004,"name":"شیروان","province_id":30,"province_name":"خراسان شمالی"},{"id":1280005,"name":"فاروج","province_id":30,"province_name":"خراسان شمالی"},{"id":12800010,"name":"مانه","province_id":30,"province_name":"خراسان شمالی"},{"id":1280007,"name":"گرمه","province_id":30,"province_name":"خراسان شمالی"},{"id":1290008,"name":"بشرویه","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290001,"name":"بیرجند","province_id":31,"province_name":"خراسان جنوبی"},{"id":12900010,"name":"خوسف","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290002,"name":"درمیان","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290009,"name":"زیرکوه","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290006,"name":"سرایان","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290003,"name":"سربیشه","province_id":31,"province_name":"خراسان جنوبی"},{"id":12900011,"name":"طبس","province_id":31,"province_name":"خراسان جنوبی"},{"id":20000002,"name":"عشق‌آباد","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290007,"name":"فردوس","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290004,"name":"قاینات","province_id":31,"province_name":"خراسان جنوبی"},{"id":1290005,"name":"نهبندان","province_id":31,"province_name":"خراسان جنوبی"}]);
const FRONTEND_SPORTS = new Set(['football', 'volleyball', 'basketball']);
const isFrontendSport = item => FRONTEND_SPORTS.has(String(item?.sport_code || item?.code || '').toLowerCase());

const MOCK = {
  cities: IRAN_COUNTIES,
  venues: [
    { id: 1, name: 'ورزشگاه آزادی', city_id: 1, city_name: 'تهران', province_name: 'تهران', capacity: 78000 },
    { id: 4, name: 'ورزشگاه نقش جهان', city_id: 4, city_name: 'اصفهان', province_name: 'اصفهان', capacity: 75000 },
    { id: 7, name: 'ورزشگاه پارس', city_id: 7, city_name: 'شیراز', province_name: 'فارس', capacity: 50000 },
  ],
  sports: [
    { id: 1, code: 'football', name: 'فوتبال' },
    { id: 2, code: 'volleyball', name: 'والیبال' },
    { id: 3, code: 'basketball', name: 'بسکتبال' },
  ],
  categories: [
    { id: 1, code: 'regular', name: 'عادی' },
    { id: 2, code: 'special', name: 'ویژه' },
    { id: 3, code: 'vip', name: 'VIP' },
  ],
  paymentMethods: [
    { id: 1, code: 'bank_card', name: 'کارت بانکی' },
    { id: 2, code: 'wallet', name: 'کیف پول' },
  ],
  reportCategories: [
    { id: 1, code: 'payment_issue', name: 'مشکل پرداخت' },
    { id: 2, code: 'seat_issue', name: 'مشکل جایگاه' },
    { id: 3, code: 'match_change', name: 'تغییر مسابقه' },
  ],
  tickets: [
    { ticket_id: 1, match_id: 1, sport_code: 'football', sport_name: 'فوتبال', home_team: 'پرسپولیس', away_team: 'استقلال', tournament_name: 'لیگ برتر خلیج فارس', starts_at: futureISO(10, 18, 30), venue_id: 1, venue_name: 'ورزشگاه آزادی', city_id: 1, city_name: 'تهران', province_name: 'تهران', category_code: 'regular', category_name: 'عادی', section_code: 'EAST', row_code: null, seat_code: null, is_numbered: false, price: '150000', available_quantity: 324, total_capacity: 500, sold_quantity: 176, amenities: 'پارکینگ، جایگاه مسقف' },
    { ticket_id: 2, match_id: 2, sport_code: 'football', sport_name: 'فوتبال', home_team: 'سپاهان', away_team: 'پرسپولیس', tournament_name: 'لیگ برتر خلیج فارس', starts_at: futureISO(15, 19, 0), venue_id: 4, venue_name: 'ورزشگاه نقش جهان', city_id: 4, city_name: 'اصفهان', province_name: 'اصفهان', category_code: 'vip', category_name: 'VIP', section_code: 'VIP-A', row_code: '1', seat_code: '1', is_numbered: true, price: '250000', available_quantity: 1, total_capacity: 1, sold_quantity: 0, amenities: 'ورودی اختصاصی، پذیرایی' },
    { ticket_id: 13, match_id: 9, sport_code: 'volleyball', sport_name: 'والیبال', home_team: 'پیکان', away_team: 'سایپا', tournament_name: 'سوپرلیگ والیبال', starts_at: futureISO(7, 17, 30), venue_id: 3, venue_name: 'سالن شهید شیرودی', city_id: 1, city_name: 'تهران', province_name: 'تهران', category_code: 'vip', category_name: 'کنار زمین', section_code: 'COURTSIDE', row_code: '1', seat_code: '1', is_numbered: true, price: '180000', available_quantity: 1, total_capacity: 1, sold_quantity: 0, amenities: 'نزدیکی به زمین، خدمات ویژه' },
    { ticket_id: 20, match_id: 15, sport_code: 'basketball', sport_name: 'بسکتبال', home_team: 'تهران بسکتبال', away_team: 'شیراز بسکتبال', tournament_name: 'سوپرلیگ بسکتبال', starts_at: futureISO(8, 20, 0), venue_id: 2, venue_name: 'ورزشگاه تختی', city_id: 1, city_name: 'تهران', province_name: 'تهران', category_code: 'regular', category_name: 'عادی', section_code: 'A', row_code: null, seat_code: null, is_numbered: false, price: '55000', available_quantity: 138, total_capacity: 200, sold_quantity: 62, amenities: 'بوفه، پارکینگ' },
    { ticket_id: 14, match_id: 10, sport_code: 'volleyball', sport_name: 'والیبال', home_team: 'شهداب یزد', away_team: 'پیکان', tournament_name: 'سوپرلیگ والیبال', starts_at: futureISO(12, 16, 0), venue_id: 4, venue_name: 'ورزشگاه نقش جهان', city_id: 4, city_name: 'اصفهان', province_name: 'اصفهان', category_code: 'regular', category_name: 'عادی', section_code: 'A', row_code: null, seat_code: null, is_numbered: false, price: '75000', available_quantity: 91, total_capacity: 180, sold_quantity: 89, amenities: 'ورودی عمومی' },
    { ticket_id: 7, match_id: 4, sport_code: 'football', sport_name: 'فوتبال', home_team: 'فجر سپاسی', away_team: 'پیکان', tournament_name: 'لیگ آزادگان', starts_at: futureISO(5, 18, 0), venue_id: 7, venue_name: 'ورزشگاه پارس', city_id: 7, city_name: 'شیراز', province_name: 'فارس', category_code: 'regular', category_name: 'عادی', section_code: 'MAIN', row_code: null, seat_code: null, is_numbered: false, price: '100000', available_quantity: 245, total_capacity: 300, sold_quantity: 55, amenities: 'پارکینگ' },
  ],
};

function futureISO(days, hour, minute) {
  const d = new Date();
  d.setDate(d.getDate() + days); d.setHours(hour, minute, 0, 0);
  return d.toISOString();
}

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
const attr = value => esc(value).replace(/`/g, '&#96;');
const uiLocale = () => window.ArenaI18n?.isEnglish ? 'en-US' : 'fa-IR';
const digitsFa = value => window.ArenaI18n?.isEnglish ? String(value ?? '') : String(value ?? '').replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);
const numberFa = value => new Intl.NumberFormat(uiLocale()).format(Number(value || 0));
const money = value => window.ArenaI18n?.isEnglish ? `${numberFa(Math.round(Number(value || 0)))} Toman` : `${numberFa(Math.round(Number(value || 0)))} تومان`;
const dateFa = (value, options = {}) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return esc(value);
  return new Intl.DateTimeFormat(uiLocale(), { year: 'numeric', month: 'long', day: 'numeric', hour: options.dateOnly ? undefined : '2-digit', minute: options.dateOnly ? undefined : '2-digit' }).format(date);
};
const timeFa = value => value ? new Intl.DateTimeFormat(uiLocale(), { hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '—';
const first = (arr, fallback = null) => Array.isArray(arr) && arr.length ? arr[0] : fallback;
const initials = user => `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}` || 'A';
const normalizeList = data => Array.isArray(data) ? data : (Array.isArray(data?.items) ? data.items : []);
const safeJson = value => { try { return typeof value === 'string' ? JSON.parse(value) : value; } catch { return value; } };
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const asciiDigits = value => String(value ?? '').replace(/[۰-۹]/g, d => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d))).replace(/[٠-٩]/g, d => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d)));


function safeSessionGet(key) {
  try { return sessionStorage.getItem(key); }
  catch (error) { console.warn('Session storage is unavailable.', error); return null; }
}
function safeSessionSet(key, value) {
  try { sessionStorage.setItem(key, value); return true; }
  catch (error) { console.warn('Session storage is unavailable.', error); return false; }
}
function safeSessionRemove(key) {
  try { sessionStorage.removeItem(key); }
  catch (error) { console.warn('Session storage is unavailable.', error); }
}
function safeMailboxUrl(value) {
  const fallback = '/mailpit/';
  try {
    const parsed = new URL(String(value || fallback), location.origin);
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.origin !== location.origin) return fallback;
    return `${parsed.pathname}${parsed.search}${parsed.hash}` || fallback;
  } catch { return fallback; }
}

function mailpitMessageUrl(mailboxUrl, messageId) {
  const base = safeMailboxUrl(mailboxUrl);
  const id = String(messageId || '').trim();
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return base;
  const root = base.endsWith('/') ? base : `${base}/`;
  return `${root}view/${encodeURIComponent(id)}.html`;
}

const I18N = {
  roles: { spectator: 'تماشاگر', support: 'پشتیبان' },
  sports: { football: 'فوتبال', volleyball: 'والیبال', basketball: 'بسکتبال', handball: 'هندبال', wrestling: 'کشتی', tennis: 'تنیس', table_tennis: 'تنیس روی میز', swimming: 'شنا', athletics: 'دوومیدانی' },
  statuses: { held: 'رزرو موقت', paid: 'پرداخت‌شده', canceled: 'لغوشده', expired: 'منقضی', refunded: 'مستردشده', pending: 'در انتظار', in_review: 'در حال بررسی', resolved: 'حل‌شده', rejected: 'ردشده', successful: 'موفق', failed: 'ناموفق', used: 'استفاده‌شده', issued: 'صادرشده', verified: 'تأییدشده', needs_correction: 'نیازمند اصلاح', not_reviewed: 'بررسی‌نشده', approved: 'تأییدشده', active: 'فعال', inactive: 'غیرفعال' },
};

class ApiClient {
  constructor() { this.refreshPromise = null; }
  async request(path, options = {}, retry = true) {
    const url = path.startsWith('http') ? path : `${appState.apiBase}${path}`;
    const method = options.method || 'GET';
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    const access = TokenStore.get('access_token');
    if (access && options.auth !== false) headers.Authorization = `Bearer ${access}`;
    if (options.body !== undefined && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeout || 15000);
    appState.requestCount += 1;
    if (options.loader) toggleGlobalLoader(true, options.loaderText);
    try {
      const response = await fetch(url, { method, headers, body: options.body === undefined ? undefined : (options.body instanceof FormData ? options.body : JSON.stringify(options.body)), signal: controller.signal });
      let payload = null;
      const type = response.headers.get('content-type') || '';
      if (type.includes('application/json')) payload = await response.json();
      if (response.status === 401 && retry && TokenStore.get('refresh_token') && !path.includes('/auth/token/refresh')) {
        const refreshed = await this.refresh();
        if (refreshed) return this.request(path, options, false);
      }
      if (!response.ok || payload?.success === false) {
        const error = new Error(payload?.error?.message || `خطای ارتباط با سرور (${response.status})`);
        error.status = response.status; error.code = payload?.error?.code || 'http_error'; error.details = payload?.error?.details; error.requestId = payload?.error?.request_id || response.headers.get('X-Request-ID');
        error.retryAfter = response.headers.get('Retry-After');
        throw error;
      }
      return payload?.data ?? payload;
    } catch (error) {
      if (error.name === 'AbortError') { const e = new Error('زمان پاسخ‌گویی سرور به پایان رسید.'); e.code = 'timeout'; throw e; }
      throw error;
    } finally {
      clearTimeout(timeout); appState.requestCount = Math.max(0, appState.requestCount - 1);
      if (options.loader) toggleGlobalLoader(false);
    }
  }
  async refresh() {
    if (this.refreshPromise) return this.refreshPromise;
    const refreshToken = TokenStore.get('refresh_token');
    if (!refreshToken) return false;
    this.refreshPromise = (async () => {
      try {
        const response = await fetch(`${appState.apiBase}/auth/token/refresh`, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }) });
        const payload = await response.json();
        if (!response.ok || !payload.success) throw new Error('refresh_failed');
        saveAuth(payload.data.user, payload.data.tokens, TokenStore.persistent());
        return true;
      } catch {
        clearAuth(false);
        return false;
      } finally { this.refreshPromise = null; }
    })();
    return this.refreshPromise;
  }
  get(path, options = {}) { return this.request(path, { ...options, method: 'GET' }); }
  post(path, body = {}, options = {}) { return this.request(path, { ...options, method: 'POST', body }); }
  patch(path, body = {}, options = {}) { return this.request(path, { ...options, method: 'PATCH', body }); }
  delete(path, options = {}) { return this.request(path, { ...options, method: 'DELETE' }); }
}
const api = new ApiClient();

const TokenStore = {
  stores: [localStorage, sessionStorage],
  persistent() { return localStorage.getItem('arenapass_persistent') === '1'; },
  set(key, value, persistent = false) { this.stores.forEach(s => s.removeItem(`arenapass_${key}`)); (persistent ? localStorage : sessionStorage).setItem(`arenapass_${key}`, value); localStorage.setItem('arenapass_persistent', persistent ? '1' : '0'); },
  get(key) { return sessionStorage.getItem(`arenapass_${key}`) || localStorage.getItem(`arenapass_${key}`); },
  clear() { ['access_token', 'refresh_token', 'user'].forEach(key => this.stores.forEach(s => s.removeItem(`arenapass_${key}`))); localStorage.removeItem('arenapass_persistent'); },
};

function saveAuth(user, tokens, persistent = false) {
  appState.user = user;
  TokenStore.set('access_token', tokens.access_token, persistent);
  TokenStore.set('refresh_token', tokens.refresh_token, persistent);
  TokenStore.set('user', JSON.stringify(user), persistent);
  updateAuthUI(); startChatPolling(); refreshSpectatorChat({ silent: true });
}
function restoreAuth() {
  const raw = TokenStore.get('user');
  if (raw) { try { appState.user = JSON.parse(raw); } catch { TokenStore.clear(); } }
  updateAuthUI();
}
async function clearAuth(callServer = true) {
  const refreshToken = TokenStore.get('refresh_token');
  if (callServer && TokenStore.get('access_token')) { try { await api.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {}, { timeout: 6000 }); } catch { /* local cleanup still required */ } }
  TokenStore.clear(); appState.user = null; appState.profile = null; clearInterval(appState.chatPollTimer); clearInterval(appState.chatUnreadTimer); appState.chatPollTimer=null; appState.chatUnreadTimer=null; setChatUnread(0); updateAuthUI();
}

function isAuthenticated() { return Boolean(appState.user && TokenStore.get('access_token')); }

function updateAuthUI() {
  const logged = isAuthenticated();
  $$('.auth-only').forEach(el => { el.hidden = !logged; });
  $$('.guest-only').forEach(el => { el.hidden = logged; });
  const support = logged && appState.user.role === 'support';
  const spectator = logged && appState.user.role === 'spectator';
  $$('.support-only').forEach(el => { el.hidden = !support; });
  $$('.spectator-only').forEach(el => { el.hidden = !spectator; });
  const dock = $('#supportChatDock');
  if (dock) dock.hidden = support;
  if (!logged) closeSupportChat();
  if (logged) {
    const name = `${appState.user.first_name || ''} ${appState.user.last_name || ''}`.trim() || 'کاربر MahTicket';
    $('#headerUserName').textContent = name;
    $('#headerUserRole').textContent = I18N.roles[appState.user.role] || appState.user.role;
    setAvatar($('#headerAvatar'), appState.user);
    setAvatar($('#dashboardAvatar'), appState.user);
    $('#dashboardName').textContent = name;
    $('#dashboardContact').textContent = appState.user.email || appState.user.phone || '—';
  }
}
function setAvatar(el, user) {
  if (!el) return;
  el.replaceChildren();
  if (!user?.profile_picture_url) { el.textContent = initials(user); return; }
  const image = document.createElement('img');
  image.alt = '';
  image.referrerPolicy = 'no-referrer';
  image.src = user.profile_picture_url;
  image.addEventListener('error', () => { el.replaceChildren(); el.textContent = initials(user); }, { once: true });
  el.append(image);
}

function toast(title, message = '', type = 'success', duration = 4500) {
  const region = $('#toastRegion');
  const el = document.createElement('div'); el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${type === 'error' ? '!' : type === 'warning' ? 'i' : '✓'}</span><div><b>${esc(title)}</b>${message ? `<p>${esc(message)}</p>` : ''}</div><button aria-label="بستن">×</button>`;
  region.append(el);
  const remove = () => { if (!el.isConnected) return; el.classList.add('removing'); setTimeout(() => el.remove(), 220); };
  el.querySelector('button').addEventListener('click', remove); setTimeout(remove, duration);
}
function toggleGlobalLoader(show, text = 'در حال پردازش درخواست...') { const el = $('#globalLoader'); el.hidden = !show; if (show) $('p', el).textContent = text || 'در حال پردازش درخواست...'; }
function showError(error, fallback = 'عملیات انجام نشد') { console.error(error); const parts = [error?.message || 'خطای پیش‌بینی‌نشده']; if (error?.retryAfter) parts.push(`تلاش مجدد پس از ${digitsFa(error.retryAfter)} ثانیه`); if (error?.requestId) parts.push(`شناسه پیگیری: ${error.requestId}`); toast(fallback, parts.join(' — '), 'error', 6500); }

function openDialog(dialog) { if (!dialog) return; dialog.showModal(); document.body.classList.add('dialog-open'); }
function closeDialog(dialog) { if (!dialog) return; dialog.close(); if (!$$('dialog[open]').length) document.body.classList.remove('dialog-open'); }
function closeAllDialogs() { $$('dialog[open]').forEach(d => d.close()); document.body.classList.remove('dialog-open'); }

function statusBadge(status) { const s = status || 'pending'; return `<span class="status-badge status-${attr(s)}">${esc(I18N.statuses[s] || s)}</span>`; }
function sportName(ticket) { return I18N.sports[ticket.sport_code] || ticket.sport_name || ticket.sport_code || 'ورزش'; }
function sportEmoji(code) { return ({ football: '⚽', volleyball: '🏐', basketball: '🏀', wrestling: '🤼', tennis: '🎾', swimming: '🏊' })[code] || '🏟️'; }
function ticketTeamClass(name) {
  const length = Array.from(String(name || '').trim()).length;
  if (length >= 24) return 'ticket-team is-very-long';
  if (length >= 17) return 'ticket-team is-long';
  return 'ticket-team';
}
function ticketCard(t) {
  const available = Number(t.available_quantity || 0);
  const location = [t.venue_name, t.city_name].filter(Boolean).join('، ');
  const homeTeam = String(t.home_team || '—');
  const awayTeam = String(t.away_team || '—');
  return `<article class="ticket-card" data-ticket-card="${attr(t.ticket_id)}">
    <div class="ticket-card-top">
      <div class="ticket-sport"><span><i></i>${esc(sportEmoji(t.sport_code))} ${esc(sportName(t))}</span><span title="${attr(t.tournament_name || '')}">${esc(t.tournament_name || '')}</span></div>
      <div class="ticket-teams" aria-label="${attr(`${homeTeam} مقابل ${awayTeam}`)}">
        <span class="${ticketTeamClass(homeTeam)} ticket-team-home" dir="auto" title="${attr(homeTeam)}">${esc(homeTeam)}</span>
        <em aria-hidden="true">مقابل</em>
        <span class="${ticketTeamClass(awayTeam)} ticket-team-away" dir="auto" title="${attr(awayTeam)}">${esc(awayTeam)}</span>
      </div>
    </div>
    <span class="availability ${available <= 5 ? 'low' : ''}">${available > 0 ? `${numberFa(available)} موجود` : 'ناموجود'}</span>
    <div class="ticket-card-body"><div class="ticket-meta">
      <span><svg viewBox="0 0 24 24"><path d="M7 2v3M17 2v3M3 9h18M5 4h14a2 2 0 0 1 2 2v15H3V6a2 2 0 0 1 2-2Z"/></svg><b>${esc(dateFa(t.starts_at, { dateOnly: true }))}</b></span>
      <span><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg><b>${esc(timeFa(t.starts_at))}</b></span>
      <span><svg viewBox="0 0 24 24"><path d="M12 21s7-4.4 7-11a7 7 0 1 0-14 0c0 6.6 7 11 7 11Z"/><circle cx="12" cy="10" r="2"/></svg><b>${esc(location)}</b></span>
      <span><svg viewBox="0 0 24 24"><path d="M4 8h16v12H4zM8 8V5h8v3"/></svg><b>${esc(t.category_name || t.category_code)} · ${esc(t.section_code || 'عمومی')}</b></span>
    </div><div class="ticket-tags"><span class="tag">${t.is_numbered ? 'صندلی شماره‌دار' : 'ورودی عمومی'}</span>${t.amenities ? `<span class="tag">${esc(String(t.amenities).split('،')[0].split(',')[0])}</span>` : ''}</div></div>
    <div class="ticket-card-footer"><div class="ticket-price"><small>قیمت هر بلیط</small><b>${money(t.price)}</b></div><button class="button button-primary" data-action="ticket-detail" data-id="${attr(t.ticket_id)}">مشاهده و رزرو</button></div>
  </article>`;
}

function syncOfflineBannerHeight() {
  const banner = $('#offlineBanner');
  const height = banner && !banner.hidden ? banner.offsetHeight : 0;
  document.documentElement.style.setProperty('--offline-banner-height', `${height}px`);
}

function updateConnectionUi(ready, details = null, message = '') {
  const banner = $('#offlineBanner');
  const footer = $('#footerServiceStatus');
  appState.readiness = details;
  if (ready) {
    banner.hidden = true;
    footer.className = 'service-status online';
    footer.innerHTML = '<span class="status-dot"></span><b>API، دیتابیس و Redis آماده‌اند</b>';
  } else {
    banner.hidden = false;
    $('#offlineBannerTitle').textContent = details ? 'زیرساخت هنوز آماده نیست.' : 'سرور در دسترس نیست.';
    $('#offlineBannerText').textContent = message || (details ? 'اتصال API برقرار است اما دیتابیس یا Redis آماده پاسخ‌گویی نیست.' : 'اطلاعات نمونه برای پیش‌نمایش رابط کاربری نمایش داده می‌شود و عملیات ثبت نمی‌شوند.');
    footer.className = 'service-status offline';
    footer.innerHTML = `<span class="status-dot"></span><b>${details ? 'وابستگی‌های سرویس آماده نیستند' : 'سرویس در دسترس نیست'}</b>`;
  }
  requestAnimationFrame(syncOfflineBannerHeight);
}

async function checkHealth({ discover = true } = {}) {
  const candidates = discover ? apiBaseCandidates() : [appState.apiBase];
  let lastError = null;
  for (const candidate of candidates) {
    appState.apiBase = candidate;
    try {
      const readiness = await api.get('/ready', { auth: false, timeout: 6500 });
      appState.online = true; appState.previewMode = false;
      updateConnectionUi(true, readiness);
      return true;
    } catch (error) {
      lastError = error;
      if (error.status === 503 && error.details) {
        appState.online = false; appState.previewMode = true;
        updateConnectionUi(false, error.details, 'API پاسخ می‌دهد، اما اتصال دیتابیس، Redis یا موتور جستجو کامل نشده است.');
        return false;
      }
    }
  }
  appState.online = false; appState.previewMode = true;
  updateConnectionUi(false, null, lastError?.message || 'اطلاعات نمونه برای پیش‌نمایش رابط کاربری نمایش داده می‌شود و عملیات ثبت نمی‌شوند.');
  return false;
}

async function loadLookups() {
  const fallback = { cities: MOCK.cities, venues: MOCK.venues, sports: MOCK.sports, categories: MOCK.categories, paymentMethods: MOCK.paymentMethods, reportCategories: MOCK.reportCategories, amenities: [], matches: [] };
  if (!appState.online) {
    Object.assign(appState.lookups, fallback);
    populateLookupFields(); return;
  }
  const specs = [
    ['cities', '/cities'], ['venues', '/venues'], ['sports', '/sports'], ['categories', '/ticket-categories'], ['paymentMethods', '/payment-methods'], ['reportCategories', '/report-categories'], ['amenities', '/amenities'], ['matches', '/matches?upcoming_only=true'],
  ];
  await Promise.all(specs.map(async ([key, path]) => {
    try {
      let items = normalizeList(await api.get(path, { auth: false }));
      if (key === 'cities') {
        const byId = new Map(IRAN_COUNTIES.map(item => [String(item.id), item]));
        items.forEach(item => byId.set(String(item.id), { ...byId.get(String(item.id)), ...item }));
        items = [...byId.values()];
      }
      if (key === 'sports') items = items.filter(isFrontendSport);
      if (key === 'matches') items = items.filter(isFrontendSport);
      appState.lookups[key] = items.length ? items : fallback[key];
    } catch (error) {
      console.warn(`Lookup ${key} failed`, error);
      appState.lookups[key] = fallback[key];
    }
  }));
  populateLookupFields();
}

function populateLookupFields() {
  fillSelect($('#sportFilter'), appState.lookups.sports.filter(isFrontendSport), 'همه ورزش‌ها', item => item.code, item => I18N.sports[item.code] || item.name);
  fillCitySelect($('#cityFilter'), appState.lookups.cities, 'همه شهرستان‌ها');
  fillSelect($('#venueFilter'), appState.lookups.venues, 'همه ورزشگاه‌ها', item => item.id, item => `${item.name}${item.city_name ? ` — ${item.city_name}` : ''}`);
  fillSelect($('#categoryFilter'), appState.lookups.categories, 'همه رده‌ها', item => item.code, item => item.name);
  fillCitySelect($('#signupCity'), appState.lookups.cities, 'انتخاب شهرستان (اختیاری)');
  enhanceAllCitySelects();
}
function cityOptionsHtml(items, placeholder, selectedValue = '') {
  const selected = String(selectedValue ?? '');
  const groups = new Map();
  [...items].sort((a, b) => String(a.province_name || '').localeCompare(String(b.province_name || ''), 'fa') || String(a.name || '').localeCompare(String(b.name || ''), 'fa')).forEach(item => {
    const province = item.province_name || 'سایر';
    if (!groups.has(province)) groups.set(province, []);
    groups.get(province).push(item);
  });
  return `<option value="">${esc(placeholder)}</option>${[...groups.entries()].map(([province, counties]) => `<optgroup label="استان ${attr(province)}">${counties.map(item => `<option value="${attr(item.id)}" ${String(item.id) === selected ? 'selected' : ''}>${esc(item.name)}</option>`).join('')}</optgroup>`).join('')}`;
}
function fillCitySelect(select, items, placeholder) {
  if (!select) return;
  const current = select.value;
  select.innerHTML = cityOptionsHtml(items, placeholder, current);
  if ([...select.options].some(option => option.value === current)) select.value = current;
  select._cityComboboxRefresh?.();
}

let cityComboboxCounter = 0;
function normalizeCityQuery(value) {
  return String(value || '')
    .toLocaleLowerCase('fa-IR')
    .replace(/[يى]/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/[ً-ٰٟ]/g, '')
    .replace(/[‌‏‪-‮]/g, ' ')
    .replace(/[-–—_,،()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
function enhanceAllCitySelects(root = document) {
  $$('select[name="city_id"]', root).forEach(enhanceCitySelect);
}
function enhanceCitySelect(select) {
  if (!select) return;
  if (select.dataset.searchableCity === '1') { select._cityComboboxRefresh?.(); return; }
  select.dataset.searchableCity = '1';

  const wrapper = document.createElement('div');
  wrapper.className = 'city-combobox';
  const input = document.createElement('input');
  input.type = 'search';
  input.className = 'city-combobox-input';
  input.autocomplete = 'off';
  input.spellcheck = false;
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-expanded', 'false');
  input.setAttribute('aria-haspopup', 'listbox');
  input.placeholder = select.options[0]?.textContent?.trim() || 'نام شهرستان را تایپ کن';

  const list = document.createElement('div');
  list.className = 'city-combobox-list';
  list.id = `city-combobox-list-${++cityComboboxCounter}`;
  list.setAttribute('role', 'listbox');
  list.hidden = true;
  input.setAttribute('aria-controls', list.id);

  select.before(wrapper);
  wrapper.append(input, select, list);
  select.classList.add('city-native-select');
  select.tabIndex = -1;
  select.setAttribute('aria-hidden', 'true');

  let items = [];
  let visibleItems = [];
  let activeIndex = -1;
  let committedValue = '';
  let committedLabel = '';

  const selectedOption = () => [...select.options].find(option => option.value === select.value);
  const closeList = () => {
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    activeIndex = -1;
  };
  const syncFromSelect = () => {
    const option = selectedOption();
    committedValue = option?.value || '';
    committedLabel = committedValue ? option.textContent.trim() : '';
    input.value = committedLabel;
    input.placeholder = select.options[0]?.textContent?.trim() || 'نام شهرستان را تایپ کن';
  };
  const rebuildItems = () => {
    items = [...select.options].filter(option => option.value).map(option => {
      const province = option.parentElement?.tagName === 'OPTGROUP'
        ? String(option.parentElement.label || '').replace(/^استان\s+/, '')
        : '';
      const name = option.textContent.trim();
      return {
        value: option.value,
        name,
        province,
        search: normalizeCityQuery(`${name} ${province}`),
        nameSearch: normalizeCityQuery(name),
      };
    });
    syncFromSelect();
  };
  const setActive = index => {
    const buttons = $$('.city-combobox-option', list);
    if (!buttons.length) { activeIndex = -1; return; }
    activeIndex = Math.max(0, Math.min(index, buttons.length - 1));
    buttons.forEach((button, i) => button.classList.toggle('active', i === activeIndex));
    const active = buttons[activeIndex];
    input.setAttribute('aria-activedescendant', active.id);
    active.scrollIntoView({ block: 'nearest' });
  };
  const renderList = query => {
    const normalized = normalizeCityQuery(query);
    visibleItems = items
      .filter(item => !normalized || item.search.includes(normalized))
      .sort((a, b) => {
        if (!normalized) return a.province.localeCompare(b.province, 'fa') || a.name.localeCompare(b.name, 'fa');
        const aScore = a.nameSearch === normalized ? 0 : a.nameSearch.startsWith(normalized) ? 1 : a.search.startsWith(normalized) ? 2 : 3;
        const bScore = b.nameSearch === normalized ? 0 : b.nameSearch.startsWith(normalized) ? 1 : b.search.startsWith(normalized) ? 2 : 3;
        return aScore - bScore || a.name.localeCompare(b.name, 'fa');
      })
      .slice(0, 40);
    list.innerHTML = visibleItems.length
      ? visibleItems.map((item, index) => `<button type="button" id="${list.id}-option-${index}" class="city-combobox-option" role="option" data-city-value="${attr(item.value)}"><b>${esc(item.name)}</b>${item.province ? `<small>استان ${esc(item.province)}</small>` : ''}</button>`).join('')
      : '<p class="city-combobox-empty">شهرستانی با این عبارت پیدا نشد.</p>';
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    activeIndex = -1;
    input.removeAttribute('aria-activedescendant');
  };
  const choose = item => {
    if (!item) return;
    select.value = item.value;
    committedValue = item.value;
    committedLabel = item.name;
    input.value = item.name;
    closeList();
    select.dispatchEvent(new Event('change', { bubbles: true }));
  };

  input.addEventListener('focus', () => { renderList(input.value === committedLabel ? '' : input.value); if (committedLabel) input.select(); });
  input.addEventListener('input', () => {
    if (!input.value.trim()) {
      select.value = '';
      committedValue = '';
      committedLabel = '';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }
    renderList(input.value);
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (list.hidden) renderList(input.value === committedLabel ? '' : input.value);
      setActive(activeIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (list.hidden) renderList(input.value === committedLabel ? '' : input.value);
      setActive(activeIndex <= 0 ? visibleItems.length - 1 : activeIndex - 1);
    } else if (event.key === 'Enter' && !list.hidden) {
      event.preventDefault();
      const exact = items.find(item => item.nameSearch === normalizeCityQuery(input.value));
      choose(visibleItems[activeIndex] || exact || visibleItems[0]);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      input.value = committedLabel;
      closeList();
    }
  });
  list.addEventListener('mousedown', event => {
    const button = event.target.closest('[data-city-value]');
    if (!button) return;
    event.preventDefault();
    choose(items.find(item => item.value === button.dataset.cityValue));
    input.focus();
  });
  input.addEventListener('blur', () => {
    window.setTimeout(() => {
      if (wrapper.contains(document.activeElement)) return;
      const exact = items.find(item => item.nameSearch === normalizeCityQuery(input.value));
      if (input.value.trim() && exact) choose(exact);
      else input.value = committedLabel;
      closeList();
    }, 100);
  });
  select.addEventListener('change', syncFromSelect);
  select.form?.addEventListener('reset', () => window.setTimeout(syncFromSelect, 0));
  document.addEventListener('pointerdown', event => { if (!wrapper.contains(event.target)) closeList(); });

  select._cityComboboxSync = syncFromSelect;
  select._cityComboboxRefresh = rebuildItems;
  rebuildItems();
}
function fillSelect(select, items, placeholder, valueFn = x => x.id, labelFn = x => x.name) {
  if (!select) return; const current = select.value;
  select.innerHTML = `<option value="">${esc(placeholder)}</option>${items.map(item => `<option value="${attr(valueFn(item))}">${esc(labelFn(item))}</option>`).join('')}`;
  if ([...select.options].some(o => o.value === current)) select.value = current;
}

async function updateVenueOptions(cityId, preserveValue = true) {
  const select = $('#venueFilter');
  const previous = preserveValue ? select.value : '';
  let venues = appState.lookups.venues;
  if (appState.online && cityId) {
    try { venues = normalizeList(await api.get(`/venues?city_id=${encodeURIComponent(cityId)}`, { auth: false })); }
    catch { /* use lookup cache */ }
  }
  if (cityId) venues = venues.filter(v => String(v.city_id) === String(cityId));
  fillSelect(select, venues, 'همه ورزشگاه‌ها', x => x.id, x => `${x.name}${x.city_name ? ` — ${x.city_name}` : ''}`);
  if (previous && [...select.options].some(option => option.value === previous)) select.value = previous;
}

function closeMobileMenu() {
  const menu = $('#mobileMenu');
  menu.hidden = true;
  $('#mobileMenuButton').setAttribute('aria-expanded', 'false');
}

function openFilterPanel() {
  $('#filterPanel').classList.add('open');
  $('#filterBackdrop').hidden = false;
  document.body.classList.add('filter-open');
  $('#closeFilterButton').focus({ preventScroll: true });
}

function closeFilterPanel() {
  $('#filterPanel').classList.remove('open');
  $('#filterBackdrop').hidden = true;
  document.body.classList.remove('filter-open');
}

function route() {
  closeAllDialogs(); closeMobileMenu(); closeFilterPanel(); clearTimers();
  const raw = location.hash.replace(/^#\/?/, '') || 'home';
  const [pathPart] = raw.split('?');
  const [page, sub] = pathPart.split('/');
  let target = ['home', 'tickets', 'my', 'support', 'help'].includes(page) ? page : 'home';
  if (target === 'my' && !isAuthenticated()) { target = 'home'; openAuth('password'); toast('ابتدا وارد شو', 'برای دسترسی به حساب کاربری باید وارد شوی.', 'warning'); }
  if (target === 'support' && (!isAuthenticated() || appState.user?.role !== 'support')) { target = isAuthenticated() ? 'my' : 'home'; toast('دسترسی محدود', 'این بخش فقط برای پشتیبان سیستم است.', 'error'); }
  $$('.page').forEach(p => p.hidden = p.dataset.page !== target);
  $$('[data-nav]').forEach(n => n.classList.toggle('active', n.dataset.nav === target));
  window.scrollTo({ top: 0, behavior: 'auto' });
  if (target === 'home') loadFeaturedTickets();
  if (target === 'tickets') { applyHashSearch(); searchTickets(); }
  if (target === 'my') { if (sub) appState.accountTab = sub; activateAccountTab(appState.accountTab); }
  if (target === 'support') { if (sub) appState.supportTab = sub; loadSupportDashboard(); }
  if (target === 'help' && sub) requestAnimationFrame(() => document.getElementById(sub)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
}

async function loadFeaturedTickets() {
  const root = $('#featuredTickets');
  try {
    let items, total;
    if (appState.online) { const raw = await rawGet('/tickets?page=1&page_size=6&ordering=starts_at'); items = normalizeList(raw.data); total = raw.meta?.total; }
    else { items = MOCK.tickets; total = items.length; }
    $('#heroTicketCount').textContent = `+${numberFa(total || items.length || 0)}`;
    root.innerHTML = items.slice(0, 6).map(ticketCard).join('');
  } catch (error) { root.innerHTML = MOCK.tickets.slice(0, 3).map(ticketCard).join(''); }
}

function formToObject(form) {
  const data = {};
  new FormData(form).forEach((value, key) => { if (value !== '') data[key] = value; });
  $$('input[type="checkbox"]', form).forEach(input => { if (input.name) data[input.name] = input.checked; });
  return data;
}
function dateStart(value) { return value ? `${value}T00:00:00+03:30` : ''; }
function dateEnd(value) { return value ? `${value}T23:59:59+03:30` : ''; }
function buildTicketQuery(page = 1) {
  const data = formToObject($('#ticketFilterForm'));
  if (data.date_from) data.date_from = dateStart(data.date_from);
  if (data.date_to) data.date_to = dateEnd(data.date_to);
  if (!data.numbered) delete data.numbered;
  data.ordering = $('#ticketOrdering').value;
  data.page = page; data.page_size = 9;
  const params = new URLSearchParams(); Object.entries(data).forEach(([k, v]) => { if (v !== '' && v !== false && v != null) params.set(k, v); });
  return params;
}
async function searchTickets(page = 1) {
  const sequence = ++appState.searchSequence;
  const root = $('#ticketResults');
  root.innerHTML = '<div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div>';
  $('#ticketsEmpty').hidden = true;
  try {
    let items, meta;
    if (appState.online) {
      const params = buildTicketQuery(page);
      // The API envelope keeps pagination metadata beside data, so use the raw helper once.
      const raw = await rawGet(`/tickets?${params}`);
      items = normalizeList(raw.data).filter(isFrontendSport); meta = raw.meta || { page, page_size: 9, total: items.length, pages: 1 };
    } else {
      ({ items, meta } = filterMockTickets(page));
    }
    if (sequence !== appState.searchSequence) return;
    appState.tickets = items; appState.ticketMeta = meta;
    root.innerHTML = items.map(ticketCard).join('');
    root.hidden = items.length === 0; $('#ticketsEmpty').hidden = items.length !== 0;
    $('#resultsCount').textContent = `${numberFa(items.length)} بلیط پیدا شد`;
    renderPagination(meta); renderActiveFilters();
  } catch (error) {
    if (sequence !== appState.searchSequence) return;
    root.innerHTML = ''; root.hidden = true; $('#ticketsEmpty').hidden = false; $('#resultsCount').textContent = 'خطا در دریافت نتایج'; showError(error, 'جستجوی بلیط ناموفق بود');
  }
}
async function rawGet(path, retry = true) {
  const url = path.startsWith('http') ? path : `${appState.apiBase}${path}`;
  const headers = { Accept: 'application/json' };
  const access = TokenStore.get('access_token');
  if (access) headers.Authorization = `Bearer ${access}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, { headers, signal: controller.signal });
    let payload = null;
    try { payload = await response.json(); } catch { payload = null; }
    if (response.status === 401 && retry && TokenStore.get('refresh_token')) {
      const refreshed = await api.refresh();
      if (refreshed) return rawGet(path, false);
    }
    if (!response.ok || payload?.success === false) {
      const error = new Error(payload?.error?.message || `خطا در دریافت اطلاعات (${response.status})`);
      error.status = response.status;
      error.code = payload?.error?.code || 'http_error';
      error.details = payload?.error?.details;
      error.requestId = payload?.error?.request_id || response.headers.get('X-Request-ID');
      error.retryAfter = response.headers.get('Retry-After');
      throw error;
    }
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') { const e = new Error('زمان پاسخ‌گویی سرور به پایان رسید.'); e.code = 'timeout'; throw e; }
    throw error;
  } finally { clearTimeout(timeout); }
}
function filterMockTickets(page = 1) {
  const data = formToObject($('#ticketFilterForm')); let items = [...MOCK.tickets];
  if (data.q) { const q = data.q.toLowerCase(); items = items.filter(t => [t.home_team, t.away_team, t.venue_name, t.tournament_name, t.city_name, t.sport_name].some(x => String(x).toLowerCase().includes(q))); }
  if (data.sport) items = items.filter(t => t.sport_code === data.sport);
  if (data.city_id) items = items.filter(t => String(t.city_id) === String(data.city_id));
  if (data.venue_id) items = items.filter(t => String(t.venue_id) === String(data.venue_id));
  if (data.category) items = items.filter(t => t.category_code === data.category);
  if (data.date_from) items = items.filter(t => new Date(t.starts_at) >= new Date(dateStart(data.date_from)));
  if (data.date_to) items = items.filter(t => new Date(t.starts_at) <= new Date(dateEnd(data.date_to)));
  if (data.price_min) items = items.filter(t => Number(t.price) >= Number(data.price_min));
  if (data.price_max) items = items.filter(t => Number(t.price) <= Number(data.price_max));
  if (data.min_available) items = items.filter(t => Number(t.available_quantity) >= Number(data.min_available));
  if (data.numbered) items = items.filter(t => t.is_numbered);
  const ordering = $('#ticketOrdering').value; const factor = ordering.startsWith('-') ? -1 : 1; const key = ordering.replace('-', '');
  items.sort((a, b) => { if (key === 'price') return (Number(a.price) - Number(b.price)) * factor; if (key === 'demand') return (Number(b.sold_quantity) - Number(a.sold_quantity)); if (key === 'availability') return Number(b.available_quantity) - Number(a.available_quantity); return (new Date(a.starts_at) - new Date(b.starts_at)) * factor; });
  const total = items.length, pageSize = 9, pages = Math.max(1, Math.ceil(total / pageSize));
  return { items: items.slice((page - 1) * pageSize, page * pageSize), meta: { page, page_size: pageSize, total, pages } };
}
function renderPagination(meta) {
  const root = $('#ticketPagination');
  const pages = Number(meta.pages || 1), current = Number(meta.page || 1);
  if (pages <= 1) { root.innerHTML = ''; return; }

  const visible = [];
  for (let p = Math.max(1, current - 2); p <= Math.min(pages, current + 2); p++) visible.push(p);

  root.innerHTML =
    `<button data-page="${current - 1}" aria-label="صفحه قبل" ${current <= 1 ? 'disabled' : ''}>‹</button>` +
    `${visible.map(p => `<button data-page="${p}" class="${p === current ? 'active' : ''}">${numberFa(p)}</button>`).join('')}` +
    `<button data-page="${current + 1}" aria-label="صفحه بعد" ${current >= pages ? 'disabled' : ''}>›</button>`;
}
function renderActiveFilters() {
  const data = formToObject($('#ticketFilterForm')); const labels = { q: 'جستجو', sport: 'ورزش', city_id: 'شهرستان', venue_id: 'ورزشگاه', category: 'رده', date_from: 'از تاریخ', date_to: 'تا تاریخ', price_min: 'حداقل قیمت', price_max: 'حداکثر قیمت', min_available: 'ظرفیت', numbered: 'شماره‌دار' };
  const root = $('#activeFilters'); root.innerHTML = Object.entries(data).filter(([, v]) => v !== '' && v !== false).map(([k, v]) => `<span class="filter-chip">${esc(labels[k] || k)}: ${esc(resolveFilterValue(k, v))}<button data-remove-filter="${attr(k)}">×</button></span>`).join('');
}
function resolveFilterValue(key, value) {
  const map = { sport: appState.lookups.sports, city_id: appState.lookups.cities, venue_id: appState.lookups.venues, category: appState.lookups.categories };
  if (!map[key]) return value === true ? 'بله' : value;
  const item = map[key].find(x => String(key === 'sport' || key === 'category' ? x.code : x.id) === String(value)); return item?.name || value;
}
async function clearFilters() { const form = $('#ticketFilterForm'); form.reset(); form.elements.city_id?._cityComboboxSync?.(); $('#ticketOrdering').value = 'starts_at'; await updateVenueOptions('', false); history.replaceState(null, '', '#/tickets'); searchTickets(1); closeFilterPanel(); }
function applyHashSearch() {
  const queryString = location.hash.includes('?') ? location.hash.split('?')[1] : '';
  const form = $('#ticketFilterForm');
  form.reset(); $('#ticketOrdering').value = 'starts_at';
  if (!queryString) { updateVenueOptions('', false); return; }
  const params = new URLSearchParams(queryString);
  params.forEach((value, key) => {
    if (key === 'ordering') { if ([...$('#ticketOrdering').options].some(o => o.value === value)) $('#ticketOrdering').value = value; return; }
    const input = form.elements[key];
    if (!input) return;
    if (input.type === 'checkbox') input.checked = ['1', 'true', 'yes', 'on'].includes(value.toLowerCase());
    else input.value = value;
  });
  form.elements.city_id?._cityComboboxSync?.();
  updateVenueOptions(form.elements.city_id.value, true);
}

async function showTicketDetail(id) {
  const dialog = $('#ticketDialog'); const root = $('#ticketDialogContent'); root.innerHTML = '<div class="dashboard-loading"><span class="spinner"></span> در حال دریافت جزئیات بلیط...</div>'; openDialog(dialog);
  try {
    let ticket;
    if (appState.online) ticket = await api.get(`/tickets/${id}`, { auth: false }); else ticket = MOCK.tickets.find(t => Number(t.ticket_id) === Number(id));
    if (!ticket) throw new Error('بلیط موردنظر پیدا نشد.');
    appState.currentTicket = ticket;
    const amenities = normalizeList(ticket.amenity_details).length ? normalizeList(ticket.amenity_details).map(a => a.name) : String(ticket.amenities || '').split(/[,،]/).filter(Boolean);
    root.innerHTML = `<div class="ticket-detail-hero"><div class="ticket-sport"><span>${sportEmoji(ticket.sport_code)} ${esc(sportName(ticket))}</span><span>${esc(ticket.tournament_name || '')}</span></div><h2>${esc(ticket.home_team)} <small>مقابل</small> ${esc(ticket.away_team)}</h2><p>${esc(ticket.venue_name)}، ${esc(ticket.city_name)} · ${esc(dateFa(ticket.starts_at))}</p></div>
      <div class="ticket-detail-grid"><div><div class="detail-list">
        <div class="detail-item"><small>رده بلیط</small><b>${esc(ticket.category_name || ticket.category_code)}</b></div><div class="detail-item"><small>بخش / سکو</small><b>${esc(ticket.section_code || 'عمومی')}</b></div>
        <div class="detail-item"><small>ردیف و صندلی</small><b>${ticket.is_numbered ? `${esc(ticket.row_code || '—')} / ${esc(ticket.seat_code || '—')}` : 'بدون شماره'}</b></div><div class="detail-item"><small>ظرفیت باقی‌مانده</small><b>${numberFa(ticket.available_quantity)} بلیط</b></div>
        <div class="detail-item"><small>زمان شروع</small><b>${esc(dateFa(ticket.starts_at))}</b></div><div class="detail-item"><small>محل برگزاری</small><b>${esc(ticket.venue_name)}</b></div>
      </div><div class="amenity-list">${amenities.map(a => `<span class="amenity-chip">✓ ${esc(a)}</span>`).join('') || '<span class="muted">امکانات ویژه‌ای ثبت نشده است.</span>'}</div></div>
      <aside class="purchase-box"><div class="purchase-price"><small>قیمت هر بلیط</small><b>${money(ticket.price)}</b></div><div class="quantity-control"><button data-qty="minus">−</button><b id="ticketQuantity">۱</b><button data-qty="plus">+</button></div><div class="confirm-summary"><div><span>تعداد</span><b id="quantityLabel">۱ بلیط</b></div><div><span>مبلغ کل</span><b id="ticketTotal">${money(ticket.price)}</b></div></div><button class="button button-accent button-block" data-action="reserve-current" ${Number(ticket.available_quantity) <= 0 ? 'disabled' : ''}>رزرو بلیط</button><p class="muted">رزرو پس از ثبت، فقط برای مدت تعیین‌شده توسط سرور معتبر است.</p></aside></div>`;
    root.dataset.quantity = '1';
  } catch (error) { root.innerHTML = `<div class="empty-state"><div class="empty-icon">!</div><h3>نمایش جزئیات ممکن نیست</h3><p>${esc(error.message)}</p></div>`; }
}
function changeTicketQuantity(delta) {
  const root = $('#ticketDialogContent'); if (!appState.currentTicket) return;
  let q = Number(root.dataset.quantity || 1) + delta; q = Math.max(1, Math.min(20, Number(appState.currentTicket.available_quantity || 1), q)); root.dataset.quantity = String(q);
  $('#ticketQuantity').textContent = numberFa(q); $('#quantityLabel').textContent = `${numberFa(q)} بلیط`; $('#ticketTotal').textContent = money(Number(appState.currentTicket.price) * q);
}
async function reserveCurrentTicket() {
  if (!ensureSpectator()) return;
  if (appState.previewMode) { toast('حالت پیش‌نمایش', 'برای ثبت رزرو، بک‌اند را اجرا کن.', 'warning'); return; }
  const quantity = Number($('#ticketDialogContent').dataset.quantity || 1); const ticket = appState.currentTicket;
  closeDialog($('#ticketDialog'));
  showFormDialog({ title: 'تأیید رزرو', description: 'پس از تأیید، ظرفیت انتخاب‌شده به‌صورت موقت برای تو قفل می‌شود.', body: `<div class="confirm-summary"><div><span>مسابقه</span><b>${esc(ticket.home_team)} - ${esc(ticket.away_team)}</b></div><div><span>جایگاه</span><b>${esc(ticket.category_name)} / ${esc(ticket.section_code)}</b></div><div><span>تعداد</span><b>${numberFa(quantity)}</b></div><div><span>مبلغ کل</span><b>${money(Number(ticket.price) * quantity)}</b></div></div>`, confirmText: 'ثبت رزرو', onConfirm: async () => { const result = await api.post('/reservations', { ticket_id: Number(ticket.ticket_id), quantity }, { loader: true, loaderText: 'در حال قفل کردن بلیط...' }); closeDialog($('#formDialog')); toast('رزرو با موفقیت ثبت شد', result.expires_at ? `مهلت پرداخت تا ${dateFa(result.expires_at)}` : 'برای پرداخت به پنل رزروها برو.'); location.hash = '#/my/reservations'; } });
}
function ensureAuth() { if (isAuthenticated()) return true; clearAuth(false); openAuth('password'); toast('ورود لازم است', 'برای ادامه وارد حساب کاربری شو.', 'warning'); return false; }
function ensureSpectator() { if (!ensureAuth()) return false; if (appState.user.role !== 'spectator') { toast('عملیات مخصوص تماشاگر', 'حساب پشتیبان امکان خرید بلیط ندارد.', 'warning'); return false; } return true; }

function requireValidForm(form) {
  if (form.checkValidity()) return true;
  form.reportValidity();
  return false;
}

function clearAuthTimer(name) {
  if (appState.authTimers[name]) clearInterval(appState.authTimers[name]);
  if (appState.authTimeouts[name]) clearTimeout(appState.authTimeouts[name]);
  appState.authTimers[name] = null;
  appState.authTimeouts[name] = null;
}

function startAuthCountdown(name, seconds, element, onDone = null) {
  clearAuthTimer(name);
  let remaining = Math.max(0, Number(seconds || 0));
  const render = () => {
    if (remaining <= 0) {
      element.textContent = 'مهلت این کد تمام شده یا امکان ارسال مجدد فراهم است.';
      clearAuthTimer(name);
      if (onDone) onDone();
      return;
    }
    const minutes = Math.floor(remaining / 60);
    const secs = String(remaining % 60).padStart(2, '0');
    element.textContent = `اعتبار کد: ${digitsFa(minutes)}:${digitsFa(secs)}`;
    remaining -= 1;
  };
  render();
  appState.authTimers[name] = setInterval(render, 1000);
}

function setAuthMessage(scope, message = '', type = '') {
  const el = $(`#${scope}FlowMessage`);
  if (!el) return;
  el.hidden = !message;
  el.className = `auth-flow-message${type ? ` ${type}` : ''}`;
  el.textContent = message;
}

function authErrorMessage(error, fallback) {
  const messages = {
    otp_delivery_failed: 'ارسال ایمیل کد تأیید انجام نشد. تنظیمات سرویس ایمیل را بررسی کن و دوباره تلاش کن.',
    otp_delivery_unavailable: 'ارسال کد برای این روش فعال نیست. در اجرای محلی روش ایمیل را انتخاب کن.',
    otp_cooldown: 'کد به‌تازگی ارسال شده است؛ چند ثانیه صبر کن و سپس ارسال مجدد را بزن.',
    rate_limited: 'تعداد درخواست‌ها زیاد شده است؛ کمی بعد دوباره تلاش کن.',
    conflict: 'قبلاً حسابی با این ایمیل یا شماره تلفن ساخته شده است.',
    signup_expired: 'فرآیند ثبت‌نام منقضی شده است؛ اطلاعات را دوباره ارسال کن.',
    otp_invalid: 'کد واردشده صحیح نیست.',
    otp_expired: 'کد منقضی شده است؛ یک کد جدید درخواست کن.',
    account_not_found: 'هیچ حسابی با این ایمیل یا شماره تلفن وجود ندارد. ابتدا ثبت‌نام کن.',
    account_inactive: 'این حساب غیرفعال است؛ برای بررسی با پشتیبانی تماس بگیر.',
  };
  return messages[error?.code] || error?.message || fallback;
}

async function loadAuthCapabilities() {
  if (!appState.online) return;
  try {
    const capabilities = await api.get('/auth/capabilities', { auth: false, timeout: 7000 });
    appState.authCapabilities = capabilities || appState.authCapabilities;
    const phoneOption = $('#signupPhoneOtpOption');
    const phoneReady = Boolean(capabilities?.otp?.phone);
    if (phoneOption) {
      phoneOption.disabled = !phoneReady;
      phoneOption.textContent = phoneReady ? 'شماره تلفن' : 'شماره تلفن (ارسال پیامک تنظیم نشده)';
    }
    const preferred = $('#signupPreferredLogin');
    if (preferred && preferred.value === 'phone' && !phoneReady) preferred.value = 'email';
    const hasLocalMailbox = Boolean(capabilities?.local_mailbox_url);
    const mailbox = hasLocalMailbox ? safeMailboxUrl(capabilities.local_mailbox_url) : '';
    $$('.mailpit-inbox-link').forEach(link => {
      if (hasLocalMailbox) link.href = mailbox;
      link.hidden = !hasLocalMailbox;
    });
    $$('.mailpit-only').forEach(element => { element.hidden = !hasLocalMailbox; });
    if (capabilities?.email_transport?.configured && !capabilities?.email_transport?.ready) {
      setAuthMessage('signup', 'سرویس ایمیل در بررسی اولیه آماده نبود؛ هنگام ارسال کد دوباره به‌صورت قطعی بررسی می‌شود.', 'warning');
      setAuthMessage('otp', 'سرویس ایمیل در بررسی اولیه آماده نبود؛ هنگام ارسال کد دوباره به‌صورت قطعی بررسی می‌شود.', 'warning');
    }
  } catch (error) {
    console.warn('Auth capabilities unavailable', error);
  }
}

function openAuth(tab = 'password') { activateAuthTab(tab); openDialog($('#authDialog')); }
function activateAuthTab(tab) {
  $$('[data-auth-tab]').forEach(b => {
    const active = b.dataset.authTab === tab;
    b.classList.toggle('active', active);
    b.setAttribute('aria-selected', String(active));
  });
  $$('[data-auth-panel]').forEach(p => { p.hidden = p.dataset.authPanel !== tab; });
}

async function handlePasswordLogin(form) {
  if (!requireValidForm(form)) return;
  const data = formToObject(form); const remember = Boolean(data.remember); delete data.remember;
  try {
    const result = await api.post('/auth/password/login', data, { auth: false, loader: true, loaderText: 'در حال ورود امن...' });
    saveAuth(result.user, result.tokens, remember);
    form.reset();
    closeDialog($('#authDialog'));
    toast('خوش آمدی', `${result.user.first_name || ''}، ورود با موفقیت انجام شد.`);
    route();
  } catch (error) { showError(error, 'ورود ناموفق بود'); }
}

function showOtpVerifyStep(contact, result) {
  $('#otpRequestForm').hidden = true;
  $('#otpVerifyForm').hidden = false;
  $('#otpVerifyForm').elements.contact.value = contact;
  $('#otpMaskedContact').textContent = result.destination || contact;
  $('#otpDebugCode').hidden = !result.debug_code;
  $('#otpDebugCode').textContent = result.debug_code ? `کد حالت توسعه: ${result.debug_code}` : '';

  const deliveredToMailpit = result.delivery_provider === 'mailpit_api';
  const rawMailboxUrl = result.mailbox_url || appState.authCapabilities?.local_mailbox_url || '';
  const mailboxUrl = rawMailboxUrl ? safeMailboxUrl(rawMailboxUrl) : '';
  if (deliveredToMailpit && mailboxUrl) {
    $$('.mailpit-inbox-link').forEach(link => { link.href = mailboxUrl; });
  }
  const mailboxButton = $('#otpMailboxButton');
  if (mailboxButton) {
    mailboxButton.hidden = !(deliveredToMailpit && mailboxUrl);
    if (deliveredToMailpit && mailboxUrl) mailboxButton.href = mailpitMessageUrl(mailboxUrl, result.delivery_message_id);
    mailboxButton.textContent = result.delivery_message_id ? 'باز کردن همین ایمیل کد ورود' : 'باز کردن صندوق ایمیل';
  }

  const resend = $('#otpResendButton');
  resend.disabled = true;
  const cooldown = Math.max(1, Number(result.resend_after || 45));
  const expires = Math.max(cooldown, Number(result.expires_in || 300));
  startAuthCountdown('otp', expires, $('#otpCountdown'), () => { resend.disabled = false; });
  appState.authTimeouts.otp = setTimeout(() => { if (resend.isConnected) resend.disabled = false; }, cooldown * 1000);
  requestAnimationFrame(() => $('#otpVerifyForm').elements.code.focus());
}

async function requestLoginOtp(contact, { resend = false } = {}) {
  const result = await api.post('/auth/otp/request', { contact }, { auth: false, loader: true, loaderText: resend ? 'در حال ارسال مجدد کد...' : 'در حال ارسال کد...' });
  showOtpVerifyStep(contact, result);
  toast('کد ارسال شد', 'کد شش‌رقمی را از ایمیل یا پیامک وارد کن.');
}

async function handleOtpRequest(form) {
  if (appState.authBusy || !requireValidForm(form)) return;
  const contact = form.elements.contact.value.trim().toLowerCase();
  setAuthMessage('otp');
  appState.authBusy = true;
  const submit = form.querySelector('button[type="submit"]');
  if (submit) submit.disabled = true;
  try { await requestLoginOtp(contact); setAuthMessage('otp', 'کد ورود ارسال شد. صندوق ورودی یا پوشه Spam ایمیل را بررسی کن.', 'success'); }
  catch (error) { setAuthMessage('otp', authErrorMessage(error, 'ارسال کد ناموفق بود.'), 'error'); showError(error, 'ارسال کد ناموفق بود'); }
  finally { appState.authBusy = false; if (submit) submit.disabled = false; }
}

async function resendLoginOtp() {
  const contact = $('#otpVerifyForm').elements.contact.value.trim();
  if (!contact) { resetOtpForm(); return; }
  try { await requestLoginOtp(contact, { resend: true }); }
  catch (error) { showError(error, 'ارسال مجدد کد ناموفق بود'); }
}

async function handleOtpVerify(form) {
  if (!requireValidForm(form)) return;
  const data = formToObject(form);
  const remember = Boolean(data.remember); delete data.remember;
  data.code = asciiDigits(data.code).replace(/\D/g, '').slice(0, 6);
  form.elements.code.value = data.code;
  if (data.code.length !== 6) { form.elements.code.setCustomValidity('کد باید دقیقاً شش رقم باشد.'); form.reportValidity(); form.elements.code.setCustomValidity(''); return; }
  try {
    const result = await api.post('/auth/otp/verify', data, { auth: false, loader: true, loaderText: 'در حال بررسی کد...' });
    saveAuth(result.user, result.tokens, remember);
    closeDialog($('#authDialog'));
    resetOtpForm();
    toast('ورود موفق', 'حساب کاربری آماده است.');
    route();
  } catch (error) { setAuthMessage('otp', authErrorMessage(error, 'کد تأیید معتبر نیست.'), 'error'); showError(error, 'کد تأیید معتبر نیست'); }
}

function resetOtpForm() {
  clearAuthTimer('otp');
  $('#otpRequestForm').hidden = false;
  $('#otpVerifyForm').hidden = true;
  $('#otpRequestForm').reset();
  $('#otpVerifyForm').reset();
  $('#otpDebugCode').hidden = true;
  $('#otpDebugCode').textContent = '';
  $('#otpCountdown').textContent = '';
  $('#otpResendButton').disabled = true;
  const mailboxButton = $('#otpMailboxButton');
  if (mailboxButton) { mailboxButton.hidden = true; mailboxButton.href = '/mailpit/'; }
  setAuthMessage('otp');
}

function setSignupProgress(step) {
  const order = ['details', 'verify', 'done'];
  const current = order.indexOf(step);
  $$('[data-signup-progress]').forEach((el, index) => {
    el.classList.toggle('active', index === current);
    el.classList.toggle('done', index < current);
  });
}

function showSignupVerifyStep(result) {
  const registrationId = String(result?.registration_id || '').trim();
  if (!/^[a-f0-9]{32}$/i.test(registrationId)) {
    throw new Error('پاسخ ثبت‌نام ناقص است و شناسه تأیید دریافت نشد.');
  }

  // Rendering the verification step must never depend on browser storage.
  activateAuthTab('signup');
  const entry = $('#signupEntryStep');
  const verify = $('#signupVerifyForm');
  entry.hidden = true;
  verify.hidden = false;
  setSignupProgress('verify');
  verify.elements.registration_id.value = registrationId;
  verify.elements.code.value = '';
  $('#signupMaskedContact').textContent = result.destination || '';

  const deliveredToMailpit = result.delivery_provider === 'mailpit_api' || Boolean(result.delivery_message_id);
  const rawMailboxUrl = result.mailbox_url || appState.authCapabilities?.local_mailbox_url || '';
  const mailboxUrl = rawMailboxUrl ? safeMailboxUrl(rawMailboxUrl) : '';
  if (deliveredToMailpit && mailboxUrl) {
    $$('.mailpit-inbox-link').forEach(link => { link.href = mailboxUrl; });
  }
  const mailboxButton = $('#signupMailboxButton');
  mailboxButton.hidden = !(deliveredToMailpit && mailboxUrl);
  if (deliveredToMailpit && mailboxUrl) mailboxButton.href = mailpitMessageUrl(mailboxUrl, result.delivery_message_id);
  mailboxButton.textContent = result.delivery_message_id ? 'باز کردن همین ایمیل تأیید' : 'باز کردن صندوق ایمیل';
  $('#signupDebugCode').hidden = !result.debug_code;
  $('#signupDebugCode').textContent = result.debug_code ? `کد حالت توسعه: ${result.debug_code}` : '';

  appState.pendingSignup = {
    registration_id: registrationId,
    destination: result.destination || '',
    mailbox_url: mailboxUrl || '',
    delivery_message_id: result.delivery_message_id || '',
    delivery_provider: result.delivery_provider || '',
    expires_at: Date.now() + (Number(result.expires_in || 600) * 1000),
  };
  safeSessionSet('arenapass_pending_signup', JSON.stringify(appState.pendingSignup));

  verify.classList.remove('auth-step-enter');
  void verify.offsetWidth;
  verify.classList.add('auth-step-enter');
  setAuthMessage(
    'signup',
    deliveredToMailpit
      ? 'ایمیل تأیید با موفقیت در Mailpit ذخیره شد. روی «باز کردن همین ایمیل تأیید» بزن و کد شش‌رقمی را وارد کن.'
      : 'کد ثبت‌نام به ایمیل واقعی ارسال شد. صندوق ورودی یا پوشه Spam را بررسی کن و کد شش‌رقمی را وارد کن.',
    'success',
  );

  const resend = $('#signupResendButton');
  resend.disabled = true;
  const cooldown = Math.max(1, Number(result.resend_after || 45));
  startAuthCountdown('signup', result.expires_in || 300, $('#signupCountdown'));
  appState.authTimeouts.signup = setTimeout(() => { if (resend.isConnected) resend.disabled = false; }, cooldown * 1000);
  requestAnimationFrame(() => {
    try { verify.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch { /* old browser */ }
    verify.elements.code.focus();
  });
}

function restorePendingSignup() {
  const raw = safeSessionGet('arenapass_pending_signup');
  if (!raw) return;
  try {
    const pending = JSON.parse(raw);
    if (!pending?.registration_id || !/^[a-f0-9]{32}$/i.test(String(pending.registration_id))) throw new Error('invalid pending signup');
    if (pending.expires_at && Number(pending.expires_at) <= Date.now()) throw new Error('expired pending signup');
    showSignupVerifyStep({
      registration_id: pending.registration_id,
      destination: pending.destination || '',
      mailbox_url: pending.mailbox_url || '',
      delivery_message_id: pending.delivery_message_id || '',
      delivery_provider: pending.delivery_provider || '',
      expires_in: pending.expires_at ? Math.max(1, Math.ceil((Number(pending.expires_at) - Date.now()) / 1000)) : 600,
      resend_after: 1,
    });
  } catch {
    safeSessionRemove('arenapass_pending_signup');
  }
}

async function handleSignup(form) {
  if (appState.authBusy || !requireValidForm(form)) return;
  const data = formToObject(form);
  setAuthMessage('signup');
  // Do not block signup using a possibly stale readiness snapshot. The backend
  // performs the authoritative provider send for this request.
  if (!data.accept_terms) { setAuthMessage('signup', 'برای ادامه باید قوانین استفاده را بپذیری.', 'warning'); return; }
  if (data.password !== data.confirm_password) {
    form.elements.confirm_password.setCustomValidity('تکرار رمز عبور با رمز اصلی یکسان نیست.');
    form.reportValidity(); form.elements.confirm_password.setCustomValidity(''); return;
  }
  delete data.accept_terms; delete data.confirm_password;
  data.email = String(data.email || '').trim().toLowerCase();
  data.phone = asciiDigits(String(data.phone || '')).replace(/[\s()-]/g, '');
  if (!data.email && !data.phone) { setAuthMessage('signup', 'حداقل ایمیل یا شماره تلفن را وارد کن.', 'warning'); return; }
  const phoneReady = Boolean(appState.authCapabilities?.otp?.phone);
  if (data.preferred_login === 'phone' && !phoneReady) {
    if (data.email) data.preferred_login = 'email';
    else { setAuthMessage('signup', 'ارسال پیامک در این محیط تنظیم نشده است؛ یک ایمیل معتبر وارد کن.', 'warning'); return; }
  }
  if (data.preferred_login === 'email' && !data.email) {
    setAuthMessage('signup', 'برای تأیید ایمیلی، واردکردن ایمیل الزامی است.', 'warning'); return;
  }
  if (!data.email) delete data.email;
  if (!data.phone) delete data.phone;
  if (data.city_id) data.city_id = Number(data.city_id); else delete data.city_id;
  if (!data.date_of_birth) delete data.date_of_birth;
  appState.authBusy = true;
  const submit = form.querySelector('button[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    const result = await api.post('/auth/signup', data, { auth: false, loader: true, loaderText: 'در حال ارسال ایمیل کد تأیید...' });
    showSignupVerifyStep(result);
    toast('کد ثبت‌نام ارسال شد', 'مرحله تأیید باز شد؛ ایمیل واقعی یا پوشه Spam را بررسی کن.');
  } catch (error) {
    const message = authErrorMessage(error, 'شروع ثبت‌نام انجام نشد.');
    setAuthMessage('signup', message, 'error');
    showError(error, 'شروع ثبت‌نام انجام نشد');
  } finally {
    appState.authBusy = false;
    if (submit) submit.disabled = false;
  }
}

async function resendSignupOtp() {
  const registrationId = $('#signupVerifyForm').elements.registration_id.value.trim();
  if (!registrationId) { resetSignupFlow(false); return; }
  try {
    const result = await api.post('/auth/signup/resend', { registration_id: registrationId }, { auth: false, loader: true, loaderText: 'در حال ارسال مجدد کد ثبت‌نام...' });
    showSignupVerifyStep(result);
    toast('کد جدید ارسال شد', 'کد قبلی دیگر معتبر نیست.');
  } catch (error) { setAuthMessage('signup', authErrorMessage(error, 'ارسال مجدد کد ثبت‌نام انجام نشد.'), 'error'); showError(error, 'ارسال مجدد کد ثبت‌نام انجام نشد'); }
}

async function handleSignupVerify(form) {
  if (appState.authBusy || !requireValidForm(form)) return;
  const data = formToObject(form);
  data.code = asciiDigits(data.code).replace(/\D/g, '').slice(0, 6);
  form.elements.code.value = data.code;
  if (data.code.length !== 6) { form.elements.code.setCustomValidity('کد باید دقیقاً شش رقم باشد.'); form.reportValidity(); form.elements.code.setCustomValidity(''); return; }
  appState.authBusy = true;
  const submit = form.querySelector('button[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    const result = await api.post('/auth/signup/verify', data, { auth: false, loader: true, loaderText: 'در حال تأیید و ساخت حساب...' });
    saveAuth(result.user, result.tokens, false);
    setSignupProgress('done');
    resetSignupFlow(true);
    closeDialog($('#authDialog'));
    toast('حساب با موفقیت ساخته شد', 'ایمیل تأیید شد و اکنون وارد حساب شده‌ای.');
    location.hash = '#/my';
  } catch (error) {
    setAuthMessage('signup', authErrorMessage(error, 'تأیید ثبت‌نام انجام نشد.'), 'error');
    showError(error, 'تأیید ثبت‌نام انجام نشد');
  } finally {
    appState.authBusy = false;
    if (submit) submit.disabled = false;
  }
}

function resetSignupFlow(clearEntry = false) {
  clearAuthTimer('signup');
  appState.pendingSignup = null;
  safeSessionRemove('arenapass_pending_signup');
  $('#signupEntryStep').hidden = false;
  $('#signupVerifyForm').hidden = true;
  $('#signupVerifyForm').reset();
  $('#signupDebugCode').hidden = true;
  $('#signupDebugCode').textContent = '';
  $('#signupCountdown').textContent = '';
  $('#signupResendButton').disabled = true;
  const mailboxButton = $('#signupMailboxButton');
  if (mailboxButton) { mailboxButton.href = '/mailpit/'; mailboxButton.textContent = 'باز کردن صندوق ایمیل'; }
  setSignupProgress('details');
  setAuthMessage('signup');
  if (clearEntry) $('#signupForm').reset();
}

function activateAccountTab(tab) {
  if (!ensureAuth()) return;
  appState.accountTab = ['overview', 'reservations', 'bookings', 'payments', 'wallet', 'reports', 'profile'].includes(tab) ? tab : 'overview';
  $$('[data-account-tab]').forEach(b => b.classList.toggle('active', b.dataset.accountTab === appState.accountTab));
  history.replaceState(null, '', `#/my/${appState.accountTab}`); loadAccountTab(appState.accountTab);
}
async function loadAccountTab(tab) {
  clearTimers(); const root = $('#accountContent'); root.innerHTML = '<div class="dashboard-loading"><span class="spinner"></span> در حال دریافت اطلاعات...</div>';
  try {
    if (tab === 'overview') await renderAccountOverview(root);
    else if (tab === 'reservations') await renderReservations(root);
    else if (tab === 'bookings') await renderBookings(root);
    else if (tab === 'payments') await renderPayments(root);
    else if (tab === 'wallet') await renderWallet(root);
    else if (tab === 'reports') await renderReports(root);
    else if (tab === 'profile') await renderProfile(root);
  } catch (error) { root.innerHTML = errorState(error); showError(error, 'دریافت اطلاعات حساب ناموفق بود'); }
}
function errorState(error) { return `<div class="empty-state"><div class="empty-icon">!</div><h3>اطلاعات قابل دریافت نیست</h3><p>${esc(error.message || 'خطای ناشناخته')}</p><button class="button button-soft" data-action="retry-account">تلاش مجدد</button></div>`; }
async function renderAccountOverview(root) {
  const [profile, wallet, reservations, bookings] = await Promise.all([api.get('/profile'), appState.user.role === 'spectator' ? api.get('/wallet') : Promise.resolve(null), appState.user.role === 'spectator' ? rawGet('/reservations?page=1&page_size=4') : Promise.resolve({ data: [], meta: {} }), appState.user.role === 'spectator' ? rawGet('/bookings?scope=upcoming&page=1&page_size=3') : Promise.resolve({ data: [], meta: {} })]);
  appState.profile = profile; appState.user = { ...appState.user, ...profile }; TokenStore.set('user', JSON.stringify(appState.user), TokenStore.persistent()); updateAuthUI();
  if (appState.user.role === 'support') { root.innerHTML = `<div class="dashboard-header"><div><h1>سلام ${esc(profile.first_name || '')}</h1><p>حساب شما نقش پشتیبان دارد؛ برای عملیات سامانه به پنل پشتیبانی برو.</p></div><a href="#/support" class="button button-primary">ورود به پنل پشتیبانی</a></div>`; return; }
  const resItems = normalizeList(reservations.data); const bookingItems = normalizeList(bookings.data); const held = resItems.filter(r => r.status === 'held').length;
  root.innerHTML = `<div class="dashboard-header"><div><h1>سلام ${esc(profile.first_name || '')} 👋</h1><p>خلاصه حساب و فعالیت‌های اخیرت را اینجا می‌بینی.</p></div><a href="#/tickets" class="button button-primary">پیدا کردن مسابقه</a></div>
    <div class="stat-grid"><div class="stat-card"><div class="stat-top"><small>موجودی کیف پول</small><span class="stat-icon">◫</span></div><b>${money(wallet?.balance)}</b></div><div class="stat-card"><div class="stat-top"><small>رزروهای موقت</small><span class="stat-icon">◷</span></div><b>${numberFa(held)}</b></div><div class="stat-card"><div class="stat-top"><small>بلیط‌های آینده</small><span class="stat-icon">▣</span></div><b>${numberFa(bookings.meta?.total || bookingItems.length)}</b></div><div class="stat-card"><div class="stat-top"><small>وضعیت حساب</small><span class="stat-icon">✓</span></div><b>${profile.is_active === false ? 'غیرفعال' : 'فعال'}</b></div></div>
    <div class="overview-grid"><div class="content-card"><div class="content-card-header"><h2>رزروهای اخیر</h2><button class="link-button" data-account-tab="reservations">مشاهده همه</button></div><div class="content-card-body list-stack">${resItems.length ? resItems.map(reservationItem).join('') : emptyInline('هنوز رزروی ثبت نکرده‌ای.')}</div></div>
    <div class="content-card"><div class="content-card-header"><h2>دسترسی سریع</h2></div><div class="content-card-body quick-actions"><button class="quick-action" data-account-tab="wallet"><b>افزایش موجودی</b><small>شارژ کیف پول محلی</small></button><button class="quick-action" data-action="new-report"><b>ثبت گزارش</b><small>پیگیری مشکل بلیط</small></button><button class="quick-action" data-account-tab="bookings"><b>بلیط‌های من</b><small>کد و مشخصات ورود</small></button><button class="quick-action" data-account-tab="profile"><b>ویرایش پروفایل</b><small>اطلاعات و امنیت حساب</small></button></div></div></div>`;
  startCountdowns(root);
}
function emptyInline(text) { return `<div class="table-empty"><span>—</span><b>${esc(text)}</b></div>`; }
function reservationItem(r) {
  const canPay = r.status === 'held'; const canCancel = r.status === 'paid' && !r.has_pending_cancellation; const canSeat = ['held', 'paid'].includes(r.status) && !r.has_pending_seat_change;
  return `<article class="reservation-item"><div class="item-main"><div>${statusBadge(r.status)} ${r.support_review_status ? statusBadge(r.support_review_status) : ''}</div><h3>${esc(r.home_team)} - ${esc(r.away_team)}</h3><p>${esc(r.venue_name)} · ${esc(dateFa(r.starts_at))}</p><div class="item-meta"><span>${numberFa(r.quantity)} بلیط</span><span>${money(r.total_amount)}</span>${r.status === 'held' && r.expires_at ? `<span class="countdown" data-expires="${attr(r.expires_at)}">--:--</span>` : ''}</div></div><div class="item-actions"><button class="button button-soft button-xs" data-action="reservation-detail" data-id="${attr(r.id)}">جزئیات</button>${canPay ? `<button class="button button-success button-xs" data-action="pay-reservation" data-id="${attr(r.id)}" data-amount="${attr(r.total_amount)}">پرداخت</button>` : ''}${canCancel ? `<button class="button button-danger button-xs" data-action="cancel-reservation" data-id="${attr(r.id)}">کنسلی</button>` : ''}${canSeat ? `<button class="button button-soft button-xs" data-action="seat-change" data-id="${attr(r.id)}">تغییر جایگاه</button>` : ''}</div></article>`;
}
async function renderReservations(root) {
  const raw = await rawGet('/reservations?page=1&page_size=100'); const items = normalizeList(raw.data);
  root.innerHTML = `<div class="dashboard-header"><div><h1>رزروهای من</h1><p>رزروهای موقت، پرداخت‌شده، لغوشده و منقضی را مدیریت کن.</p></div><select id="reservationStatusFilter" class="input-like" style="width:170px"><option value="">همه وضعیت‌ها</option><option value="held">رزرو موقت</option><option value="paid">پرداخت‌شده</option><option value="canceled">لغوشده</option><option value="expired">منقضی</option><option value="refunded">مستردشده</option></select></div><div class="content-card"><div class="content-card-body list-stack" id="reservationList">${items.length ? items.map(reservationItem).join('') : emptyInline('رزروی وجود ندارد.')}</div></div>`;
  $('#reservationStatusFilter').addEventListener('change', e => { const filtered = e.target.value ? items.filter(x => x.status === e.target.value) : items; $('#reservationList').innerHTML = filtered.length ? filtered.map(reservationItem).join('') : emptyInline('رزروی با این وضعیت وجود ندارد.'); startCountdowns($('#reservationList')); }); startCountdowns(root);
}
function startCountdowns(root = document) {
  $$('[data-expires]', root).forEach(el => { const update = () => { const ms = new Date(el.dataset.expires).getTime() - Date.now(); if (ms <= 0) { el.textContent = 'منقضی شده'; return; } const min = Math.floor(ms / 60000), sec = Math.floor((ms % 60000) / 1000); el.textContent = `${digitsFa(String(min).padStart(2, '0'))}:${digitsFa(String(sec).padStart(2, '0'))}`; }; update(); const timer = setInterval(update, 1000); appState.timers.add(timer); });
}
function clearTimers() { appState.timers.forEach(clearInterval); appState.timers.clear(); }
async function showReservationDetail(id) {
  try { const r = await api.get(`/reservations/${id}`, { loader: true }); const payments = normalizeList(safeJson(r.payments)); const issued = normalizeList(safeJson(r.issued_tickets)); showFormDialog({ title: `جزئیات رزرو #${numberFa(r.id)}`, description: `${r.home_team || ''} - ${r.away_team || ''}`, body: `<div class="confirm-summary"><div><span>وضعیت</span><b>${I18N.statuses[r.status] || r.status}</b></div><div><span>تعداد</span><b>${numberFa(r.quantity)}</b></div><div><span>مبلغ</span><b>${money(r.total_amount)}</b></div><div><span>زمان رزرو</span><b>${dateFa(r.reserved_at)}</b></div><div><span>مهلت پرداخت</span><b>${dateFa(r.expires_at)}</b></div></div><h3>پرداخت‌ها</h3>${payments.length ? payments.map(p => `<p class="inline-message">#${numberFa(p.id)} · ${money(p.amount)} · ${esc(I18N.statuses[p.status] || p.status)}</p>`).join('') : '<p class="muted">پرداختی ثبت نشده است.</p>'}<h3>بلیط‌های صادرشده</h3>${issued.length ? issued.map(t => `<p class="inline-message">${esc(t.ticket_number)} · ${esc(I18N.statuses[t.status] || t.status)}</p>`).join('') : '<p class="muted">بلیطی صادر نشده است.</p>'}`, hideConfirm: true }); }
  catch (error) { showError(error, 'دریافت جزئیات رزرو ناموفق بود'); }
}
async function openPayment(id, amount) {
  let methods = appState.lookups.paymentMethods; if (!methods.length) methods = normalizeList(await api.get('/payment-methods', { auth: false }));
  showFormDialog({ title: 'پرداخت رزرو', description: `مبلغ قابل پرداخت: ${money(amount)}`, body: `<form id="paymentForm" class="stack-form"><label class="field"><span>روش پرداخت</span><select name="payment_method" required>${methods.map(m => `<option value="${attr(m.code)}">${esc(m.name)}</option>`).join('')}</select></label><div class="inline-message">پرداخت این پروژه به‌صورت محلی شبیه‌سازی می‌شود و به درگاه بانکی واقعی متصل نیست.</div></form>`, confirmText: 'پرداخت و صدور بلیط', onConfirm: async () => { const method = $('#paymentForm').elements.payment_method.value; const result = await api.post(`/reservations/${id}/pay`, { payment_method: method }, { loader: true, loaderText: 'در حال پردازش پرداخت...' }); closeDialog($('#formDialog')); toast('پرداخت موفق', result.transaction_ref ? `کد تراکنش: ${result.transaction_ref}` : 'بلیط صادر شد.'); loadAccountTab('reservations'); } });
}
async function openCancellation(id) {
  try { const quote = await api.get(`/reservations/${id}/cancellation-quote`, { loader: true }); showFormDialog({ title: 'درخواست کنسلی', description: 'پیش‌نمایش جریمه و مبلغ استرداد بر اساس قوانین برگزارکننده', body: `<div class="confirm-summary"><div><span>مبلغ پرداختی</span><b>${money(quote.total_amount)}</b></div><div><span>درصد جریمه</span><b>${numberFa(quote.penalty_percentage)}٪</b></div><div><span>استرداد تقریبی</span><b>${money(quote.estimated_refund)}</b></div></div><form id="cancelForm" class="stack-form"><label class="field"><span>دلیل کنسلی</span><textarea name="reason" minlength="3" maxlength="2000" required placeholder="دلیل درخواست را توضیح بده..."></textarea></label></form>`, confirmText: 'ثبت درخواست کنسلی', danger: true, onConfirm: async () => { const reason = $('#cancelForm').elements.reason.value.trim(); if (reason.length < 3) throw new Error('دلیل کنسلی را وارد کن.'); await api.post(`/reservations/${id}/cancellation-requests`, { reason }, { loader: true }); closeDialog($('#formDialog')); toast('درخواست ثبت شد', 'پشتیبان نتیجه بررسی را در حساب تو ثبت می‌کند.'); loadAccountTab('reservations'); } }); }
  catch (error) { showError(error, 'محاسبه کنسلی ناموفق بود'); }
}
async function openSeatChange(id) {
  try { const options = normalizeList(await api.get(`/seat-change-options?reservation_id=${id}`, { loader: true })); if (!options.length) { toast('گزینه‌ای موجود نیست', 'جایگاه هم‌قیمت و دارای ظرفیت پیدا نشد.', 'warning'); return; } showFormDialog({ title: 'درخواست تغییر جایگاه', description: 'فقط جایگاه‌های هم‌قیمت و مجاز نمایش داده شده‌اند.', body: `<form id="seatChangeForm" class="stack-form"><label class="field"><span>جایگاه جدید</span><select name="new_ticket_id" required>${options.map(o => `<option value="${attr(o.ticket_id)}">${esc(o.category_name)} · بخش ${esc(o.section_code)}${o.row_code ? ` · ردیف ${esc(o.row_code)}` : ''}${o.seat_code ? ` · صندلی ${esc(o.seat_code)}` : ''} · ${numberFa(o.available_quantity)} موجود</option>`).join('')}</select></label></form>`, confirmText: 'ثبت درخواست تغییر', onConfirm: async () => { const new_ticket_id = Number($('#seatChangeForm').elements.new_ticket_id.value); await api.post(`/reservations/${id}/seat-change-requests`, { new_ticket_id }, { loader: true }); closeDialog($('#formDialog')); toast('درخواست تغییر جایگاه ثبت شد'); loadAccountTab('reservations'); } }); }
  catch (error) { showError(error, 'دریافت جایگاه‌های جایگزین ناموفق بود'); }
}
async function renderBookings(root) {
  const raw = await rawGet('/bookings?scope=all&page=1&page_size=100'); const items = normalizeList(raw.data);
  root.innerHTML = `<div class="dashboard-header"><div><h1>بلیط‌های من</h1><p>بلیط‌های صادرشده، آینده، استفاده‌شده و مستردشده.</p></div><select id="bookingScope" class="input-like" style="width:180px"><option value="all">همه بلیط‌ها</option><option value="upcoming">مسابقات آینده</option><option value="used">استفاده‌شده</option><option value="canceled">کنسل‌شده</option></select></div><div class="content-card"><div class="content-card-body list-stack" id="bookingList">${items.length ? items.map(bookingItem).join('') : emptyInline('هنوز بلیط خریداری‌شده‌ای نداری.')}</div></div>`;
  $('#bookingScope').addEventListener('change', async e => { const response = await rawGet(`/bookings?scope=${encodeURIComponent(e.target.value)}&page=1&page_size=100`); const list = normalizeList(response.data); $('#bookingList').innerHTML = list.length ? list.map(bookingItem).join('') : emptyInline('بلیطی در این دسته وجود ندارد.'); });
}
function bookingItem(b) {
  const tickets = normalizeList(safeJson(b.tickets));
  return `<article class="booking-item"><div class="item-main"><div>${statusBadge(b.reservation_status)}</div><h3>${esc(b.home_team)} - ${esc(b.away_team)}</h3><p>${esc(b.venue_name)} · ${esc(dateFa(b.starts_at))}</p><div class="item-meta"><span>${esc(b.category_name)} / ${esc(b.section_code)}</span><span>${money(b.total_amount)}</span>${tickets.length ? `<span>شماره: ${esc(tickets[0].ticket_number)}</span>` : ''}</div></div><div class="item-actions">${tickets.length ? `<button class="button button-primary button-xs" data-action="show-issued-ticket" data-payload="${attr(encodeURIComponent(JSON.stringify({ ...b, ticket: tickets[0] })))}">نمایش بلیط</button>` : ''}<button class="button button-soft button-xs" data-action="new-report" data-reservation="${attr(b.reservation_id)}" data-ticket="${attr(b.ticket_id)}">گزارش مشکل</button></div></article>`;
}
function showIssuedTicket(payload) {
  const b = JSON.parse(decodeURIComponent(payload)); const t = b.ticket;
  showFormDialog({ title: 'بلیط ورود به مسابقه', description: `${b.home_team} - ${b.away_team}`, body: `<div class="ticket-detail-hero"><div class="ticket-sport"><span>${esc(b.sport_name)}</span><span>${esc(I18N.statuses[t.status] || t.status)}</span></div><h2>${esc(t.ticket_number)}</h2><p>${esc(b.venue_name)} · ${esc(dateFa(b.starts_at))}</p></div><div class="confirm-summary" style="margin-top:15px"><div><span>رده / بخش</span><b>${esc(b.category_name)} / ${esc(b.section_code)}</b></div><div><span>ردیف / صندلی</span><b>${esc(b.row_code || '—')} / ${esc(b.seat_code || '—')}</b></div><div><span>کد QR</span><b dir="ltr" style="font-size:9px;word-break:break-all">${esc(t.qr_token)}</b></div></div><button class="button button-soft button-block" data-copy="${attr(t.qr_token)}">کپی کد ورود</button>`, hideConfirm: true });
}
async function renderPayments(root) {
  const raw = await rawGet('/payments?page=1&page_size=100'); const items = normalizeList(raw.data);
  root.innerHTML = `<div class="dashboard-header"><div><h1>تاریخچه پرداخت‌ها</h1><p>وضعیت، روش و شماره پیگیری تراکنش‌های حساب.</p></div></div><div class="content-card"><div class="data-table-wrap"><table class="data-table"><thead><tr><th>شناسه</th><th>رزرو</th><th>مبلغ</th><th>روش</th><th>وضعیت</th><th>شماره پیگیری</th><th>زمان</th></tr></thead><tbody>${items.map(p => `<tr><td>#${numberFa(p.id)}</td><td>#${numberFa(p.reservation_id)}</td><td>${money(p.amount)}</td><td>${esc(p.method_name || p.method_code)}</td><td>${statusBadge(p.status)}</td><td dir="ltr">${esc(p.transaction_ref || '—')}</td><td>${esc(dateFa(p.paid_at || p.created_at))}</td></tr>`).join('') || `<tr><td colspan="7">${emptyInline('پرداختی ثبت نشده است.')}</td></tr>`}</tbody></table></div></div>`;
}
async function renderWallet(root) {
  const wallet = await api.get('/wallet'); const tx = normalizeList(safeJson(wallet.recent_transactions));
  root.innerHTML = `<div class="dashboard-header"><div><h1>کیف پول</h1><p>موجودی و تراکنش‌های کیف پول داخلی MahTicket.</p></div><button class="button button-primary" data-action="wallet-topup">افزایش موجودی</button></div><div class="wallet-card"><small>موجودی قابل استفاده</small><h2>${money(wallet.balance)}</h2><div class="wallet-card-footer"><span>ارز: ${esc(wallet.currency || 'IRR')}</span><span>آخرین بروزرسانی: ${esc(dateFa(wallet.updated_at))}</span></div></div><div class="content-card" style="margin-top:16px"><div class="content-card-header"><h2>تراکنش‌های اخیر</h2></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>نوع</th><th>مبلغ</th><th>موجودی پس از تراکنش</th><th>توضیح</th><th>زمان</th></tr></thead><tbody>${tx.map(t => `<tr><td>${esc(t.transaction_type || t.type)}</td><td>${money(t.amount)}</td><td>${money(t.balance_after)}</td><td>${esc(t.description || '—')}</td><td>${esc(dateFa(t.created_at))}</td></tr>`).join('') || `<tr><td colspan="5">${emptyInline('تراکنشی ثبت نشده است.')}</td></tr>`}</tbody></table></div></div>`;
}
function parseWalletTopupAmount(value) {
  const normalized = asciiDigits(value)
    .replace(/[\s,_،٬]/g, '')
    .trim();
  if (!/^\d+$/.test(normalized)) return null;
  const amount = Number(normalized);
  if (!Number.isSafeInteger(amount) || amount < 1 || amount > 100000000000) return null;
  return String(amount);
}
function openWalletTopup() {
  showFormDialog({
    title: 'افزایش موجودی کیف پول',
    description: 'این قابلیت فقط برای محیط نمایشی پروژه فعال است.',
    body: `<form id="walletTopupForm" class="stack-form"><label class="field"><span>مبلغ (تومان)</span><input name="amount" type="text" inputmode="numeric" autocomplete="off" maxlength="15" required placeholder="۵۰۰٬۰۰۰" aria-describedby="walletAmountHelp"><small id="walletAmountHelp">مبلغ را با ارقام فارسی یا انگلیسی، با یا بدون جداکننده وارد کن.</small></label><label class="field"><span>توضیح</span><input name="description" maxlength="500" value="افزایش موجودی کیف پول"></label></form>`,
    confirmText: 'افزایش موجودی',
    onConfirm: async () => {
      const f = $('#walletTopupForm');
      const amountInput = f.elements.amount;
      const amount = parseWalletTopupAmount(amountInput.value);
      if (!amount) {
        amountInput.setCustomValidity('یک مبلغ صحیح بین ۱ تا ۱۰۰٬۰۰۰٬۰۰۰٬۰۰۰ تومان وارد کن.');
        amountInput.reportValidity();
        amountInput.addEventListener('input', () => amountInput.setCustomValidity(''), { once: true });
        return false;
      }
      const description = f.elements.description.value.trim() || 'Wallet top-up';
      await api.post('/wallet/top-up', { amount, description }, { loader: true });
      closeDialog($('#formDialog'));
      toast('کیف پول شارژ شد');
      loadAccountTab('wallet');
    },
  });
}
async function renderReports(root) {
  const raw = await rawGet('/reports?page=1&page_size=100'); const items = normalizeList(raw.data);
  root.innerHTML = `<div class="dashboard-header"><div><h1>گزارش‌ها و پشتیبانی</h1><p>مشکلات ثبت‌شده و پاسخ تیم پشتیبانی.</p></div><button class="button button-primary" data-action="new-report">+ ثبت گزارش جدید</button></div><div class="content-card"><div class="content-card-body list-stack">${items.length ? items.map(r => `<article class="report-item"><div class="item-main"><div>${statusBadge(r.status)} <span class="tag">${esc(r.category_name)}</span></div><h3>${esc(r.subject)}</h3><p>${esc(r.description)}</p><div class="item-meta"><span>${esc(dateFa(r.created_at))}</span>${r.support_first_name ? `<span>پشتیبان: ${esc(r.support_first_name)} ${esc(r.support_last_name)}</span>` : ''}</div>${r.support_response ? `<div class="inline-message" style="margin-top:9px"><b>پاسخ پشتیبان:</b> ${esc(r.support_response)}</div>` : ''}</div><div class="item-actions"><span>#${numberFa(r.id)}</span></div></article>`).join('') : emptyInline('گزارشی ثبت نشده است.')}</div></div>`;
}
function openNewReport(preset = {}) {
  const cats = appState.lookups.reportCategories;
  showFormDialog({ title: 'ثبت گزارش مشکل', description: 'گزارش با جزئیات کافی باعث رسیدگی سریع‌تر می‌شود.', body: `<form id="reportForm" class="stack-form"><label class="field"><span>نوع مرجع</span><select name="target_type"><option value="ticket" ${preset.ticket ? 'selected' : ''}>بلیط</option><option value="reservation" ${preset.reservation ? 'selected' : ''}>رزرو</option><option value="payment">پرداخت</option></select></label><label class="field"><span>شناسه مرجع</span><input name="target_id" type="number" min="1" required value="${attr(preset.reservation || preset.ticket || '')}"></label><label class="field"><span>دسته‌بندی</span><select name="category_id" required>${cats.map(c => `<option value="${attr(c.id)}">${esc(c.name)}</option>`).join('')}</select></label><label class="field"><span>موضوع</span><input name="subject" minlength="3" maxlength="200" required></label><label class="field"><span>شرح کامل</span><textarea name="description" minlength="5" maxlength="5000" required></textarea></label></form>`, confirmText: 'ارسال گزارش', onConfirm: async () => { const data = formToObject($('#reportForm')); const payload = { category_id: Number(data.category_id), subject: data.subject.trim(), description: data.description.trim() }; payload[`${data.target_type}_id`] = Number(data.target_id); await api.post('/reports', payload, { loader: true }); closeDialog($('#formDialog')); toast('گزارش ثبت شد', 'وضعیت رسیدگی در همین بخش قابل مشاهده است.'); if (appState.accountTab === 'reports') loadAccountTab('reports'); } });
}
async function renderProfile(root) {
  const p = await api.get('/profile'); appState.profile = p;
  root.innerHTML = `<div class="dashboard-header"><div><h1>پروفایل و امنیت</h1><p>اطلاعات شخصی و روش‌های ورود حساب را مدیریت کن.</p></div></div><div class="profile-grid"><form id="profileForm" class="form-card"><h2>اطلاعات شخصی</h2><div class="field-group"><label class="field"><span>نام</span><input name="first_name" required value="${attr(p.first_name)}"></label><label class="field"><span>نام خانوادگی</span><input name="last_name" required value="${attr(p.last_name)}"></label></div><label class="field"><span>شهرستان</span><select name="city_id">${cityOptionsHtml(appState.lookups.cities, 'بدون انتخاب', p.city_id)}</select></label><label class="field"><span>تاریخ تولد</span><input name="date_of_birth" type="date" value="${attr(p.date_of_birth || '')}"></label><label class="field"><span>آدرس عکس پروفایل</span><input name="profile_picture_url" type="url" dir="ltr" value="${attr(p.profile_picture_url || '')}" placeholder="https://..."></label><button class="button button-primary button-block" type="submit">ذخیره تغییرات</button></form>
    <div><form id="passwordChangeForm" class="form-card"><h2>تغییر رمز عبور</h2><div class="inline-message">ابتدا کد امنیتی را درخواست کن؛ در محیط توسعه ممکن است کد در پاسخ نمایش داده شود.</div><button type="button" class="button button-soft button-block" data-action="request-password-otp">دریافت کد امنیتی</button><p id="passwordOtpDebug" class="debug-code" hidden></p><label class="field"><span>رمز فعلی</span><input name="current_password" type="password" required></label><label class="field"><span>رمز جدید</span><input name="new_password" type="password" minlength="8" required></label><label class="field"><span>کد شش رقمی</span><input name="code" inputmode="numeric" maxlength="6" required></label><button class="button button-primary button-block" type="submit">تغییر رمز</button></form><button class="form-card" style="width:100%;margin-top:16px;text-align:right;cursor:pointer" data-action="change-contact"><h2>تغییر ایمیل یا شماره تلفن</h2><p class="muted">با احراز هویت OTP، راه ارتباطی و روش ورود ترجیحی را بروزرسانی کن.</p></button></div></div>`;
  enhanceCitySelect($('#profileForm select[name="city_id"]'));
  $('#profileForm').addEventListener('submit', updateProfile);
  $('#passwordChangeForm').addEventListener('submit', changePassword);
}
async function updateProfile(e) { e.preventDefault(); const data = formToObject(e.currentTarget); if (data.city_id) data.city_id = Number(data.city_id); else data.city_id = null; data.date_of_birth ||= null; data.profile_picture_url ||= null; try { const result = await api.patch('/profile', data, { loader: true }); appState.user = { ...appState.user, ...result }; TokenStore.set('user', JSON.stringify(appState.user), TokenStore.persistent()); updateAuthUI(); toast('پروفایل بروزرسانی شد'); } catch (error) { showError(error, 'ذخیره پروفایل ناموفق بود'); } }
async function requestPasswordOtp() { try { const result = await api.post('/profile/password/otp/request', {}, { loader: true }); const el = $('#passwordOtpDebug'); if (result.debug_code) { el.hidden = false; el.textContent = `کد حالت توسعه: ${result.debug_code}`; } toast('کد امنیتی ارسال شد', result.destination || 'راه ارتباطی ثبت‌شده را بررسی کن.'); } catch (error) { showError(error, 'ارسال کد امنیتی ناموفق بود'); } }
async function changePassword(e) { e.preventDefault(); const data = formToObject(e.currentTarget); try { const result = await api.post('/profile/password', data, { loader: true }); if (result.tokens) saveAuth(result.profile || appState.user, result.tokens, TokenStore.persistent()); e.currentTarget.reset(); toast('رمز عبور تغییر کرد'); } catch (error) { showError(error, 'تغییر رمز ناموفق بود'); } }
function openContactChange() { showFormDialog({ title: 'تغییر راه ارتباطی', description: 'ابتدا کد OTP برای ایمیل یا شماره جدید درخواست می‌شود.', body: `<form id="contactRequestForm" class="stack-form"><label class="field"><span>ایمیل یا شماره تلفن جدید</span><input name="contact" required></label><label class="field"><span>روش ورود ترجیحی</span><select name="preferred_login"><option value="email">ایمیل</option><option value="phone">شماره تلفن</option></select></label><label class="field" id="contactCodeField" hidden><span>کد تأیید</span><input name="code" inputmode="numeric" maxlength="6"></label><p id="contactDebug" class="debug-code" hidden></p></form>`, confirmText: 'ارسال کد', onConfirm: async button => { const form = $('#contactRequestForm'); const contact = form.elements.contact.value.trim(); if (!form.dataset.requested) { const result = await api.post('/profile/contact/request', { contact }, { loader: true }); form.dataset.requested = '1'; $('#contactCodeField').hidden = false; form.elements.code.required = true; button.textContent = 'تأیید تغییر'; if (result.debug_code) { $('#contactDebug').hidden = false; $('#contactDebug').textContent = `کد حالت توسعه: ${result.debug_code}`; } toast('کد ارسال شد'); return false; } const code = form.elements.code.value.trim(); const preferred_login = form.elements.preferred_login.value; const result = await api.post('/profile/contact/confirm', { contact, code, preferred_login }, { loader: true }); saveAuth(result.profile || appState.user, result.tokens, TokenStore.persistent()); closeDialog($('#formDialog')); toast('راه ارتباطی تغییر کرد'); loadAccountTab('profile'); } }); }

function showFormDialog({ title, description = '', body = '', confirmText = 'تأیید', cancelText = 'انصراف', onConfirm = null, hideConfirm = false, danger = false }) {
  const root = $('#formDialogContent'); root.innerHTML = `<span class="eyebrow dark">MahTicket</span><h2 class="modal-title">${esc(title)}</h2>${description ? `<p class="modal-description">${esc(description)}</p>` : ''}${body}<div class="dialog-actions"><button class="button button-soft" data-close-dialog>${esc(cancelText)}</button>${hideConfirm ? '' : `<button class="button ${danger ? 'button-danger' : 'button-primary'}" id="formDialogConfirm">${esc(confirmText)}</button>`}</div>`;
  openDialog($('#formDialog'));
  if (!hideConfirm && onConfirm) { $('#formDialogConfirm').addEventListener('click', async e => { const button = e.currentTarget; const form = $('#formDialogContent form'); if (form && !form.reportValidity()) return; button.disabled = true; try { const result = await onConfirm(button); if (result === false) button.disabled = false; } catch (error) { button.disabled = false; showError(error, 'عملیات انجام نشد'); } }); }
}

async function loadSupportDashboard() {
  const root = $('#supportMetrics'); const content = $('#supportContent'); content.innerHTML = '<div class="dashboard-loading"><span class="spinner"></span> در حال دریافت اطلاعات...</div>';
  try { const data = await api.get('/support/dashboard'); const metrics = [ ['کاربران فعال', data.active_spectators], ['گفتگوی خوانده‌نشده', data.unread_chats, true], ['گفتگوی باز', data.open_chats], ['ردیف بلیط فعال', data.active_ticket_rows], ['رزرو موقت', data.held_reservations], ['کنسلی در انتظار', data.pending_cancellations, true], ['گزارش باز', data.open_reports, true], ['تغییر جایگاه', data.pending_seat_changes], ['نیازمند اصلاح', data.reservations_needing_correction, true], ['پرداخت ناموفق ۲۴ساعت', data.failed_payments_24h, true], ['فروش امروز', money(data.successful_volume_today)] ]; root.innerHTML = metrics.map(([label, value, alert]) => `<div class="metric-card ${alert && Number(value) ? 'alert' : ''}"><span>${esc(label)}</span><b>${typeof value === 'string' && value.includes('تومان') ? value : numberFa(value)}</b></div>`).join(''); activateSupportTab(appState.supportTab); }
  catch (error) { root.innerHTML = ''; content.innerHTML = errorState(error); showError(error, 'پنل پشتیبانی در دسترس نیست'); }
}
function activateSupportTab(tab) { appState.supportTab = ['chats', 'reservations', 'cancellations', 'seatChanges', 'reports', 'payments', 'tickets'].includes(tab) ? tab : 'reservations'; $$('[data-support-tab]').forEach(b => b.classList.toggle('active', b.dataset.supportTab === appState.supportTab)); history.replaceState(null, '', `#/support/${appState.supportTab}`); loadSupportTab(appState.supportTab); }
async function loadSupportTab(tab) {
  const root = $('#supportContent'); root.innerHTML = '<div class="dashboard-loading"><span class="spinner"></span> در حال دریافت اطلاعات...</div>';
  try { if (tab === 'chats') await supportChats(root); else if (tab === 'reservations') await supportReservations(root); else if (tab === 'cancellations') await supportCancellations(root); else if (tab === 'seatChanges') await supportSeatChanges(root); else if (tab === 'reports') await supportReports(root); else if (tab === 'payments') await supportPayments(root); else if (tab === 'tickets') await supportTickets(root); }
  catch (error) { root.innerHTML = errorState(error); showError(error, 'دریافت اطلاعات پشتیبانی ناموفق بود'); }
}
async function supportReservations(root, filters = {}) {
  const params = new URLSearchParams({ page: 1, page_size: 100, ...filters }); Object.keys(filters).forEach(k => { if (!filters[k]) params.delete(k); }); const raw = await rawGet(`/support/reservations?${params}`); const items = normalizeList(raw.data);
  root.innerHTML = `<div class="support-toolbar"><b>${numberFa(raw.meta?.total || items.length)} رزرو</b><form id="supportReservationFilter"><select name="status"><option value="">همه وضعیت‌ها</option><option value="held">موقت</option><option value="paid">پرداخت‌شده</option><option value="canceled">لغوشده</option><option value="refunded">مسترد</option></select><select name="review_status"><option value="">همه بررسی‌ها</option><option value="not_reviewed">بررسی‌نشده</option><option value="verified">تأییدشده</option><option value="needs_correction">نیازمند اصلاح</option></select><input name="user_id" type="number" placeholder="شناسه کاربر"><button class="button button-soft button-xs">فیلتر</button></form></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>رزرو</th><th>کاربر</th><th>مسابقه</th><th>مبلغ</th><th>وضعیت</th><th>بررسی</th><th>عملیات</th></tr></thead><tbody>${items.map(r => `<tr><td>#${numberFa(r.id)}</td><td>${esc(r.first_name)} ${esc(r.last_name)}<br><small>${esc(r.email || r.phone)}</small></td><td>${esc(r.home_team)} - ${esc(r.away_team)}<br><small>${esc(dateFa(r.starts_at))}</small></td><td>${money(r.total_amount)}</td><td>${statusBadge(r.status)}</td><td>${statusBadge(r.support_review_status)}</td><td class="actions-cell"><button class="button button-success button-xs" data-action="support-review-reservation" data-id="${r.id}" data-status="verified">تأیید</button><button class="button button-danger button-xs" data-action="support-review-reservation" data-id="${r.id}" data-status="needs_correction">نیاز به اصلاح</button>${r.status === 'held' ? `<button class="button button-danger button-xs" data-action="support-cancel-reservation" data-id="${r.id}">لغو</button>` : ''}<button class="button button-soft button-xs" data-action="support-seat-correct" data-id="${r.id}">اصلاح صندلی</button><button class="button button-soft button-xs" data-action="support-deactivate-user" data-user="${r.user_id}">غیرفعال‌سازی کاربر</button></td></tr>`).join('') || `<tr><td colspan="7">${emptyInline('رزروی پیدا نشد.')}</td></tr>`}</tbody></table></div>`;
  $('#supportReservationFilter').addEventListener('submit', e => { e.preventDefault(); supportReservations(root, formToObject(e.currentTarget)); });
}
function supportReviewReservation(id, status) { showFormDialog({ title: status === 'verified' ? 'تأیید رزرو' : 'علامت‌گذاری برای اصلاح', description: 'نتیجه بررسی پشتیبان در رکورد رزرو ثبت می‌شود.', body: `<form id="supportReviewForm"><label class="field"><span>یادداشت پشتیبان ${status === 'needs_correction' ? '(الزامی)' : ''}</span><textarea name="note" ${status === 'needs_correction' ? 'required minlength="3"' : ''}></textarea></label></form>`, confirmText: 'ثبت نتیجه', onConfirm: async () => { const note = $('#supportReviewForm').elements.note.value.trim() || null; await api.post(`/support/reservations/${id}/review`, { review_status: status, note }, { loader: true }); closeDialog($('#formDialog')); toast('نتیجه بررسی ثبت شد'); loadSupportTab('reservations'); } }); }
function supportCancelReservation(id) { showFormDialog({ title: 'لغو رزرو موقت', description: 'ظرفیت رزروشده آزاد می‌شود.', body: `<form id="supportCancelForm"><label class="field"><span>دلیل لغو</span><textarea name="reason" minlength="3" required></textarea></label></form>`, confirmText: 'لغو رزرو', danger: true, onConfirm: async () => { const reason = $('#supportCancelForm').elements.reason.value.trim(); await api.post(`/support/reservations/${id}/cancel`, { reason }, { loader: true }); closeDialog($('#formDialog')); toast('رزرو لغو شد'); loadSupportTab('reservations'); loadSupportDashboard(); } }); }
async function supportSeatCorrection(id) { try { const options = normalizeList(await api.get(`/seat-change-options?reservation_id=${id}`, { loader: true })); if (!options.length) throw new Error('جایگاه جایگزین هم‌قیمت وجود ندارد.'); showFormDialog({ title: 'اصلاح جایگاه رزرو', description: 'اصلاح از مسیر امن تغییر جایگاه انجام می‌شود.', body: `<form id="seatCorrectionForm"><label class="field"><span>بلیط جایگزین</span><select name="new_ticket_id">${options.map(o => `<option value="${o.ticket_id}">${esc(o.category_name)} / ${esc(o.section_code)} / ${esc(o.row_code || '—')} / ${esc(o.seat_code || '—')}</option>`).join('')}</select></label><label class="field"><span>توضیح اصلاح</span><textarea name="note" minlength="3" required></textarea></label></form>`, confirmText: 'اعمال اصلاح', onConfirm: async () => { const f = $('#seatCorrectionForm'); await api.post(`/support/reservations/${id}/seat-correction`, { new_ticket_id: Number(f.elements.new_ticket_id.value), note: f.elements.note.value.trim() }, { loader: true }); closeDialog($('#formDialog')); toast('جایگاه رزرو اصلاح شد'); loadSupportTab('reservations'); } }); } catch (error) { showError(error, 'اصلاح جایگاه ممکن نیست'); } }
function supportDeactivateUser(userId) { showFormDialog({ title: 'غیرفعال‌سازی حساب کاربر', description: 'رزروهای موقت کاربر آزاد و نشست‌های فعال او باطل می‌شوند.', body: `<form id="deactivateForm"><label class="field"><span>دلیل</span><textarea name="reason" minlength="3" required></textarea></label></form>`, confirmText: 'غیرفعال‌سازی', danger: true, onConfirm: async () => { const reason = $('#deactivateForm').elements.reason.value.trim(); await api.post(`/support/users/${userId}/deactivate`, { reason }, { loader: true }); closeDialog($('#formDialog')); toast('حساب کاربر غیرفعال شد'); loadSupportTab('reservations'); } }); }
async function supportCancellations(root, status = '') { const raw = await rawGet(`/support/cancellation-requests?page=1&page_size=100${status ? `&status=${status}` : ''}`); const items = normalizeList(raw.data); root.innerHTML = `<div class="support-toolbar"><b>${numberFa(raw.meta?.total || items.length)} درخواست کنسلی</b><select id="supportCancelStatus"><option value="">همه وضعیت‌ها</option><option value="pending">در انتظار</option><option value="approved">تأییدشده</option><option value="rejected">ردشده</option></select></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>درخواست</th><th>کاربر</th><th>مسابقه</th><th>جریمه</th><th>استرداد</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>${items.map(r => `<tr><td>#${numberFa(r.id)}<br><small>${esc(r.reason)}</small></td><td>${esc(r.first_name)} ${esc(r.last_name)}</td><td>${esc(r.home_team)} - ${esc(r.away_team)}</td><td>${numberFa(r.penalty_percentage)}٪</td><td>${money(r.refund_amount)}</td><td>${statusBadge(r.status)}</td><td class="actions-cell">${r.status === 'pending' ? `<button class="button button-success button-xs" data-action="review-cancellation" data-id="${r.id}" data-approve="true">تأیید</button><button class="button button-danger button-xs" data-action="review-cancellation" data-id="${r.id}" data-approve="false">رد</button>` : '—'}</td></tr>`).join('') || `<tr><td colspan="7">${emptyInline('درخواستی وجود ندارد.')}</td></tr>`}</tbody></table></div>`; $('#supportCancelStatus').value = status; $('#supportCancelStatus').addEventListener('change', e => supportCancellations(root, e.target.value)); }
function reviewSimpleRequest(type, id, approve) { const isCancel = type === 'cancellation'; showFormDialog({ title: `${approve ? 'تأیید' : 'رد'} درخواست ${isCancel ? 'کنسلی' : 'تغییر جایگاه'}`, body: `<form id="reviewRequestForm"><label class="field"><span>یادداشت پشتیبان</span><textarea name="note" maxlength="2000"></textarea></label></form>`, confirmText: approve ? 'تأیید درخواست' : 'رد درخواست', danger: !approve, onConfirm: async () => { const note = $('#reviewRequestForm').elements.note.value.trim() || null; await api.post(`/support/${isCancel ? 'cancellation' : 'seat-change'}-requests/${id}/review`, { approve, note }, { loader: true }); closeDialog($('#formDialog')); toast('نتیجه بررسی ثبت شد'); loadSupportTab(isCancel ? 'cancellations' : 'seatChanges'); loadSupportDashboard(); } }); }
async function supportSeatChanges(root, status = '') { const raw = await rawGet(`/support/seat-change-requests?page=1&page_size=100${status ? `&status=${status}` : ''}`); const items = normalizeList(raw.data); root.innerHTML = `<div class="support-toolbar"><b>${numberFa(raw.meta?.total || items.length)} درخواست تغییر</b><select id="supportSeatStatus"><option value="">همه وضعیت‌ها</option><option value="pending">در انتظار</option><option value="approved">تأییدشده</option><option value="rejected">ردشده</option><option value="expired">منقضی</option></select></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>درخواست</th><th>کاربر</th><th>مسابقه</th><th>جایگاه فعلی</th><th>جایگاه جدید</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>${items.map(r => `<tr><td>#${numberFa(r.id)}</td><td>${esc(r.first_name)} ${esc(r.last_name)}</td><td>${esc(r.home_team)} - ${esc(r.away_team)}</td><td>${esc(r.old_section)} / ${esc(r.old_row || '—')} / ${esc(r.old_seat || '—')}</td><td>${esc(r.new_section)} / ${esc(r.new_row || '—')} / ${esc(r.new_seat || '—')}</td><td>${statusBadge(r.status)}</td><td class="actions-cell">${r.status === 'pending' ? `<button class="button button-success button-xs" data-action="review-seat-change" data-id="${r.id}" data-approve="true">تأیید</button><button class="button button-danger button-xs" data-action="review-seat-change" data-id="${r.id}" data-approve="false">رد</button>` : '—'}</td></tr>`).join('') || `<tr><td colspan="7">${emptyInline('درخواستی وجود ندارد.')}</td></tr>`}</tbody></table></div>`; $('#supportSeatStatus').value = status; $('#supportSeatStatus').addEventListener('change', e => supportSeatChanges(root, e.target.value)); }
async function supportReports(root, status = '') { const raw = await rawGet(`/support/reports?page=1&page_size=100${status ? `&status=${status}` : ''}`); const items = normalizeList(raw.data); root.innerHTML = `<div class="support-toolbar"><b>${numberFa(raw.meta?.total || items.length)} گزارش</b><select id="supportReportStatus"><option value="">همه وضعیت‌ها</option><option value="pending">در انتظار</option><option value="in_review">در بررسی</option><option value="resolved">حل‌شده</option><option value="rejected">ردشده</option></select></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>گزارش</th><th>کاربر</th><th>دسته</th><th>شرح</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>${items.map(r => `<tr><td>#${numberFa(r.id)}<br><b>${esc(r.subject)}</b></td><td>${esc(r.first_name)} ${esc(r.last_name)}<br><small>${esc(r.email || r.phone)}</small></td><td>${esc(r.category_name)}</td><td>${esc(String(r.description).slice(0, 90))}${String(r.description).length > 90 ? '…' : ''}</td><td>${statusBadge(r.status)}</td><td><button class="button button-primary button-xs" data-action="support-update-report" data-id="${r.id}" data-current="${attr(r.status)}">رسیدگی</button></td></tr>`).join('') || `<tr><td colspan="6">${emptyInline('گزارشی وجود ندارد.')}</td></tr>`}</tbody></table></div>`; $('#supportReportStatus').value = status; $('#supportReportStatus').addEventListener('change', e => supportReports(root, e.target.value)); }
function supportUpdateReport(id, current) { showFormDialog({ title: `رسیدگی به گزارش #${numberFa(id)}`, body: `<form id="supportReportForm"><label class="field"><span>وضعیت</span><select name="status"><option value="pending">در انتظار</option><option value="in_review">در حال بررسی</option><option value="resolved">حل‌شده</option><option value="rejected">ردشده</option></select></label><label class="field"><span>پاسخ پشتیبان</span><textarea name="response" maxlength="5000"></textarea></label></form>`, confirmText: 'ثبت نتیجه', onConfirm: async () => { const data = formToObject($('#supportReportForm')); data.response ||= null; await api.patch(`/support/reports/${id}`, data, { loader: true }); closeDialog($('#formDialog')); toast('گزارش بروزرسانی شد'); loadSupportTab('reports'); loadSupportDashboard(); } }); $('#supportReportForm').elements.status.value = current === 'resolved' || current === 'rejected' ? current : 'in_review'; }
async function supportPayments(root) { const raw = await rawGet('/support/payments/suspicious?page=1&page_size=100'); const items = normalizeList(raw.data); root.innerHTML = `<div class="support-toolbar"><b>${numberFa(raw.meta?.total || items.length)} پرداخت مشکوک</b></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>پرداخت</th><th>کاربر</th><th>رزرو</th><th>مبلغ</th><th>علت</th><th>زمان</th></tr></thead><tbody>${items.map(p => `<tr><td>#${numberFa(p.id)}</td><td>${esc(p.first_name)} ${esc(p.last_name)}<br><small>${esc(p.email || p.phone)}</small></td><td>#${numberFa(p.reservation_id)}</td><td>${money(p.amount)}</td><td>${esc(p.failure_reason || 'الگوی مشکوک شناسایی‌شده')}</td><td>${esc(dateFa(p.created_at))}</td></tr>`).join('') || `<tr><td colspan="6">${emptyInline('پرداخت مشکوکی وجود ندارد.')}</td></tr>`}</tbody></table></div>`; }
async function supportTickets(root) { const raw = await rawGet('/support/tickets?include_inactive=true&page=1&page_size=100'); const items = normalizeList(raw.data).filter(isFrontendSport); appState.supportTickets = items; root.innerHTML = `<div class="support-toolbar"><b>${numberFa(raw.meta?.total || items.length)} ردیف بلیط</b><button class="button button-primary button-xs" data-action="support-create-ticket">+ ایجاد ردیف</button></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>شناسه</th><th>مسابقه</th><th>رده / بخش</th><th>قیمت</th><th>ظرفیت</th><th>موجود</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>${items.map(t => `<tr><td>#${numberFa(t.ticket_id)}</td><td>${esc(t.home_team)} - ${esc(t.away_team)}<br><small>${esc(dateFa(t.starts_at))}</small></td><td>${esc(t.category_name)} / ${esc(t.section_code)}</td><td>${money(t.price)}</td><td>${numberFa(t.total_capacity)}</td><td>${numberFa(t.available_quantity)}</td><td>${statusBadge(t.is_active ? 'active' : 'inactive')}</td><td class="actions-cell"><button class="button button-soft button-xs" data-action="support-edit-ticket" data-id="${t.ticket_id}">ویرایش</button>${t.is_active ? `<button class="button button-danger button-xs" data-action="support-delete-ticket" data-id="${t.ticket_id}">غیرفعال</button>` : ''}</td></tr>`).join('') || `<tr><td colspan="8">${emptyInline('بلیطی وجود ندارد.')}</td></tr>`}</tbody></table></div>`; }
function ticketAdminForm(ticket = {}) {
  const matches = appState.lookups.matches;
  const categories = appState.lookups.categories;
  const amenities = appState.lookups.amenities;
  const selectedCategoryId = ticket.ticket_category_id || categories.find(category => category.code === ticket.category_code)?.id;
  const selectedAmenityIds = new Set((Array.isArray(ticket.amenity_ids) ? ticket.amenity_ids : []).map(item => Number(item?.id ?? item)));
  const editing = Boolean(ticket.ticket_id);
  const activeControl = editing && ticket.is_active !== false
    ? '<input type="checkbox" name="is_active" checked disabled><span class="switch"></span><span>فعال است؛ برای غیرفعال‌سازی از دکمه اختصاصی استفاده کن</span>'
    : `<input type="checkbox" name="is_active" ${ticket.is_active !== false ? 'checked' : ''}><span class="switch"></span><span>فعال باشد</span>`;
  return `<form id="ticketAdminForm" class="stack-form">
    <div class="field-group">
      <label class="field"><span>مسابقه</span><select name="match_id" ${editing ? 'disabled' : ''} required>${matches.map(match => `<option value="${match.id}" ${String(match.id) === String(ticket.match_id) ? 'selected' : ''}>${esc(match.home_team)} - ${esc(match.away_team)} · ${esc(dateFa(match.starts_at, { dateOnly: true }))}</option>`).join('')}</select></label>
      <label class="field"><span>رده بلیط</span><select name="ticket_category_id" required>${categories.map(category => `<option value="${category.id}" ${String(category.id) === String(selectedCategoryId) ? 'selected' : ''}>${esc(category.name)}</option>`).join('')}</select></label>
    </div>
    <div class="field-group">
      <label class="field"><span>بخش</span><input name="section_code" required maxlength="50" value="${attr(ticket.section_code || '')}"></label>
      <label class="field"><span>قیمت</span><input name="price" type="number" min="0" required value="${attr(ticket.price || '')}"></label>
    </div>
    <label class="switch-row"><input type="checkbox" name="is_numbered" ${ticket.is_numbered ? 'checked' : ''}><span class="switch"></span><span>صندلی شماره‌دار</span></label>
    <div class="field-group">
      <label class="field"><span>ردیف</span><input name="row_code" maxlength="50" value="${attr(ticket.row_code || '')}"></label>
      <label class="field"><span>صندلی</span><input name="seat_code" maxlength="50" value="${attr(ticket.seat_code || '')}"></label>
    </div>
    <label class="field"><span>ظرفیت کل</span><input name="total_capacity" type="number" min="1" required value="${attr(ticket.total_capacity || 1)}"></label>
    <p id="ticketNumberingHint" class="muted"></p>
    <label class="field"><span>امکانات</span><select name="amenity_ids" multiple size="4">${amenities.map(amenity => `<option value="${amenity.id}" ${selectedAmenityIds.has(Number(amenity.id)) ? 'selected' : ''}>${esc(amenity.name)}</option>`).join('')}</select></label>
    <label class="switch-row">${activeControl}</label>
  </form>`;
}

function bindTicketAdminForm() {
  const form = $('#ticketAdminForm');
  if (!form) return;
  const numbered = form.elements.is_numbered;
  const row = form.elements.row_code;
  const seat = form.elements.seat_code;
  const capacity = form.elements.total_capacity;
  const hint = $('#ticketNumberingHint');
  const sync = () => {
    const isNumbered = numbered.checked;
    row.required = isNumbered;
    seat.required = isNumbered;
    row.disabled = !isNumbered;
    seat.disabled = !isNumbered;
    if (isNumbered) {
      capacity.value = '1';
      capacity.readOnly = true;
      hint.textContent = 'برای بلیط شماره‌دار، ردیف و صندلی الزامی و ظرفیت دقیقاً ۱ است.';
    } else {
      row.value = '';
      seat.value = '';
      capacity.readOnly = false;
      hint.textContent = 'برای ورودی عمومی، ردیف و صندلی ارسال نمی‌شود و ظرفیت می‌تواند بیشتر از ۱ باشد.';
    }
  };
  numbered.addEventListener('change', sync);
  sync();
}

function collectTicketAdminPayload(form, partial = false) {
  const data = formToObject(form);
  const activeInput = form.elements.is_active;
  const payload = {
    ticket_category_id: Number(data.ticket_category_id),
    section_code: String(data.section_code || '').trim(),
    is_numbered: Boolean(data.is_numbered),
    price: String(data.price),
    total_capacity: Number(data.total_capacity),
    amenity_ids: [...form.elements.amenity_ids.selectedOptions].map(option => Number(option.value)),
  };
  if (!partial) {
    payload.match_id = Number(form.elements.match_id.value);
    payload.is_active = activeInput ? activeInput.checked : true;
  } else if (activeInput && !activeInput.disabled && activeInput.checked) {
    payload.is_active = true;
  }
  if (payload.is_numbered) {
    payload.row_code = String(form.elements.row_code.value || '').trim() || null;
    payload.seat_code = String(form.elements.seat_code.value || '').trim() || null;
  } else {
    payload.row_code = null;
    payload.seat_code = null;
  }
  return payload;
}

function supportCreateTicket() {
  showFormDialog({
    title: 'ایجاد ردیف بلیط',
    description: 'اطلاعات با قواعد ظرفیت و شماره‌گذاری بک‌اند همگام می‌شود.',
    body: ticketAdminForm(),
    confirmText: 'ایجاد بلیط',
    onConfirm: async () => {
      const payload = collectTicketAdminPayload($('#ticketAdminForm'));
      await api.post('/support/tickets', payload, { loader: true });
      closeDialog($('#formDialog'));
      toast('ردیف بلیط ایجاد شد');
      loadSupportTab('tickets');
      loadSupportDashboard();
    },
  });
  bindTicketAdminForm();
}

async function supportEditTicket(id) {
  try {
    let ticket = appState.supportTickets.find(item => String(item.ticket_id) === String(id));
    if (!ticket) {
      const raw = await rawGet('/support/tickets?include_inactive=true&page=1&page_size=100');
      appState.supportTickets = normalizeList(raw.data);
      ticket = appState.supportTickets.find(item => String(item.ticket_id) === String(id));
    }
    if (!ticket) throw new Error('بلیط در فهرست مدیریت پیدا نشد؛ فهرست را تازه‌سازی کن.');
    showFormDialog({
      title: `ویرایش بلیط #${numberFa(id)}`,
      body: ticketAdminForm(ticket),
      confirmText: 'ذخیره تغییرات',
      onConfirm: async () => {
        const payload = collectTicketAdminPayload($('#ticketAdminForm'), true);
        await api.patch(`/support/tickets/${id}`, payload, { loader: true });
        closeDialog($('#formDialog'));
        toast('بلیط بروزرسانی شد');
        loadSupportTab('tickets');
      },
    });
    bindTicketAdminForm();
  } catch (error) {
    showError(error, 'دریافت بلیط ناموفق بود');
  }
}

function supportDeleteTicket(id) { showFormDialog({ title: 'غیرفعال‌سازی ردیف بلیط', description: 'بلیط از نتایج عمومی حذف می‌شود اما برای حفظ تاریخچه پاک نخواهد شد.', body: '<div class="inline-message">این عملیات حذف نرم انجام می‌دهد.</div>', confirmText: 'غیرفعال‌سازی', danger: true, onConfirm: async () => { await api.delete(`/support/tickets/${id}`, { loader: true }); closeDialog($('#formDialog')); toast('بلیط غیرفعال شد'); loadSupportTab('tickets'); } }); }


// Chat launcher spring settings. Increase MAX_OFFSET and IMPULSE_FACTOR to make
// the button feel more strongly dragged by scrolling. Increase DAMPING to make
// the spring return more slowly (keep it below 0.90).
const SUPPORT_CHAT_MOTION_CONFIG = Object.freeze({
  IMPULSE_FACTOR: 0.70,
  MAX_IMPULSE: 16,
  MAX_OFFSET: 60,
  DAMPING: 0.86,
  STOP_THRESHOLD: 0.10,
  STRETCH_DIVISOR: 175,
  MAX_STRETCH: 0.075,
  MIN_IMPULSE: 0.20,
});

const supportChatMotion = {
  lastScrollY: window.scrollY || 0,
  offsetY: 0,
  frame: 0,
};

function prefersReducedMotion() {
  return Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}

function paintSupportChatMotion() {
  supportChatMotion.frame = 0;
  const launcher = $('#supportChatLauncher');
  if (!launcher) return;

  supportChatMotion.offsetY *= SUPPORT_CHAT_MOTION_CONFIG.DAMPING;
  if (Math.abs(supportChatMotion.offsetY) < SUPPORT_CHAT_MOTION_CONFIG.STOP_THRESHOLD) supportChatMotion.offsetY = 0;

  const stretch = 1 + Math.min(
    Math.abs(supportChatMotion.offsetY) / SUPPORT_CHAT_MOTION_CONFIG.STRETCH_DIVISOR,
    SUPPORT_CHAT_MOTION_CONFIG.MAX_STRETCH,
  );
  launcher.style.setProperty('--chat-drag-y', `${supportChatMotion.offsetY.toFixed(2)}px`);
  launcher.style.setProperty('--chat-drag-scale-y', stretch.toFixed(3));
  launcher.classList.toggle('is-scroll-dragging', supportChatMotion.offsetY !== 0);

  if (supportChatMotion.offsetY !== 0) {
    supportChatMotion.frame = requestAnimationFrame(paintSupportChatMotion);
  }
}

function resetSupportChatMotion() {
  if (supportChatMotion.frame) cancelAnimationFrame(supportChatMotion.frame);
  supportChatMotion.frame = 0;
  supportChatMotion.offsetY = 0;
  supportChatMotion.lastScrollY = window.scrollY || 0;
  const launcher = $('#supportChatLauncher');
  if (!launcher) return;
  launcher.style.setProperty('--chat-drag-y', '0px');
  launcher.style.setProperty('--chat-drag-scale-y', '1');
  launcher.classList.remove('is-scroll-dragging');
}

function handleSupportChatScroll() {
  const currentScrollY = window.scrollY || 0;
  const delta = currentScrollY - supportChatMotion.lastScrollY;
  supportChatMotion.lastScrollY = currentScrollY;

  const panelOpen = !$('#supportChatPanel')?.hidden;
  if (panelOpen || prefersReducedMotion()) {
    resetSupportChatMotion();
    return;
  }

  const impulse = Math.max(
    -SUPPORT_CHAT_MOTION_CONFIG.MAX_IMPULSE,
    Math.min(SUPPORT_CHAT_MOTION_CONFIG.MAX_IMPULSE, -delta * SUPPORT_CHAT_MOTION_CONFIG.IMPULSE_FACTOR),
  );
  if (Math.abs(impulse) < SUPPORT_CHAT_MOTION_CONFIG.MIN_IMPULSE) return;
  supportChatMotion.offsetY = Math.max(
    -SUPPORT_CHAT_MOTION_CONFIG.MAX_OFFSET,
    Math.min(SUPPORT_CHAT_MOTION_CONFIG.MAX_OFFSET, supportChatMotion.offsetY + impulse),
  );
  if (!supportChatMotion.frame) supportChatMotion.frame = requestAnimationFrame(paintSupportChatMotion);
}

function positionSupportChatDock() {
  // The dock itself stays viewport-stable. Only the circular launcher receives
  // a small springy drag while scrolling, so closing chat never changes scroll.
  const dock = $('#supportChatDock');
  if (dock) dock.style.removeProperty('top');
  resetSupportChatMotion();
}
function setChatUnread(count) {
  const value = Number(count || 0); const badge = $('#supportChatUnread');
  if (!badge) return; badge.hidden = value < 1; badge.textContent = numberFa(value > 99 ? 99 : value);
}
function chatMessageHtml(message, mineRole = 'spectator') {
  const mine = message.sender_role === mineRole;
  const name = mine ? 'شما' : `${message.first_name || message.sender_first_name || 'پشتیبان'} ${message.last_name || message.sender_last_name || ''}`.trim();
  return `<article class="chat-message ${mine ? 'mine' : 'theirs'}" data-message-id="${attr(message.id)}"><div class="chat-bubble" data-i18n-ignore dir="auto">${esc(message.body)}</div><span class="chat-message-meta"><span data-i18n-ignore dir="auto">${esc(name)}</span> · ${esc(timeFa(message.created_at))}</span></article>`;
}
function scrollChatToEnd(root) { if (root) requestAnimationFrame(() => { root.scrollTop = root.scrollHeight; }); }
async function refreshSpectatorChat({ markRead = false, silent = false } = {}) {
  if (!isAuthenticated() || appState.user?.role !== 'spectator' || !appState.online) return;
  try {
    const data = await api.get(`/support-chat?limit=100&mark_read=${markRead ? 'true' : 'false'}`);
    appState.chatConversation = data.conversation;
    setChatUnread(markRead ? 0 : data.unread_count);
    if ($('#supportChatPanel') && !$('#supportChatPanel').hidden) {
      const root = $('#supportChatMessages'); const items = normalizeList(data.messages);
      root.innerHTML = items.length ? items.map(m => chatMessageHtml(m, 'spectator')).join('') : '<div class="chat-empty">هنوز پیامی ثبت نشده؛ اولین پیام را برای پشتیبانی بفرست.</div>';
      scrollChatToEnd(root);
    }
  } catch (error) { if (!silent) showError(error, 'گفتگو در دسترس نیست'); }
}
function startChatPolling() {
  clearInterval(appState.chatPollTimer); clearInterval(appState.chatUnreadTimer);
  if (!isAuthenticated() || appState.user?.role !== 'spectator') return;
  appState.chatPollTimer = setInterval(() => { if (!$('#supportChatPanel').hidden) refreshSpectatorChat({ markRead: true, silent: true }); }, 4000);
  appState.chatUnreadTimer = setInterval(() => { if ($('#supportChatPanel').hidden) refreshSpectatorChat({ silent: true }); }, 12000);
}
async function openSupportChat() {
  const panel = $('#supportChatPanel'), launcher = $('#supportChatLauncher'); panel.hidden = false; launcher.setAttribute('aria-expanded', 'true'); positionSupportChatDock();
  const guest = !isAuthenticated(); $('#supportChatLogin').hidden = !guest; $('#supportChatForm').hidden = guest; $('#supportChatMessages').hidden = guest; $('.support-chat-welcome').hidden = guest;
  if (guest) return;
  if (appState.user.role === 'support') { closeSupportChat(); location.hash = '#/support/chats'; return; }
  await refreshSpectatorChat({ markRead: true }); startChatPolling(); $('#supportChatInput').focus();
}
function closeSupportChat() {
  const panel = $('#supportChatPanel'), launcher = $('#supportChatLauncher');
  const scrollTop = window.scrollY;
  if (panel) panel.hidden = true;
  if (launcher) launcher.setAttribute('aria-expanded', 'false');
  positionSupportChatDock();
  clearInterval(appState.chatPollTimer); appState.chatPollTimer = null;
  requestAnimationFrame(() => {
    launcher?.focus({ preventScroll: true });
    if (Math.abs(window.scrollY - scrollTop) > 1) window.scrollTo({ top: scrollTop, behavior: 'auto' });
  });
}
async function sendSpectatorChat(e) { e.preventDefault(); const input = $('#supportChatInput'); const body = input.value.trim(); if (!body) return; const button = $('button[type="submit"]', e.currentTarget); button.disabled = true; try { await api.post('/support-chat/messages', { body }); input.value=''; await refreshSpectatorChat({ markRead: true, silent: true }); } catch (error) { showError(error, 'ارسال پیام انجام نشد'); } finally { button.disabled=false; input.focus(); } }

async function supportChats(root, selectedId = null, status = '') {
  const raw = await rawGet(`/support/chats?page=1&page_size=100${status ? `&status=${status}` : ''}`); const items = normalizeList(raw.data); const unread = items.reduce((a,x)=>a+Number(x.unread_count||0),0); const badge=$('#supportChatTabBadge'); badge.hidden=unread<1; badge.textContent=numberFa(unread);
  const chosen = selectedId || appState.supportChatConversationId || items[0]?.id; appState.supportChatConversationId = chosen || null;
  root.innerHTML = `<div class="support-chat-admin"><aside class="support-chat-list"><div class="support-chat-list-header"><select id="supportChatStatusFilter"><option value="">همه گفتگوها</option><option value="open">باز</option><option value="closed">بسته</option></select></div>${items.map(c=>`<button class="support-conversation-card ${String(c.id)===String(chosen)?'active':''}" data-action="open-support-chat-thread" data-id="${c.id}"><span class="support-conversation-card-top"><b>${esc(c.first_name)} ${esc(c.last_name)}</b>${Number(c.unread_count)?`<span class="support-tab-badge">${numberFa(c.unread_count)}</span>`:''}</span><p>${esc(c.latest_message||'بدون پیام')}</p><small>${esc(dateFa(c.last_message_at))}</small></button>`).join('')||'<div class="support-chat-placeholder">هنوز گفتگویی شروع نشده است.</div>'}</aside><section class="support-chat-admin-detail" id="supportChatAdminDetail"><div class="support-chat-placeholder">یک گفتگو را برای پاسخ‌گویی انتخاب کن.</div></section></div>`;
  $('#supportChatStatusFilter').value = status; $('#supportChatStatusFilter').addEventListener('change', e=>{ appState.supportChatConversationId=null; supportChats(root, null, e.target.value); });
  if (chosen) await openSupportChatThread(chosen);
}
function renderSupportChatMessages(messages) {
  const root = $('#supportChatAdminMessages');
  if (!root) return;
  const items = normalizeList(messages);
  root.innerHTML = items.length
    ? items.map(message => chatMessageHtml(message, 'support')).join('')
    : '<div class="chat-empty">پیامی وجود ندارد.</div>';
  scrollChatToEnd(root);
}

function appendSupportChatMessage(message) {
  const root = $('#supportChatAdminMessages');
  if (!root || !message) return;
  const messageId = String(message.id || '');
  if (messageId && root.querySelector(`[data-message-id="${messageId}"]`)) return;
  root.querySelector('.chat-empty')?.remove();
  root.insertAdjacentHTML(
    'beforeend',
    chatMessageHtml({ ...message, sender_role: message.sender_role || 'support' }, 'support'),
  );
  scrollChatToEnd(root);
}

function updateSupportConversationPreview(conversationId, message) {
  const card = $(`.support-conversation-card[data-id="${conversationId}"]`);
  if (!card || !message) return;
  const preview = $('p', card);
  const timestamp = $('small', card);
  if (preview) preview.textContent = message.body || '';
  if (timestamp && message.created_at) timestamp.textContent = dateFa(message.created_at);
}

async function refreshSupportChatMessages(id, { silent = true } = {}) {
  try {
    const data = await api.get(`/support/chats/${id}?limit=100&mark_read=true`);
    if (Number(appState.supportChatConversationId) !== Number(id)) return data;
    renderSupportChatMessages(data.messages);
    return data;
  } catch (error) {
    if (!silent) showError(error, 'به‌روزرسانی گفتگو انجام نشد');
    return null;
  }
}

async function openSupportChatThread(id) {
  appState.supportChatConversationId = Number(id);
  const data = await api.get(`/support/chats/${id}?limit=100&mark_read=true`);
  const c = data.conversation;
  const detail = $('#supportChatAdminDetail');
  if (!detail) return;
  detail.innerHTML = `<header class="support-chat-admin-head"><div><h3>${esc(c.spectator_first_name)} ${esc(c.spectator_last_name)}</h3><p>${esc(c.spectator_email||c.spectator_phone||'')} · ${c.status==='open'?'گفتگوی باز':'گفتگوی بسته'}</p></div><button class="button button-soft button-xs" data-action="toggle-support-chat-status" data-id="${c.id}" data-status="${c.status==='open'?'closed':'open'}">${c.status==='open'?'بستن گفتگو':'بازگشایی'}</button></header><div class="support-chat-admin-messages" id="supportChatAdminMessages"></div><form class="support-chat-admin-composer" id="supportChatReplyForm"><textarea name="body" maxlength="2000" required placeholder="پاسخ پشتیبان..."></textarea><button class="button button-primary" type="submit">ارسال پاسخ</button></form>`;
  renderSupportChatMessages(data.messages);

  $('#supportChatReplyForm').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const textarea = form.elements.body;
    const button = $('button[type="submit"]', form);
    const body = textarea.value.trim();
    if (!body || button.disabled) return;

    button.disabled = true;
    textarea.disabled = true;
    try {
      const sentMessage = await api.post(`/support/chats/${id}/messages`, { body });
      form.reset();
      appendSupportChatMessage(sentMessage);
      updateSupportConversationPreview(id, sentMessage);
      toast('پاسخ ارسال شد');

      // Reconcile with the server without replacing the composer or the whole
      // support dashboard. Rebuilding the dashboard here previously removed
      // the freshly rendered reply and made it look as if nothing was sent.
      window.setTimeout(() => refreshSupportChatMessages(id), 250);
    } catch (error) {
      showError(error, 'ارسال پاسخ انجام نشد');
    } finally {
      textarea.disabled = false;
      button.disabled = false;
      textarea.focus();
    }
  });
}

function setupEvents() {
  window.addEventListener('hashchange', route);
  $('#themeButton').addEventListener('click', toggleTheme);
  $('#apiSettingsButton').addEventListener('click', () => { $('#apiConfigForm').elements.api_base.value = appState.apiBase; openDialog($('#apiDialog')); });
  $('#apiConfigForm').addEventListener('submit', async e => { e.preventDefault(); try { const value = normalizeApiBase(e.currentTarget.elements.api_base.value); localStorage.setItem('arenapass_api_base', value); appState.apiBase = value; closeDialog($('#apiDialog')); await checkHealth({ discover: false }); await loadLookups(); await loadAuthCapabilities(); route(); toast('تنظیمات ذخیره شد'); } catch (error) { showError(error, 'آدرس API معتبر نیست'); } });
  $('#mobileMenuButton').addEventListener('click', e => { const menu = $('#mobileMenu'); menu.hidden = !menu.hidden; e.currentTarget.setAttribute('aria-expanded', String(!menu.hidden)); });
  $('#userMenuButton').addEventListener('click', e => { const menu = $('#userMenu'); menu.hidden = !menu.hidden; e.currentTarget.setAttribute('aria-expanded', String(!menu.hidden)); });
  document.addEventListener('click', e => { if (!e.target.closest('#userMenuButton') && !e.target.closest('#userMenu')) $('#userMenu').hidden = true; });
  $('#openAuthButton').addEventListener('click', () => openAuth('password'));
  $$('[data-auth-tab]').forEach(b => b.addEventListener('click', () => activateAuthTab(b.dataset.authTab)));
  $('#passwordLoginForm').addEventListener('submit', e => { e.preventDefault(); handlePasswordLogin(e.currentTarget); });
  $('#otpRequestForm').addEventListener('submit', e => { e.preventDefault(); handleOtpRequest(e.currentTarget); });
  $('#otpVerifyForm').addEventListener('submit', e => { e.preventDefault(); handleOtpVerify(e.currentTarget); });
  $('#signupForm').addEventListener('submit', e => { e.preventDefault(); handleSignup(e.currentTarget); });
  $('#signupVerifyForm').addEventListener('submit', e => { e.preventDefault(); handleSignupVerify(e.currentTarget); });
  $$('.otp-input').forEach(input => input.addEventListener('input', () => {
    input.value = asciiDigits(input.value).replace(/\D/g, '').slice(0, 6);
  }));
  $('#heroSearchForm').addEventListener('submit', e => { e.preventDefault(); const q = e.currentTarget.elements.q.value.trim(); location.hash = `#/tickets${q ? `?q=${encodeURIComponent(q)}` : ''}`; });
  $('#ticketFilterForm').addEventListener('submit', e => { e.preventDefault(); searchTickets(1); closeFilterPanel(); });
  $('#ticketOrdering').addEventListener('change', () => searchTickets(1));
  $('#cityFilter').addEventListener('change', e => updateVenueOptions(e.target.value, false));
  $('#clearFilters').addEventListener('click', clearFilters);
  $('#mobileFilterButton').addEventListener('click', openFilterPanel);
  $('#closeFilterButton').addEventListener('click', closeFilterPanel);
  $('#filterBackdrop').addEventListener('click', closeFilterPanel);
  $('#accountTabs').addEventListener('click', e => { const b = e.target.closest('[data-account-tab]'); if (b) activateAccountTab(b.dataset.accountTab); });
  $('#supportChatLauncher').addEventListener('click', () => $('#supportChatPanel').hidden ? openSupportChat() : closeSupportChat());
  $('#supportChatForm').addEventListener('submit', sendSpectatorChat);
  $('#supportTabs').addEventListener('click', e => { const b = e.target.closest('[data-support-tab]'); if (b) activateSupportTab(b.dataset.supportTab); });
  document.addEventListener('submit', e => { /* dynamically attached forms use explicit handlers */ });
  document.addEventListener('click', handleDelegatedClick);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeFilterPanel(); closeMobileMenu(); } });
  window.addEventListener('scroll', handleSupportChatScroll, { passive: true });
  window.addEventListener('resize', () => { syncOfflineBannerHeight(); positionSupportChatDock(); if (window.innerWidth > 900) closeFilterPanel(); });
  if ('ResizeObserver' in window) new ResizeObserver(syncOfflineBannerHeight).observe($('#offlineBanner'));
  $$('dialog').forEach(dialog => dialog.addEventListener('close', () => { if (!$$('dialog[open]').length) document.body.classList.remove('dialog-open'); }));
}

async function copyText(value) {
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value);
    else {
      const area = document.createElement('textarea'); area.value = value; area.style.position = 'fixed'; area.style.opacity = '0'; document.body.appendChild(area); area.select(); document.execCommand('copy'); area.remove();
    }
    toast('کپی شد');
  } catch { toast('کپی انجام نشد', 'کد را به‌صورت دستی انتخاب و کپی کن.', 'warning'); }
}

async function handleDelegatedClick(e) {
  const target = e.target.closest('button,a'); if (!target) return;
  if (target.matches('[data-close-dialog]')) { e.preventDefault(); closeDialog(target.closest('dialog')); return; }
  if (target.matches('[data-toggle-password]')) { const input = target.parentElement.querySelector('input'); input.type = input.type === 'password' ? 'text' : 'password'; return; }
  if (target.dataset.helpTarget) { e.preventDefault(); location.hash = `#/help/${encodeURIComponent(target.dataset.helpTarget)}`; return; }
  if (target.dataset.quickSearch !== undefined) { location.hash = `#/tickets?q=${encodeURIComponent(target.dataset.quickSearch)}`; return; }
  if (target.closest('[data-sport]')) { const b = target.closest('[data-sport]'); location.hash = `#/tickets?sport=${encodeURIComponent(b.dataset.sport)}`; return; }
  if (target.dataset.page) { searchTickets(Number(target.dataset.page)); return; }
  if (target.dataset.removeFilter) { const key = target.dataset.removeFilter; const input = $('#ticketFilterForm').elements[key]; if (input) { if (input.type === 'checkbox') input.checked = false; else input.value = ''; input._cityComboboxSync?.(); } if (key === 'city_id') await updateVenueOptions('', false); searchTickets(1); return; }
  if (target.dataset.accountTab) { activateAccountTab(target.dataset.accountTab); return; }
  if (target.dataset.copy !== undefined) { await copyText(target.dataset.copy); return; }
  if (target.dataset.demoLogin) { const contact = target.dataset.demoLogin === 'support' ? 'sara.ahmadi@support.ir' : 'hossein.m@gmail.com'; $('#passwordLoginForm').elements.contact.value = contact; $('#passwordLoginForm').elements.password.value = 'Demo@123'; handlePasswordLogin($('#passwordLoginForm')); return; }
  if (target.dataset.qty) { changeTicketQuantity(target.dataset.qty === 'plus' ? 1 : -1); return; }
  const action = target.dataset.action; if (!action) return;
  e.preventDefault();
  if (action === 'retry-api') { await checkHealth(); await loadLookups(); await loadAuthCapabilities(); route(); }
  else if (action === 'reset-api') { localStorage.removeItem('arenapass_api_base'); appState.apiBase = resolveDefaultApiBase(); $('#apiConfigForm').elements.api_base.value = appState.apiBase; closeDialog($('#apiDialog')); await checkHealth(); await loadLookups(); await loadAuthCapabilities(); route(); toast('آدرس خودکار API بازیابی شد'); }
  else if (action === 'close-filters') closeFilterPanel();
  else if (action === 'close-support-chat') closeSupportChat();
  else if (action === 'chat-login') { closeSupportChat(); openAuth('password'); }
  else if (action === 'open-support-chat-thread') { await openSupportChatThread(target.dataset.id); $$('.support-conversation-card').forEach(x=>x.classList.toggle('active',x.dataset.id===target.dataset.id)); }
  else if (action === 'toggle-support-chat-status') { await api.patch(`/support/chats/${target.dataset.id}/status`,{status:target.dataset.status},{loader:true}); await openSupportChatThread(target.dataset.id); loadSupportDashboard(); }
  else if (action === 'logout') { await clearAuth(true); closeAllDialogs(); toast('از حساب خارج شدی'); location.hash = '#/home'; }
  else if (action === 'otp-back') resetOtpForm();
  else if (action === 'otp-resend') resendLoginOtp();
  else if (action === 'signup-back') resetSignupFlow(false);
  else if (action === 'signup-resend') resendSignupOtp();
  else if (action === 'ticket-detail') showTicketDetail(target.dataset.id);
  else if (action === 'clear-filters') await clearFilters();
  else if (action === 'reserve-current') reserveCurrentTicket();
  else if (action === 'reservation-detail') showReservationDetail(target.dataset.id);
  else if (action === 'pay-reservation') openPayment(target.dataset.id, target.dataset.amount);
  else if (action === 'cancel-reservation') openCancellation(target.dataset.id);
  else if (action === 'seat-change') openSeatChange(target.dataset.id);
  else if (action === 'show-issued-ticket') showIssuedTicket(target.dataset.payload);
  else if (action === 'wallet-topup') openWalletTopup();
  else if (action === 'new-report') { if (ensureSpectator()) openNewReport({ reservation: target.dataset.reservation, ticket: target.dataset.ticket }); }
  else if (action === 'request-password-otp') requestPasswordOtp();
  else if (action === 'change-contact') openContactChange();
  else if (action === 'retry-account') loadAccountTab(appState.accountTab);
  else if (action === 'support-create-ticket') supportCreateTicket();
  else if (action === 'support-review-reservation') supportReviewReservation(target.dataset.id, target.dataset.status);
  else if (action === 'support-cancel-reservation') supportCancelReservation(target.dataset.id);
  else if (action === 'support-seat-correct') supportSeatCorrection(target.dataset.id);
  else if (action === 'support-deactivate-user') supportDeactivateUser(target.dataset.user);
  else if (action === 'review-cancellation') reviewSimpleRequest('cancellation', target.dataset.id, target.dataset.approve === 'true');
  else if (action === 'review-seat-change') reviewSimpleRequest('seat-change', target.dataset.id, target.dataset.approve === 'true');
  else if (action === 'support-update-report') supportUpdateReport(target.dataset.id, target.dataset.current);
  else if (action === 'support-edit-ticket') supportEditTicket(target.dataset.id);
  else if (action === 'support-delete-ticket') supportDeleteTicket(target.dataset.id);
}

function setupTheme() { const saved = localStorage.getItem('arenapass_theme'); const preferred = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; document.documentElement.dataset.theme = saved || preferred; }
function toggleTheme() { const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = next; localStorage.setItem('arenapass_theme', next); }

async function init() {
  setupTheme(); restoreAuth(); setupEvents();
  const online = await checkHealth(); await loadLookups(); await loadAuthCapabilities(); restorePendingSignup();
  if (online && isAuthenticated()) { try { const p = await api.get('/profile'); appState.user = { ...appState.user, ...p }; TokenStore.set('user', JSON.stringify(appState.user), TokenStore.persistent()); updateAuthUI(); } catch (error) { if (error.status === 401) clearAuth(false); } }
  route(); positionSupportChatDock(); startChatPolling(); if (isAuthenticated() && appState.user?.role === 'spectator') refreshSpectatorChat({ silent: true });
}

document.addEventListener('DOMContentLoaded', init);
