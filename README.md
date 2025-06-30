# Unified Tag Extraction API

This API combines Mezink API data fetching and Gemini AI tag extraction into a single endpoint.

## Features

- Fetches bio and captions from Mezink API using username and platform
- Processes content through Gemini AI for language detection and content style classification
- Returns structured tags without storing intermediate data
- Batch processing support for Google Sheets integration

## Setup

### Environment Variables

Set these in your Railway environment:

```
NEW_API_KEY=your_gemini_api_key_here
MEZINK_EMAIL=mezink_mail_here
MEZINK_PASSWORD=your_mezink_password_here
```

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Set the environment variable `NEW_API_KEY`
3. Deploy using the Dockerfile

### Google Sheets Setup

1. Your sheet should have these columns:
   - `username` - The social media username
   - `platform` - The platform (instagram, youtube, tiktok, etc.)

2. The API will automatically create these output columns:
   - `detected_languages` - Array of detected languages and regions
   - `is_multilingual` - Boolean indicating multilingual content
   - `content_style` - Array of content categories
   - `processed_at` - Timestamp of processing
   - `error` - Any error messages

3. Copy the `updated_tag_appscript.js` code to Google Apps Script
4. Update the endpoint URL in the script to your Railway app URL
5. Run the script to process your data

## API Endpoints

### POST /process

Process username/platform pairs and return tags.

**Request:**
```json
{
  "rows": [
    {
      "username": "example_user",
      "platform": "instagram"
    }
  ]
}
```

**Response:**
```json
[
  {
    "detected_languages": ["English", "Indonesia"],
    "is_multilingual": false,
    "content_style": ["Fashion", "Lifestyle"],
    "processed_at": "2024-01-01T12:00:00",
    "error": ""
  }
]
```

### GET /health

Health check endpoint.

## Supported Platforms

- instagram/ig
- youtube/yt
- tiktok/tt
- facebook/fb
- twitter/x
- linkedin

## Content Style Categories

- Fashion
- Lifestyle
- Travel
- Beauty
- Health & Wellness
- Parenting & Kids
- Food
- Finance
- Business
- Sports
- Fitness
- Entrepreneurship
- Home Appliances
- DIY & Crafts
- Education & Learning
- Tech & Gadgets
- Entertainment
- Personal 