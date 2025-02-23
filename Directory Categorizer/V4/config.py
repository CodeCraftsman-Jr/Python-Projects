# Configuration for Gemini API keys
GEMINI_API_KEYS = [
    "AIzaSyCNidNjYtsouuJtJpme9xUtjiV9QJf5mSc",  # Primary API key
    "AIzaSyDK_rlILDv6fQJm_uHIHYXTBrIjs8rCqYY",  # Secondary API key
    "AIzaSyCSU8nAd_ZnT39cBtbAoJibDV-6G6x3nG8",  # Third API key
    "AIzaSyB1KdgZ1vJ00m6ZZN0lj-LsoFnjInCeMCU",  # Fourth API key
    "AIzaSyBNFAmqazVDGZ_g293oRWKQGbsTkCBRTZk"   # Fifth API key
]

# API endpoint
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent'

# Rate limiting settings (per API key)
REQUESTS_PER_MINUTE = 10  # Conservative limit per API key
BATCH_SIZE = 5  # Number of plugins to process in parallel per batch
