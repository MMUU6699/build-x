import 'dart:async';
import '../api_service.dart';
// import '../../models/token_usage.dart'; // Removed

class ChatApiService {
  static final ApiService _apiService = ApiService();

  static Future<Stream<String>> sendMessage({
    required String message,
    required List<Map<String, dynamic>> history,
  }) async {
    return await _apiService.sendMessage(message, history);
  }

  static Future<String> sendMessageSync({
    required String message,
    required List<Map<String, dynamic>> history,
  }) async {
    return await _apiService.sendMessageSync(message, history);
  }

  static Future<Stream<String>> sendMessageStream({
    required dynamic config,
    required String modelId,
    required String prompt,
    List<Map<String, dynamic>>? history,
    List<Map<String, dynamic>>? messages,
  }) async {
    return await _apiService.sendMessage(prompt, history ?? []);
  }

  static Future<String> generateText({
    required dynamic config,
    required String modelId,
    required String prompt,
  }) async {
    return await _apiService.sendMessageSync(prompt, []);
  }

  static Future<bool> testConnection() async {
    return await _apiService.testConnection();
  }

  static String get modelName => _apiService.modelName;
  static String get apiUrl => _apiService.apiUrl;

  // Dummy token usage for compatibility
  static dynamic getTokenUsage() {
    return {
      'promptTokens': 0,
      'completionTokens': 0,
      'totalTokens': 0,
    };
  }
}