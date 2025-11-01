import requests
import os
import sys
import base64
from urllib.parse import urlparse, unquote
from datetime import datetime
import concurrent.futures
import re

def download_story(story, download_path, story_count):
    base64_url = story.get('url')
    if not base64_url:
        return False
    media_type = 'video' if story.get('type') == 'video' else 'image'
    story_id = story.get('id')
    taken_at = story.get('taken_at')
    if taken_at:
        dt_object = datetime.fromtimestamp(taken_at)
        timestamp_str = dt_object.strftime('%H-%M-%S_%m-%d-%Y')
        folder_name = dt_object.strftime('%m-%d-%Y')
        if media_type == 'video':
            filename = f"{timestamp_str}.mp4"
        else:
            filename = f"{timestamp_str}.jpg"
    else:
        folder_name = "unknown_date"
        if media_type == 'video':
            filename = f"{story_id}.mp4"
        else:
            filename = f"{story_id}.jpg"
    day_folder_path = os.path.join(download_path, folder_name)
    os.makedirs(day_folder_path, exist_ok=True)
    if media_type == 'video':
        media_url = 'https://stories-cdn.fun/' + base64_url
    else:
        try:
            base64_url += '=' * (-len(base64_url) % 4)
            media_url = base64.urlsafe_b64decode(base64_url).decode('utf-8')
        except (base64.binascii.Error, UnicodeDecodeError):
            return False
    filepath = os.path.join(day_folder_path, filename)
    if os.path.exists(filepath):
        return False
    try:
        response = requests.get(media_url, timeout=60)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return True
    except requests.RequestException:
        return False

def main():
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = "umaaclara"
    base_url = "https://storynavigation.com"
    user_page_url = f"{base_url}/user/{username}"
    profile_api_url = f"{base_url}/mystorysaver-data/get-user-profile"
    stories_api_url = f"{base_url}/mystorysaver-data/get-user-last-stories"
    download_folder_name = "auto_archive"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    download_path = os.path.join(script_dir, download_folder_name)
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    with requests.Session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        response = session.get(user_page_url, timeout=30)
        response.raise_for_status()
        match = re.search('<meta name="csrf-token" content="(.*?)">', response.text)
        if not match:
            sys.exit(1)
        csrf_token = match.group(1)
        session.headers.update({
            "X-CSRF-TOKEN": csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": user_page_url
        })
        response = session.post(profile_api_url, json={"userName": username}, timeout=30)
        response.raise_for_status()
        profile_data = response.json()
        if not profile_data.get("found"):
            sys.exit(1)
        user_info = profile_data.get("accountInfo", {})
        user_id = user_info.get("id")
        is_private = user_info.get("isPrivate")
        if not user_id:
            sys.exit(1)
        response = session.post(stories_api_url, json={"userName": username, "isPrivate": is_private, "instagramUserId": user_id}, timeout=30)
        response.raise_for_status()
        stories = response.json().get("lastStories", [])
    if not stories:
        return
    downloaded_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_story = {
            executor.submit(download_story, story, download_path, i + 1): story 
            for i, story in enumerate(stories)
        }
        for future in concurrent.futures.as_completed(future_to_story):
            try:
                if future.result():
                    downloaded_count += 1
            except Exception:
                pass

if __name__ == "__main__":
    main()
