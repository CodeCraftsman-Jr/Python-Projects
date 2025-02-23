import os
import logging
from dotenv import load_dotenv
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from difflib import get_close_matches

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Add debug logging
logger.debug(f"Environment variables loaded. GEMINI_API_KEY present: {bool(os.getenv('GEMINI_API_KEY'))}")

# Configure the Gemini API (Placeholder API endpoint and key)
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Get API key from environment variable
if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")

# Define the source and destination directories
source_dir = r'C:\Users\evasa\Documents\WP_PLUGINS\Utilities'  # Change this to your source directory
dest_dir = r'C:\Users\evasa\Documents\WP_PLUGINS'  # Change this to your destination directory

# Define the maximum categories you want to use
MAX_CATEGORIES = 25  # Change this to 25
MAX_TOTAL_CATEGORIES = 50

# Define the predefined categories
PREDEFINED_CATEGORIES = [
    # SEO and Marketing
    "SEO", "Local SEO", "SEO Tools", "Marketing Automation", "Email Marketing",
    "Social Media Marketing", "Content Marketing", "Analytics", "Conversion Tools",
    "Advertisement Management",
    
    # Security and Protection
    "Security", "Firewall", "Anti-Spam", "Malware Protection", "Access Control",
    "Authentication", "SSL Management", "Privacy Tools", "Backup", "Data Security",
    
    # Performance and Optimization
    "Performance", "Caching", "Image Optimization", "Database Optimization",
    "Minification", "CDN Integration", "Speed Optimization", "Resource Management",
    "Lazy Loading", "Server Optimization",
    
    # E-commerce and Payments
    "E-commerce", "Payment Gateways", "Shopping Cart", "Product Management",
    "Order Management", "Shipping", "Inventory Management", "Digital Downloads",
    "Subscriptions", "Multi-vendor Marketplace",
    
    # Content and Media
    "Content Management", "Media Library", "File Management", "Image Gallery",
    "Video Management", "Audio Management", "Document Management", "PDF Tools",
    "Content Editor", "Version Control",
    
    # User Management
    "User Management", "Membership", "User Roles", "User Profiles",
    "Registration Forms", "Login Management", "User Authentication",
    "Community Management", "User Directory", "Access Management",
    
    # Design and Customization
    "Theme Customization", "Page Builders", "Custom CSS", "Layout Management",
    "Typography", "Color Management", "Widget Management", "Menu Management",
    "Design Tools", "Responsive Design",
    
    # Forms and Interaction
    "Forms", "Contact Forms", "Survey Tools", "Polls", "Feedback Management",
    "Quiz Tools", "Booking Systems", "Appointment Scheduling", "Event Management",
    "Calendar Management",
    
    # Integration and Development
    "API Integration", "Developer Tools", "Custom Code", "Database Tools",
    "Migration Tools", "Testing Tools", "Debugging", "Compatibility", 
    "Multilingual Tools", "Code Snippets"
]

# Track created categories
created_categories = set()

# Add a function to test network connectivity
def test_network_connection():
    try:
        response = requests.get('https://www.google.com', timeout=5)
        logger.info(f"Network connection test successful. Status code: {response.status_code}")
        return True
    except requests.RequestException as e:
        logger.error(f"Network connection test failed: {e}")
        return False

# Add a function to get existing categories
def get_existing_categories():
    """Get list of existing category directories."""
    return [d for d in os.listdir(dest_dir) 
            if os.path.isdir(os.path.join(dest_dir, d)) and d != "Error"]

def find_similar_category(plugin_name, category_name):
    """Find the most similar existing category based on name matching."""
    existing_cats = list(created_categories)
    # Add predefined categories if they're not already in existing categories
    all_categories = list(set(existing_cats + PREDEFINED_CATEGORIES))
    
    # Try to find matches based on the suggested category name
    matches = get_close_matches(category_name, all_categories, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    
    # If no match found based on category, try matching based on plugin name
    # This helps when the plugin name contains category hints (e.g., "seo-master" → "SEO")
    matches = get_close_matches(plugin_name, all_categories, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    
    # If still no match, return a general category based on plugin name analysis
    common_categories = {
        'form': 'Forms',
        'security': 'Security',
        'seo': 'SEO',
        'backup': 'Backup',
        'cache': 'Performance',
        'analytics': 'Analytics',
        'social': 'Social Media',
        'payment': 'E-commerce',
        'woo': 'E-commerce',
        'shop': 'E-commerce',
        'user': 'User Management',
        'admin': 'Admin Tools',
        'media': 'Media Management',
        'email': 'Email Marketing',
        'custom': 'Customization'
    }
    
    plugin_name_lower = plugin_name.lower()
    for keyword, category in common_categories.items():
        if keyword in plugin_name_lower:
            return category
    
    # If nothing else matches, use "Utilities" as a last resort
    return "Utilities"

# Modify the existing function to include more robust error handling
@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),  # Start with 4s delay, exponentially increase up to 60s
    stop=stop_after_attempt(5)  # Maximum 5 attempts
)
def get_plugin_category_from_gemini(plugin_name):
    """Get plugin category using Gemini API with retry logic for rate limits."""
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': GEMINI_API_KEY
        }
        
        prompt = f"""Analyze this WordPress plugin name: '{plugin_name}'
        Suggest a single, specific category that best describes its primary function.
        Choose from these categories or suggest a similar one:
        {', '.join(PREDEFINED_CATEGORIES)}
        Respond with ONLY the category name, nothing else."""

        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }

        response = requests.post(GEMINI_API_URL, headers=headers, json=data)
        
        if response.status_code == 429:
            logger.warning("Rate limit hit, retrying with backoff...")
            raise requests.exceptions.RequestException("Rate limit exceeded")
            
        response.raise_for_status()
        
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            category = result['candidates'][0]['content']['parts'][0]['text'].strip()
            logger.info(f"Successfully categorized '{plugin_name}' as '{category}'")
            return category
        else:
            logger.warning(f"Unexpected API response format for {plugin_name}")
            return find_similar_category(plugin_name, "")
            
    except Exception as e:
        logger.error(f"Error getting category from Gemini for '{plugin_name}': {str(e)}")
        return find_similar_category(plugin_name, "")

