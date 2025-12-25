
"""
Simple greeting tool for testing
"""


def hello(message: str = "world") -> dict:
    """
    Respond to greetings
    
    Args:
        message: Message to respond to
    
    Returns:
        dict: Greeting response
    """
    # Simple greeting responses
    greetings = {
        "こんにちは": "こんにちは！元気ですか？ 😊",
        "こんにちわ": "こんにちは！元気ですか？ 😊",
        "hello": "Hello! How can I help you today? 👋",
        "hi": "Hi there! 👋",
        "おはよう": "おはようございます！ ☀️",
        "こんばんは": "こんばんは！ 🌙",
    }
    
    # Check if message matches any greeting
    msg_lower = message.lower().strip()
    for key, response in greetings.items():
        if key in msg_lower:
            return {"message": response, "input": message}
    
    # Default response
    return {
        "message": f"Hello, {message}! 👋",
        "input": message
    }
