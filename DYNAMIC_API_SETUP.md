# نظام إدارة API الديناميكي

## الوصف
هذا النظام يسمح بتحديث رابط API بدون الحاجة لإعادة بناء التطبيق. يتم جلب الرابط من ملف JSON على GitHub Gist.

## كيفية الإعداد

### 1. إنشاء Gist على GitHub

1. انتقل إلى [gist.github.com](https://gist.github.com)
2. أنشئ Gist جديد بالملف التالي:

**اسم الملف:** `config.json`

**المحتوى:**
```json
{
  "api_url": "https://your-tunnel.trycloudflare.com"
}
```

3. احسب رابط **RAW** للملف (يظهر زر "Raw" في الزاوية العلوية اليمنى)
4. انسخ الرابط - يجب أن يبدو مثل:
```
https://gist.githubusercontent.com/USERNAME/GIST_ID/raw/HASH/config.json
```

### 2. تحديث الرابط في التطبيق

افتح ملف `lib/core/config/api_config.dart` وحدّث:

```dart
static const String configUrl = "YOUR_GIST_RAW_URL";
```

### 3. بدء التطبيق

التطبيق سيجلب الرابط تلقائياً عند البدء. لا تحتاج لإعادة بناء!

## الملفات المعدّلة

### `lib/core/config/api_config.dart` ✓
- إنشاء فئة `ApiConfig` لإدارة الرابط الديناميكي
- دعم التخزين المؤقت (Cache) لمدة 30 دقيقة
- معالجة الأخطاء والقيم الافتراضية

### `lib/main.dart` ✓
- استدعاء `ApiConfig.loadConfig()` في `main()`
- تحميل الرابط قبل تشغيل التطبيق

### `lib/core/services/api/chat_api_service.dart` ✓
- إضافة دالة `_getBaseUrl()` للحصول على الرابط من `ApiConfig`
- تحديث جميع الدوال لاستخدام الرابط الديناميكي:
  - `testConnection()`
  - `_sendStreamRequest()`
  - `_sendTextRequest()`

## أمثلة الاستخدام

### الحصول على الرابط الحالي
```dart
String apiUrl = ApiConfig.apiUrl;
```

### تحديث الرابط يدوياً (للاختبار)
```dart
ApiConfig.apiUrl = "https://new-url.trycloudflare.com";
```

### إعادة تحميل الإعدادات
```dart
await ApiConfig.reloadConfig();
```

### التحقق من تحميل الرابط
```dart
if (ApiConfig.isConfigLoaded()) {
  print("API URL: ${ApiConfig.apiUrl}");
} else {
  print("API URL not loaded yet");
}
```

## الميزات

✓ **تحديث بدون إعادة بناء** - غيّر الرابط في Gist والتطبيق سيستخدم الرابط الجديد
✓ **معالجة الأخطاء** - إذا فشل التحميل، سيحاول استخدام قيمة افتراضية
✓ **التخزين المؤقت** - لا يعيد تحميل الرابط أكثر من مرة كل 30 دقيقة
✓ **سهل الاستخدام** - لا حاجة لتعديل الكود

## استكشاف الأخطاء

### لا يتم توصيل API
- تحقق من أن رابط Gist صحيح في `ApiConfig.configUrl`
- تأكد من أن JSON يحتوي على `"api_url"` بالفعل
- تحقق من أن الإنترنت متصل

### الرابط لا يتحدّث بعد تعديل Gist
- تطبيق Gist قد يأخذ بعض الوقت لتحديث الملف
- جرّب إعادة تشغيل التطبيق
- استخدم `ApiConfig.reloadConfig()` لإعادة تحميل يدوي

### خطأ "API URL is not configured"
- تحقق من أن `ApiConfig.apiUrl` ليس فارغاً
- تأكد من أن الرابط يبدأ بـ `http://` أو `https://`

## الملاحظات الأمان

- ⚠️ لا تضع مفاتيح API في ملف Gist العام
- استخدم متغيرات البيئة (`.env`) للمعلومات الحساسة
- ملف Gist يجب أن يكون **خاص** إذا كان يحتوي على معلومات حساسة
