class ChatStreamChunk {
  final String? content;
  final bool isFinished;
  final String? error;
  final String? reasoning;
  final List<dynamic>? toolCalls;
  final List<dynamic>? toolResults;
  final bool isDone;
  final int totalTokens;
  final TokenUsage? usage;

  ChatStreamChunk({
    this.content,
    this.isFinished = false,
    this.error,
    this.reasoning,
    this.toolCalls,
    this.toolResults,
    this.isDone = false,
    this.totalTokens = 0,
    this.usage,
  });
}

class TokenUsage {
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
  
  const TokenUsage({
    this.promptTokens = 0,
    this.completionTokens = 0,
    this.totalTokens = 0,
  });
  
  TokenUsage merge(TokenUsage other) {
    return TokenUsage(
      promptTokens: promptTokens + other.promptTokens,
      completionTokens: completionTokens + other.completionTokens,
      totalTokens: totalTokens + other.totalTokens,
    );
  }
}