def categorize_plugin(categories):
    global created_categories
    
    # Get current existing categories
    existing_cats = get_existing_categories()
    created_categories.update(existing_cats)
    
    # Convert input categories to lowercase for case-insensitive matching
    input_categories = [cat.lower() for cat in categories]
    
    # First try to match with predefined categories
    matched_categories = [category for category in PREDEFINED_CATEGORIES 
                        if category.lower() in input_categories]
    
    if not matched_categories:
        # If no predefined match, check if we can create a new category
        new_category = categories[0].strip()
        new_category = ' '.join(word.capitalize() for word in new_category.split())
        
        # Check if we're at the category limit
        if new_category not in created_categories:
            if len(created_categories) >= MAX_TOTAL_CATEGORIES:
                # Find the most similar existing category
                similar_category = find_similar_category(new_category, new_category)
                logger.info(f"Category limit reached. Using similar category: {similar_category}")
                new_category = similar_category
            else:
                created_categories.add(new_category)
        
        matched_categories = [new_category]
    
    return matched_categories[:MAX_CATEGORIES]

def move_plugin(folder):
    folder_path = os.path.join(source_dir, folder)
    if os.path.isdir(folder_path):
        try:
            # Fetch the category from Gemini
            suggested_category = get_plugin_category_from_gemini(folder)
            categories = [suggested_category]
            
            # Get up to MAX_CATEGORIES categories
            matched_categories = categorize_plugin(categories)
            
            for category in matched_categories:
                # Create the destination category folder if it doesn't exist
                category_folder = os.path.join(dest_dir, category)
                os.makedirs(category_folder, exist_ok=True)
                
                # Create the full destination path
                dest_path = os.path.join(category_folder, folder)
                
                # Check if destination already exists
                if os.path.exists(dest_path):
                    logger.warning(f"Destination path already exists for {folder} in {category}. Adding timestamp.")
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    folder_name = f"{folder}_{timestamp}"
                    dest_path = os.path.join(category_folder, folder_name)
                
                # Move the folder to the appropriate category folder
                shutil.move(folder_path, dest_path)
                logger.info(f'Moved {folder} to {category} ({dest_path})')
                break  # Move to the first matched category
                
        except Exception as e:
            logger.error(f"Failed to move plugin {folder}: {str(e)}")
            # Create an 'Error' category for failed moves
            error_folder = os.path.join(dest_dir, "Error")
            os.makedirs(error_folder, exist_ok=True)
            error_dest = os.path.join(error_folder, folder)
            if not os.path.exists(error_dest):
                shutil.move(folder_path, error_folder)
                logger.info(f'Moved {folder} to Error category due to processing failure')

def process_plugins_with_rate_limiting():
    """Process plugins in batches with rate limiting."""
    # Initialize by getting existing categories
    existing_cats = get_existing_categories()
    created_categories.update(existing_cats)
    
    logger.info(f"Starting with {len(created_categories)} existing categories")
    
    folders = os.listdir(source_dir)
    batch_size = 8  # Process 8 plugins per minute (staying under 10 QPM limit)
    delay_between_requests = 8  # 8 seconds between batches
    
    for i in range(0, len(folders), batch_size):
        batch = folders[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} of {(len(folders) + batch_size - 1)//batch_size}")
        logger.info(f"Current number of categories: {len(created_categories)}/{MAX_TOTAL_CATEGORIES}")
        
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {executor.submit(move_plugin, folder): folder for folder in batch}
            for future in as_completed(futures):
                folder = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error processing {folder}: {str(e)}")
        
        if i + batch_size < len(folders):
            logger.info(f"Waiting {delay_between_requests} seconds before next batch...")
            time.sleep(delay_between_requests)

if __name__ == "__main__":
    process_plugins_with_rate_limiting()
    print("Plugins have been categorized and moved successfully!")