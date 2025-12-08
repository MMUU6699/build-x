import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../config/api_config.dart';
import '../../providers/settings_provider.dart';

class ChatApiService {
  /// الحصول على baseUrl (من ApiConfig أو من config)
  static String _getBaseUrl(ProviderConfig config) {
    String baseUrl = config.baseUrl;
    
    // إذا كان baseUrl فارغاً أو غير صحيح، حاول استخدام ApiConfig
    if (baseUrl.isEmpty || !baseUrl.startsWith('http')) {
      baseUrl = ApiConfig.apiUrl;
    }
    
    // تنظيف الرابط
    if (baseUrl.endsWith('/')) {
      baseUrl = baseUrl.substring(0, baseUrl.length - 1);
    }
    
    return baseUrl;
  }

  /// Send message with streaming response
  static Future<Stream<String>> sendMessageStream({
    required dynamic config,
    required String modelId,
    required String prompt,
    List<Map<String, dynamic>>? history,
    List<Map<String, dynamic>>? messages,
  }) async {
    if (config is! ProviderConfig) {
      throw Exception('Invalid config type');
    }

    return _sendStreamRequest(
      config: config,
      modelId: modelId,
      prompt: prompt,
      messages: messages ?? history ?? [],
    );
  }

  /// Send message synchronously
  static Future<String> sendMessageSync({
    required String message,
    required List<Map<String, dynamic>> history,
  }) async {
    throw Exception('Sync mode not implemented. Use sendMessageStream instead.');
  }

  /// Generate text (for conversation titles, etc.)
  static Future<String> generateText({
    required dynamic config,
    required String modelId,
    required String prompt,
  }) async {
    if (config is! ProviderConfig) {
      throw Exception('Invalid config type');
    }

    return _sendTextRequest(
      config: config,
      modelId: modelId,
      prompt: prompt,
    );
  }

  /// Test connection to the API
  static Future<bool> testConnection(ProviderConfig config) async {
    try {
      final baseUrl = _getBaseUrl(config);

      if (baseUrl.isEmpty) {
        print("✗ baseUrl is empty, cannot test connection");
        return false;
      }

      final response = await http.get(
        Uri.parse('$baseUrl/models'),
        headers: {
          'Authorization': 'Bearer ${config.apiKey}',
        },
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Private: Build and send streaming request
  static Future<Stream<String>> _sendStreamRequest({
    required ProviderConfig config,
    required String modelId,
    required String prompt,
    required List<Map<String, dynamic>> messages,
  }) async {
    try {
      final baseUrl = _getBaseUrl(config);

      if (baseUrl.isEmpty) {
        throw Exception('API URL is not configured. Please set the API URL in your config or Gist.');
      }

      final chatPath = (config.chatPath ?? '').startsWith('/')
          ? config.chatPath ?? ''
          : '/${config.chatPath ?? ''}';

      final url = Uri.parse('$baseUrl$chatPath');

      // Build messages list
      final messagesList = <Map<String, dynamic>>[];

      // Add history messages
      for (final msg in messages) {
        messagesList.add({
          'role': msg['role'] ?? 'user',
          'content': msg['content'] ?? '',
        });
      }

      // Add current prompt if not already in messages
      if (prompt.isNotEmpty &&
          (messagesList.isEmpty ||
              messagesList.last['content'] != prompt)) {
        messagesList.add({
          'role': 'user',
          'content': prompt,
        });
      }

      final body = {
        'model': modelId,
        'messages': messagesList,
        'stream': true,
        'temperature': 0.7,
        'max_tokens': 2048,
      };

      final request = http.Request('POST', url);
      request.headers.addAll({
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${config.apiKey}',
        'Accept': 'text/event-stream',
      });
      request.body = jsonEncode(body);

      final streamedResponse = await request.send();

      if (streamedResponse.statusCode != 200) {
        final body = await streamedResponse.stream.bytesToString();
        throw Exception(
          'API request failed with status: ${streamedResponse.statusCode}. Response: $body',
        );
      }

      return streamedResponse.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .where((line) => line.isNotEmpty && line.startsWith('data: '))
          .map((line) => line.substring(6)) // Remove 'data: ' prefix
          .where((data) => data != '[DONE]')
          .map((data) {
            try {
              final json = jsonDecode(data);
              final content = json['choices']?[0]?['delta']?['content'];
              return content ?? '';
            } catch (e) {
              return '';
            }
          })
          .where((content) => content.isNotEmpty)
          .cast<String>();
    } catch (e) {
      throw Exception('Failed to send message: $e');
    }
  }

  /// Private: Send synchronous text request (for generating titles, etc.)
  static Future<String> _sendTextRequest({
    required ProviderConfig config,
    required String modelId,
    required String prompt,
  }) async {
    try {
      final baseUrl = _getBaseUrl(config);

      if (baseUrl.isEmpty) {
        throw Exception('API URL is not configured. Please set the API URL in your config or Gist.');
      }

      final chatPath = (config.chatPath ?? '').startsWith('/')
          ? config.chatPath ?? ''
          : '/${config.chatPath ?? ''}';

      final url = Uri.parse('$baseUrl$chatPath');

      final body = {
        'model': modelId,
        'messages': [
          {
            'role': 'user',
            'content': prompt,
          },
        ],
        'stream': false,
        'temperature': 0.7,
        'max_tokens': 256,
      };

      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ${config.apiKey}',
        },
        body: jsonEncode(body),
      );

      if (response.statusCode != 200) {
        throw Exception(
          'API request failed with status: ${response.statusCode}. Response: ${response.body}',
        );
      }

      final json = jsonDecode(response.body);
      final content = json['choices']?[0]?['message']?['content'];
      return content ?? '';
    } catch (e) {
      throw Exception('Failed to generate text: $e');
    }
  }
}