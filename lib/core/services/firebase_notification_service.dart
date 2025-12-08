import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import '../../shared/widgets/snackbar.dart';

class FirebaseNotificationService {
  static final FirebaseNotificationService _instance = FirebaseNotificationService._internal();
  
  factory FirebaseNotificationService() {
    return _instance;
  }
  
  FirebaseNotificationService._internal();

  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  BuildContext? _context;

  Future<void> initialize(BuildContext context) async {
    _context = context;
    
    try {
      // Request notification permission (iOS 13+)
      await _firebaseMessaging.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );

      // Get FCM token
      String? token = await _firebaseMessaging.getToken();
      print('FCM Token: $token');

      // Handle foreground notifications
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        _handleForegroundNotification(message);
      });

      // Handle background notifications when app is resumed from background
      FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
        _handleBackgroundNotification(message);
      });

      // Handle notifications when app is terminated and opened by notification
      RemoteMessage? initialMessage = await _firebaseMessaging.getInitialMessage();
      if (initialMessage != null) {
        _handleBackgroundNotification(initialMessage);
      }

      print('Firebase Notifications initialized successfully');
    } catch (e) {
      print('Error initializing Firebase Notifications: $e');
      if (_context != null) {
        showAppSnackBar(
          _context!,
          message: 'Failed to initialize notifications: ${e.toString()}',
          type: NotificationType.error,
        );
      }
    }
  }

  void _handleForegroundNotification(RemoteMessage message) {
    if (_context == null) return;

    final title = message.notification?.title ?? 'Notification';
    final body = message.notification?.body ?? '';
    final data = message.data;

    // Show snackbar notification
    showAppSnackBar(
      _context!,
      message: '$title: $body',
      type: NotificationType.info,
      duration: const Duration(seconds: 5),
    );

    // Log notification data
    print('Foreground Notification:');
    print('  Title: $title');
    print('  Body: $body');
    print('  Data: $data');

    // Handle custom data
    if (data.isNotEmpty) {
      _handleNotificationData(data);
    }
  }

  void _handleBackgroundNotification(RemoteMessage message) {
    final title = message.notification?.title ?? 'Notification';
    final body = message.notification?.body ?? '';
    final data = message.data;

    print('Background Notification:');
    print('  Title: $title');
    print('  Body: $body');
    print('  Data: $data');

    // Handle custom data
    if (data.isNotEmpty) {
      _handleNotificationData(data);
    }
  }

  void _handleNotificationData(Map<String, dynamic> data) {
    // Handle custom notification actions
    final action = data['action'] as String?;
    
    switch (action) {
      case 'message':
        print('Message notification received: ${data['content']}');
        break;
      case 'alert':
        print('Alert notification received: ${data['alert_content']}');
        break;
      default:
        print('Unknown notification action');
    }
  }

  /// Send test notification (for development/testing)
  Future<void> sendTestNotification({
    required String title,
    required String body,
    Map<String, dynamic>? data,
  }) async {
    try {
      print('Test Notification:');
      print('  Title: $title');
      print('  Body: $body');
      print('  Data: $data');
      
      if (_context != null) {
        showAppSnackBar(
          _context!,
          message: '$title: $body',
          type: NotificationType.success,
          duration: const Duration(seconds: 4),
        );
      }
    } catch (e) {
      print('Error sending test notification: $e');
    }
  }

  /// Get FCM token
  Future<String?> getToken() async {
    try {
      return await _firebaseMessaging.getToken();
    } catch (e) {
      print('Error getting FCM token: $e');
      return null;
    }
  }

  /// Subscribe to a topic
  Future<void> subscribeToTopic(String topic) async {
    try {
      await _firebaseMessaging.subscribeToTopic(topic);
      print('Subscribed to topic: $topic');
      if (_context != null) {
        showAppSnackBar(
          _context!,
          message: 'Subscribed to $topic',
          type: NotificationType.success,
        );
      }
    } catch (e) {
      print('Error subscribing to topic: $e');
      if (_context != null) {
        showAppSnackBar(
          _context!,
          message: 'Failed to subscribe to topic: $e',
          type: NotificationType.error,
        );
      }
    }
  }

  /// Unsubscribe from a topic
  Future<void> unsubscribeFromTopic(String topic) async {
    try {
      await _firebaseMessaging.unsubscribeFromTopic(topic);
      print('Unsubscribed from topic: $topic');
      if (_context != null) {
        showAppSnackBar(
          _context!,
          message: 'Unsubscribed from $topic',
          type: NotificationType.success,
        );
      }
    } catch (e) {
      print('Error unsubscribing from topic: $e');
      if (_context != null) {
        showAppSnackBar(
          _context!,
          message: 'Failed to unsubscribe from topic: $e',
          type: NotificationType.error,
        );
      }
    }
  }
}
