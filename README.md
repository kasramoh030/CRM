# CRM

## Motion graphics for @framebaz

این ریپو یک موتور ساخت **موشن‌گرافیک / موشن استوری / ریلز** (عمودی ۹:۱۶، ۱۰۸۰×۱۹۲۰، ۳۰fps)
با **گویندگی فارسی + زیرنویس انگلیسی** را در پوشهٔ [`motion/`](motion/) نگه می‌دارد.

خروجی‌های آمادهٔ آپلود در `motion/out/` (بعد از اجرای رندر):

| فایل | توضیح |
|---|---|
| `framebaz_reel_44s_music.mp4` | نسخهٔ اصلی ۴۳.۹ ثانیه — گویندگی + موسیقی |
| `framebaz_reel_44s_vonoly.mp4` | فقط گویندگی (برای گذاشتن آهنگ ترند) |
| `framebaz_reel_30s_music.mp4` | نسخهٔ کوتاه ۲۹.۴ ثانیه |
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
