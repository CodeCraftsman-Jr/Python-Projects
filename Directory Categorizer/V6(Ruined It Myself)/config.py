# Configuration for Gemini API keys
GEMINI_API_KEYS = [
    "AIzaSyBNFAmqazVDGZ_g293oRWKQGbsTkCBRTZk",  # Primary API key
    "AIzaSyBNFAmqazVDGZ_g293oRWKQGbsTkCBRTZk",  # Secondary API key (optional)
]

# Gemini API endpoint
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent'

# OpenAI Configuration
OPENAI_API_KEY = "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"  # Get from https://platform.openai.com/api-keys

# Cohere Configuration
COHERE_API_KEY = "jQj31ihfIePM1rW5ast1kaOvTeggnjDDbRMCujxF"  # Get from https://dashboard.cohere.ai/api-keys

# Anthropic Configuration
ANTHROPIC_API_KEY = "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"  # Get from https://console.anthropic.com/

# Rate limiting settings (per API key)
REQUESTS_PER_MINUTE = 10  # Conservative limit per API key
BATCH_SIZE = 5  # Number of plugins to process in parallel per batch

# Model settings
OPENAI_MODEL = "gpt-3.5-turbo"  # or "gpt-4" if you have access
ANTHROPIC_MODEL = "claude-2"     # or other available Claude models
COHERE_MODEL = "command"         # or other available Cohere models
