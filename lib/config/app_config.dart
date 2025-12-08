/// Configuration for Build X AI Model
/// 
/// This file manages the API endpoint for the local AI model.
/// Update API_URL in .env file to change the model endpoint.

import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  /// Get the API URL from .env file
  static String get apiUrl {
    final url = dotenv.env['API_URL'] ?? 'https://premiere-geographic-telling-call.trycloudflare.com';
    return url;
  }

  /// Get the model name
  static String get modelName {
    return dotenv.env['MODEL_NAME'] ?? 'Build X';
  }

  /// Complete model endpoint for API calls
  static String get modelEndpoint {
    return '$apiUrl/v1/chat/completions';
  }
}
