import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration for Gemini API keys
GEMINI_API_KEYS = ['AIzaSyCSU8nAd_ZnT39cBtbAoJibDV-6G6x3nG8', 'AIzaSyDK_rlILDv6fQJm_uHIHYXTBrIjs8rCqYY']
    os.getenv("GEMINI_API_KEY_1", "AIzaSyCSU8nAd_ZnT39cBtbAoJibDV-6G6x3nG8"),  # Primary API key
    os.getenv("GEMINI_API_KEY_2", "AIzaSyDK_rlILDv6fQJm_uHIHYXTBrIjs8rCqYY"),  # Secondary API key
]

# Gemini API endpoint
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent'

# OpenAI Configuration
OPENAI_API_KEY = "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"

# Cohere Configuration
COHERE_API_KEY = "Th4MejtA1766eLR03SUkod20LgvkZ5KA5VEGsidJ"

# Anthropic Configuration
ANTHROPIC_API_KEY = "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"

# Rate limiting settings
RATE_LIMIT_SETTINGS = {
    'gemini': {
        'requests_per_minute': 10,
        'batch_size': 5,
        'retry_delay': 1.0,
        'max_retries': 3
    },
    'openai': {
        'requests_per_minute': 10,
        'batch_size': 5,
        'retry_delay': 1.0,
        'max_retries': 3
    },
    'cohere': {
        'requests_per_minute': 10,
        'batch_size': 5,
        'retry_delay': 1.0,
        'max_retries': 3
    },
    'anthropic': {
        'requests_per_minute': 10,
        'batch_size': 5,
        'retry_delay': 1.0,
        'max_retries': 3
    }
}

# Model settings
MODEL_SETTINGS = {
    'openai': {
        'model': 'gpt-3.5-turbo',
        'temperature': 0.3,
        'max_tokens': 150
    },
    'anthropic': {
        'model': 'claude-2',
        'temperature': 0.3,
        'max_tokens': 150
    },
    'cohere': {
        'model': 'command',
        'temperature': 0.3,
        'max_tokens': 150
    },
    'gemini': {
        'model': 'gemini-pro',
        'temperature': 0.3,
        'max_tokens': 150
    }
}

# UI Theme settings
THEME_SETTINGS = {
    'light': {
        'bg': '#ffffff',
        'fg': '#000000',
        'button_bg': '#e1e1e1',
        'button_fg': '#000000',
        'highlight_bg': '#0078d7',
        'highlight_fg': '#ffffff'
    },
    'dark': {
        'bg': '#2d2d2d',
        'fg': '#ffffff',
        'button_bg': '#3d3d3d',
        'button_fg': '#ffffff',
        'highlight_bg': '#0078d7',
        'highlight_fg': '#ffffff'
    }
}

# Logging settings
LOG_SETTINGS = {
    'filename': 'plugin_categorizer.log',
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    'max_size': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5
}

# Cache settings
CACHE_SETTINGS = {
    'enabled': True,
    'directory': '.cache',
    'max_size': 100 * 1024 * 1024,  # 100 MB
    'expiry': 24 * 60 * 60  # 24 hours
}

# Plugin categorization settings
CATEGORIZATION_SETTINGS = {
    'min_confidence': 0.7,
    'default_category': 'Uncategorized',
    'fallback_to_search': True,
    'search_results_count': 5,
    'category_suggestions': [
        'E-commerce', 'SEO', 'Security', 'Performance',
        'Social Media', 'Content Management', 'Forms',
        'Analytics', 'Backup', 'Media', 'Marketing',
        'User Management', 'Development Tools'
    ]
}

# Error handling settings
ERROR_SETTINGS = {
    'max_retries': 3,
    'retry_delay': 1.0,
    'exponential_backoff': True,
    'notify_on_error': True
}
