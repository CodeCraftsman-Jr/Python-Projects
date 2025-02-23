# Advanced Directory Categorizer V8

A powerful GUI application that uses multiple AI models to intelligently categorize plugins and files.

## Features

- **Multi-Model Support**: Uses Gemini, OpenAI, Cohere, and Anthropic APIs for better accuracy
- **Smart Rate Limiting**: Intelligent handling of API rate limits and quotas
- **Modern UI**: Dark/Light theme support with a clean, intuitive interface
- **Advanced Caching**: Smart caching system to reduce API calls
- **Error Handling**: Robust error handling with retries and fallbacks
- **Progress Tracking**: Real-time progress updates with detailed statistics
- **API Key Management**: Secure storage and testing of API keys
- **Batch Processing**: Efficient batch processing of files
- **Export/Import**: Save and load categorization results
- **Search Integration**: Fallback to web search for better accuracy
- **Customizable Categories**: Suggest and manage custom categories

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API keys:
   - Create a `.env` file with your API keys (optional)
   - Or enter them directly in the GUI

3. Run the application:
```bash
python plugin_categorizer_gui.py
```

## API Keys

- Gemini API: Get from Google AI Studio
- OpenAI API: Get from OpenAI Platform
- Cohere API: Get from Cohere Dashboard
- Anthropic API: Get from Anthropic Console

## Usage

1. Launch the application
2. Enter your API keys in the Setup tab
3. Select a directory to categorize
4. Choose categorization options
5. Start the process
6. View and export results

## Requirements

- Python 3.8+
- See requirements.txt for package dependencies
