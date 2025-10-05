# Gemini API Configuration
# Get your API key from: https://makersuite.google.com/app/apikey

apikey = "AIzaSyDR9d0lfB1hKDfS9ye4OY6XbkgjNPbI3-c"

# Server Configuration
HOST = "localhost"
PORT = 8765

# WebSocket Configuration
PING_INTERVAL = 20  # seconds
PING_TIMEOUT = 10   # seconds

# Gemini Model Configuration
MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.7
TOP_P = 0.95
TOP_K = 40
MAX_OUTPUT_TOKENS = 1024

# Debug mode
DEBUG = True

print("Configuration loaded successfully")