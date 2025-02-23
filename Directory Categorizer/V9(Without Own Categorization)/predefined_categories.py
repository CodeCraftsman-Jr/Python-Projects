"""Predefined categories for WordPress plugin categorization."""

PREDEFINED_CATEGORIES = {
    # Core categories from WordPress plugin directory
    "3D": ["3d model", "3d viewer", "three dimensional"],
    "ACCESSIBILITY": ["screen reader", "aria", "wcag", "disability"],
    "ADMIN_TOOLS": ["admin", "dashboard", "management"],
    "ANALYTICS": ["statistics", "tracking", "metrics", "google analytics"],
    "API_INTEGRATION": ["api", "integration", "connect", "webhook"],
    "AUTHENTICATION": ["login", "register", "user auth", "oauth"],
    "BACKUP": ["backup", "restore", "export", "clone"],
    "BLOGGING": ["blog", "post", "author", "writing"],
    "BOOKING": ["appointment", "reservation", "schedule", "calendar"],
    "CACHING": ["cache", "speed", "performance", "optimization"],
    "CALENDAR": ["events", "schedule", "dates", "booking"],
    "CHAT": ["messaging", "live chat", "support", "communication"],
    "COMMENTS": ["discussion", "replies", "conversation", "moderation"],
    "CONTACT_FORMS": ["form", "contact", "feedback", "input"],
    "CONTENT_MANAGEMENT": ["cms", "content", "posts", "pages"],
    "CUSTOMIZATION": ["custom", "modify", "personalize", "theme"],
    "DATABASE": ["db", "mysql", "queries", "data"],
    "DEVELOPMENT": ["debug", "code", "developer", "programming"],
    "DOCUMENTATION": ["docs", "help", "manual", "guide"],
    "E_COMMERCE": ["shop", "store", "payment", "products"],
    "EDITOR": ["text editor", "visual editor", "wysiwyg", "gutenberg"],
    "EMAIL": ["mail", "newsletter", "subscription", "smtp"],
    "EVENTS": ["calendar", "booking", "schedule", "registration"],
    "FORMS": ["contact", "input", "survey", "questionnaire"],
    "GALLERY": ["images", "photos", "portfolio", "media"],
    "GDPR": ["privacy", "compliance", "cookie", "consent"],
    "IMAGES": ["photo", "gallery", "media", "picture"],
    "LANGUAGE": ["translation", "multilingual", "localization", "i18n"],
    "MARKETING": ["seo", "social media", "analytics", "advertising"],
    "MEDIA": ["video", "audio", "image", "gallery"],
    "MEMBERSHIP": ["users", "subscription", "access", "roles"],
    "MENU": ["navigation", "header", "footer", "links"],
    "MIGRATION": ["import", "export", "transfer", "move"],
    "MOBILE": ["responsive", "app", "phone", "tablet"],
    "MONITORING": ["uptime", "security", "logs", "tracking"],
    "NEWSLETTER": ["email", "subscription", "mailing list", "campaign"],
    "OPTIMIZATION": ["speed", "performance", "cache", "compress"],
    "PAGE_BUILDER": ["layout", "design", "blocks", "templates"],
    "PAYMENT": ["gateway", "checkout", "transaction", "ecommerce"],
    "PERFORMANCE": ["speed", "optimization", "cache", "compress"],
    "POPUP": ["modal", "overlay", "lightbox", "notification"],
    "SECURITY": ["protection", "firewall", "antispam", "backup"],
    "SEO": ["search engine", "meta", "sitemap", "keywords"],
    "SHIPPING": ["delivery", "tracking", "orders", "ecommerce"],
    "SLIDER": ["carousel", "gallery", "slideshow", "banner"],
    "SOCIAL_MEDIA": ["share", "facebook", "twitter", "instagram"],
    "SPAM": ["protection", "antispam", "security", "filter"],
    "SUPPORT": ["help desk", "ticket", "chat", "customer service"],
    "THEME": ["design", "layout", "template", "style"],
    "USER_MANAGEMENT": ["profile", "registration", "roles", "access"],
    "VIDEO": ["player", "streaming", "embed", "media"],
    "WIDGETS": ["sidebar", "footer", "content", "display"],
    "WOO_COMMERCE": ["shop", "store", "ecommerce", "products"]
}

def find_matching_category(plugin_name: str, description: str = "") -> str:
    """
    Find a matching category from predefined categories based on plugin name and description.
    
    Args:
        plugin_name (str): Name of the plugin
        description (str): Optional plugin description
    
    Returns:
        str: Matching category name or empty string if no match found
    """
    search_text = (plugin_name + " " + description).lower()
    
    for category, keywords in PREDEFINED_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in search_text:
                return category.replace("_", " ").title()
    
    return ""
