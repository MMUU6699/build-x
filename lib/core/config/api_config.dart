import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiConfig {
  static String _apiUrl = "";
  static DateTime? _lastLoadTime;
  static const Duration _cacheDuration = Duration(minutes: 30);

  // رابط RAW من Gist
  // غير الرابط إلى Gist URL الخاص بك
  static const String configUrl =
      "https://gist.githubusercontent.com/dididj883u/dcd084b749a446a5a2c042715d92bf50/raw/ebf3a5c9f38ff78b47d2b783536a13d512f14427/gistfile1.txt";

  /// جلب إعدادات API من Gist
  static Future<void> loadConfig() async {
    try {
      final response = await http.get(Uri.parse(configUrl)).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception('Config loading timeout');
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _apiUrl = (data["api_url"] ?? "").toString().trim();
        _lastLoadTime = DateTime.now();
        print("✓ Loaded API URL: $_apiUrl");
      } else {
        print("✗ Failed to load config: ${response.statusCode}");
        _setDefaultUrl();
      }
    } catch (e) {
      print("✗ Error loading config: $e");
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
