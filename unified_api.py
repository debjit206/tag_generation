import json
import os
import time
from datetime import datetime, timezone
import base64

import emoji
import google.generativeai as genai
import pandas as pd
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- CONFIGURATION ---
API_URL = 'https://api.cloudsuper.link/sosmed/v1/analytics'
LOGIN_URL = 'https://api.cloudsuper.link/usr/v1/login'
EMAIL = os.environ['MEZINK_EMAIL']
PASSWORD = os.environ['MEZINK_PASSWORD']

# Gemini API key
genai.configure(api_key=os.environ.get("NEW_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Map Excel platform values to API mediaType values
PLATFORM_MAP = {
    'instagram': 'INSTAGRAM',
    'ig': 'INSTAGRAM',
    'youtube': 'YOUTUBE',
    'yt': 'YOUTUBE',
    'tiktok': 'TIKTOK',
    'tt': 'TIKTOK',
    'facebook': 'FACEBOOK',
    'fb': 'FACEBOOK',
    'twitter': 'TWITTER',
    'x': 'TWITTER',
    'linkedin': 'LINKEDIN'
}

def get_auth_token():
    """Get authentication token from Mezink API"""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    login_headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "timestamp": timestamp
    }
    encoded_password = base64.b64encode(PASSWORD.encode()).decode()
    login_payload = {
        "email": EMAIL,
        "password": encoded_password,
        "provider": "",
        "token": ""
    }
    try:
        login_response = requests.post(LOGIN_URL, headers=login_headers, json=login_payload)
        if login_response.status_code == 200:
            response_data = login_response.json()
            token = response_data.get("data", {}).get("token", "")
            if token:
                print("✅ Login successful!")
                return token
        print("❌ Login failed")
        return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def fetch_api_data(username, platform, token):
    """Fetch bio and captions from Mezink API"""
    media_type = PLATFORM_MAP.get(platform.lower().strip(), platform.upper().strip())
    params = {
        'username': username,
        'mediaType': media_type
    }
    headers = {
        'Authorization': f'Bearer {token}'
    }
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API error for {username} ({media_type}): {response.status_code}")
            return None
    except Exception as e:
        print(f"Request error for {username} ({media_type}): {e}")
        return None

def extract_bio_and_captions(api_data):
    """Extract bio and captions from API response"""
    bio = ''
    captions = [''] * 6
    if not api_data or 'data' not in api_data:
        return bio, captions
    data = api_data['data']
    # Description (bio)
    if 'metaData' in data and 'description' in data['metaData']:
        bio = data['metaData']['description']
    # Captions: get up to 6 from topEngagementPost
    if 'metaData' in data and 'topEngagementPost' in data['metaData']:
        posts = data['metaData']['topEngagementPost']
        if isinstance(posts, list) and posts:
            for i, post in enumerate(posts[:6]):
                captions[i] = post.get('caption', '')
    return bio, captions

def sanitize_text(text: str, max_length=600) -> str:
    """Clean text, retain emojis, and truncate to safe length."""
    text = str(text).replace('\n', ' ').strip()
    return text[:max_length]

def create_prompt(bio, post1, post2, post3, post4, post5, post6):
    return f"""
You are a multilingual content analyst. Your only task is to detect:

1. The primary language(s) used in the Instagram bio and post captions.
2. Whether there is multilingual content (e.g., English-Hindi).
3. The content style(s) based on the captions and bio. Use only the allowed categories listed below. You may select multiple if applicable.
4. If any emoji, text, or mention suggests a country or location (e.g., 🇮🇩, 🇲🇾, KL, Dubai), include that as part of the detected_languages array.

Allowed content style categories:
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

Examples:
- A pregnancy announcement should fall under "Parenting & Kids"
- A skincare routine post goes under "Beauty" and possibly "Health & Wellness"
- Avoid niche labels like "pregnancy update" — map them to the closest valid category
- If unsure, choose the most relevant category
- If a caption includes 🇮🇩 or "Jakarta", add "Indonesia" to the language list

INPUT DATA:
Bio: {bio}
Post 1: {post1}
Post 2: {post2}
Post 3: {post3}
Post 4: {post4}
Post 5: {post5}
Post 6: {post6}

IMPORTANT:
- Do not make assumptions beyond what's written.
- Translate content if needed, but return output in English.
- Output must be a valid JSON object in the format below. No explanation.
- Include that as part of the detected_languages array
- Include that (e.g., nationality or country) as an additional entry in the detected_languages array

OUTPUT FORMAT:
{{
  "detected_languages": ["language1", "language2", "country_or_region_if_any1", "country_or_region_if_any2"],
  "is_multilingual": true/false,
  "content_style": ["chosen_category1", "chosen_category2_if_any"]
}}
"""

def gemini_generate(prompt):
    """Generate tags using Gemini API"""
    try:
        if len(prompt) > 5000:
            return json.dumps({"error": "Prompt too long. Skipped to avoid failure."})
        response = model.generate_content(prompt)
        if (not response or not response.candidates
                or not response.candidates[0].content.parts):
            return ""

        text = response.candidates[0].content.parts[0].text.strip()

        if text.startswith("```json"):
            text = text[7:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        return text
    except Exception as e:
        return json.dumps({"error": f"Gemini error: {str(e)}"})

@app.route('/process', methods=['POST'])
def process_rows():
    """Main endpoint that processes username/platform pairs and returns tags"""
    try:
        data = request.get_json()
        rows = data.get("rows", [])
        results = []

        # Get auth token once for all requests
        token = get_auth_token()
        if not token:
            return jsonify({"error": "Failed to authenticate with Mezink API"}), 500

        for row in rows:
            username = str(row.get('username', '')).strip()
            platform = str(row.get('platform', '')).strip()
            
            # Only use post1_caption to post6_caption for Gemini
            bio = row.get('bio', '').strip()
            # Fallback: if post1_caption is missing but caption exists, use caption
            post1_caption = row.get('post1_caption', '').strip()
            if not post1_caption:
                post1_caption = row.get('caption', '').strip()
            captions = [post1_caption] + [row.get(f'post{i}_caption', '').strip() for i in range(2, 7)]
            has_sheet_data = bool(bio or any(captions))

            if not has_sheet_data:
                api_data = fetch_api_data(username, platform, token)
                bio, captions = extract_bio_and_captions(api_data)

            bio_clean = sanitize_text(bio)
            captions_clean = [sanitize_text(caption) for caption in captions]

            prompt = create_prompt(bio_clean, *captions_clean)
            print("🤖 Prompt to Gemini:\n", prompt)

            if not bio_clean and all(not c for c in captions_clean):
                results.append({
                    "detected_languages": [],
                    "is_multilingual": False,
                    "content_style": [],
                    "processed_at": datetime.now().isoformat(),
                    "error": "No bio or captions found for this user/platform."
                })
                continue

            raw_response = gemini_generate(prompt)
            print("🔁 Gemini raw response:\n", raw_response)

            try:
                parsed = json.loads(raw_response.strip())
                parsed["processed_at"] = datetime.now().isoformat()
                parsed["error"] = ""
                results.append(parsed)
            except Exception as e:
                results.append({
                    "detected_languages": [],
                    "is_multilingual": False,
                    "content_style": [],
                    "processed_at": datetime.now().isoformat(),
                    "error": f"Parsing error: {str(e)} | Raw: {raw_response[:100]}"
                })

            time.sleep(1)

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000) 
