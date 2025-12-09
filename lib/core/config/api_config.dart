import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiConfig {
  static String _apiUrl = "";
  static DateTime? _lastLoadTime;
  static const Duration _cacheDuration = Duration(minutes: 30);

  // رابط RAW من Gist - يحتوي على API URL الديناميكي
  static const String configUrl =
      "https://gist.githubusercontent.com/MMUU6699/f86a0eaee693eafc7867efbd8a1f05aa/raw/config.json";

  /// جلب إعدادات API من Gist
  static Future<void> loadConfig() async {
    try {
      print("📡 Loading config from: $configUrl");
      final response = await http.get(Uri.parse(configUrl)).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception('Config loading timeout');
        },
      );

      if (response.statusCode == 200) {
        print("📦 Config response received: ${response.body}");
        final data = json.decode(response.body);
        _apiUrl = (data["api_url"] ?? "").toString().trim();
        _lastLoadTime = DateTime.now();
        print("✅ Loaded API URL: $_apiUrl");
      } else {
        print("❌ Failed to load config: ${response.statusCode}");
        print("Response body: ${response.body}");
        _setDefaultUrl();
      }
    } catch (e) {
      print("❌ Error loading config: $e");
      print("Stack trace: ${StackTrace.current}");
      _setDefaultUrl();
    }
  }

  /// إعادة تحميل الإعدادات (يمكن استدعاؤها يدوياً)
  static Future<void> reloadConfig() async {
    await loadConfig();
  }

  /// الحصول على رابط API
  static String get apiUrl => _apiUrl;

  /// تعيين رابط API مباشرة (للاختبار)
  static set apiUrl(String url) {
    _apiUrl = url.trim();
    _lastLoadTime = DateTime.now();
  }

  /// تعيين رابط افتراضي في حالة الفشل
  static void _setDefaultUrl() {
    _apiUrl = "";
    _lastLoadTime = DateTime.now();
    print("⚠ Using empty API URL as fallback");
  }

  /// التحقق من تحميل الرابط بنجاح
  static bool isConfigLoaded() {
    return _apiUrl.isNotEmpty;
  }

  /// التحقق مما إذا كان يجب إعادة تحميل الإعدادات
  static bool shouldReload() {
    if (_lastLoadTime == null) return true;
    final timeSinceLastLoad = DateTime.now().difference(_lastLoadTime!);
    return timeSinceLastLoad > _cacheDuration;
  }

  /// الحصول على وقت آخر تحميل
  static DateTime? get lastLoadTime => _lastLoadTime;
}
