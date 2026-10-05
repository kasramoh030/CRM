# CRM

## Motion graphics for @framebaz
## دانلود فایل‌ها

سه راه داری:

1. **صفحهٔ دانلود (زنده)**: سرور محلی روی پورت `8080` ساخته می‌شود و به‌صورت
   «پیش‌نمایش زنده» نمایش داده می‌شود؛ در همان صفحه روی «دانلود» هر فایل بزن.

   ```bash
   cd motion/deliverables
   python3 -m http.server 8080 --bind 0.0.0.0
   ```

2. **از پنل چت**: فایل‌ها در نمایشگر فایل قابل مشاهده و دانلود هستند
   (مثلاً `motion/deliverables/framebaz_reel_full_music.mp4`).

3. **بازسازی کامل** (اگر سندباکس ریست شد و فایل‌ها پاک شدند):

   ```bash
   cd motion
   TOOLS=/opt/framebaz-tools bash tools/bootstrap.sh   # نصب ابزارها (~۱ دقیقه)
   bash tools/make_all.sh                              # ساخت دوباره همه چیز (~۱۳ دقیقه)
   ```

> نکته: پوشه‌هایی با نام `out`، `build` و `dist` در اسنپ‌شات ورک‌اسپیس ذخیره **نمی‌شوند**؛
> به همین دلیل خروجی‌ها در `deliverables/` و فایل‌های موقت در `work/` قرار می‌گیرند.



این ریپو یک موتور ساخت **موشن‌گرافیک / موشن استوری / ریلز** (عمودی ۹:۱۶، ۱۰۸۰×۱۹۲۰، ۳۰fps)
با **گویندگی فارسی + زیرنویس انگلیسی** و **کاراکتر تصویری اختصاصی (فریم‌باز)** را در پوشهٔ [`motion/`](motion/) نگه می‌دارد.

خروجی‌های آمادهٔ آپلود در `motion/out/` (بعد از اجرای رندر):

| فایل | توضیح |
|---|---|
| `framebaz_reel_full_music.mp4` | نسخهٔ اصلی ~۴۹ ثانیه، ۹ صحنه — گویندگی + موسیقی |
| `framebaz_reel_full_vonoly.mp4` | فقط گویندگی (برای گذاشتن آهنگ ترند) |
| `framebaz_reel_short_music.mp4` | نسخهٔ کوتاه ~۳۱ ثانیه |
| `cover_frame.png` / `cover.png` | کاور ریلز / کاور ثابت |
| `storyboard.md` , `storyboard.html` | استوری‌بورد صحنه‌به‌صحنه |
| `subtitles_fa.srt` , `subtitles_en.srt` | زیرنویس‌ها |

* راهنمای فارسی ویرایش: [`motion/راهنمای-ویرایش.md`](motion/راهنمای-ویرایش.md)
* مستندات فنی (انگلیسی): [`motion/README.md`](motion/README.md)

ساخت دوباره:

```bash
cd motion
export PYTHONPATH=~/.local/share/framebaz/pylibs:$(pwd)
bash tools/make_all.sh
```
