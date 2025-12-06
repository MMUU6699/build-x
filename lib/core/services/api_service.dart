import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String get apiUrl => dotenv.env['API_URL'] ?? 'http://localhost:8000';
  String get modelName => dotenv.env['MODEL_NAME'] ?? 'Build X';

  Future<Stream<String>> sendMessage(String message, List<Map<String, dynamic>> history) async {
    try {
      final url = Uri.parse('$apiUrl/v1/chat/completions');
      
      // Prepare messages for the API
      List<Map<String, dynamic>> messages = [];
      
      // Add history
      for (var msg in history) {
        messages.add({
          'role': msg['role'] ?? 'user',
          'content': msg['content'] ?? '',
        });
      }
      
      // Add current message
      messages.add({
        'role': 'user',
        'content': message,
      });

      final body = {
        'model': modelName,
        'messages': messages,
        'stream': true,
        'temperature': 0.7,
        'max_tokens': 2048,
      };

      final request = http.Request('POST', url);
      request.headers.addAll({
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      });
      request.body = jsonEncode(body);

      final streamedResponse = await request.send();
      
      if (streamedResponse.statusCode != 200) {
        throw Exception('API request failed with status: ${streamedResponse.statusCode}');
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
          .where((content) => content.isNotEmpty).cast<String>();
          
    } catch (e) {
      throw Exception('Failed to send message: $e');
    }
  }

  Future<String> sendMessageSync(String message, List<Map<String, dynamic>> history) async {
    try {
      final url = Uri.parse('$apiUrl/v1/chat/completions');
      
      // Prepare messages for the API
      List<Map<String, dynamic>> messages = [];
      
      // Add history
      for (var msg in history) {
        messages.add({
          'role': msg['role'] ?? 'user',
          'content': msg['content'] ?? '',
        });
      }
      
      // Add current message
      messages.add({
        'role': 'user',
        'content': message,
      });

      final body = {
        'model': modelName,
        'messages': messages,
        'stream': false,
        'temperature': 0.7,
        'max_tokens': 2048,
      };

      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode(body),
      );

      if (response.statusCode != 200) {
        throw Exception('API request failed with status: ${response.statusCode}');
      }

      final json = jsonDecode(response.body);
      final content = json['choices']?[0]?['message']?['content'];
      return content ?? '';
      
    } catch (e) {
      throw Exception('Failed to send message: $e');
    }
  }

  Future<bool> testConnection() async {
    try {
      final url = Uri.parse('$apiUrl/v1/models');
      final response = await http.get(url);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}