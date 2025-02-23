# Configuration for Gemini API keys
GEMINI_API_KEYS = [
    "AIzaSyCSU8nAd_ZnT39cBtbAoJibDV-6G6x3nG8",  # Primary API key
    "AIzaSyDK_rlILDv6fQJm_uHIHYXTBrIjs8rCqYY",  # Secondary API key (optional)
]

# Gemini API endpoint
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent'

# OpenAI Configuration
OPENAI_API_KEY = "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"  # Get from https://platform.openai.com/api-keys

# Cohere Configuration
COHERE_API_KEY = "Th4MejtA1766eLR03SUkod20LgvkZ5KA5VEGsidJ"  # Get from https://dashboard.cohere.ai/api-keys

# Anthropic Configuration
ANTHROPIC_API_KEY = "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"  # Get from https://console.anthropic.com/

# Rate limiting settings (per API key)
REQUESTS_PER_MINUTE = 5  # More conservative limit
BATCH_SIZE = 3  # Smaller batch size
REQUEST_TIMEOUT = 10  # Timeout in seconds

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # Base delay in seconds
MAX_RETRY_DELAY = 30  # Maximum delay in seconds

# Model settings
OPENAI_MODEL = "gpt-3.5-turbo"  # or "gpt-4" if you have access
ANTHROPIC_MODEL = "claude-3-haiku-20240307"  # Latest Claude model
COHERE_MODEL = "command"         # or other available Cohere models
