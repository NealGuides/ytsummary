import os
import re
import requests
import yt_dlp
import cv2
import pytesseract
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled

app = Flask(__name__)

# Set up Tesseract OCR (Modify path if needed)
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Change path if using locally

# Keywords to detect if it's a tactics video
TACTIC_KEYWORDS = ["tactic", "custom tactics", "formation", "tactics"]

def download_frame(video_url, timestamp="3:58"):
    """Downloads a frame from the video at a given timestamp."""
    video_id = video_url.split("v=")[-1].split("&")[0]
    output_filename = f"{video_id}.jpg"

    ydl_opts = {
        "format": "best",
        "outtmpl": "temp_video.mp4"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        os.system(f"ffmpeg -i temp_video.mp4 -ss {timestamp} -vframes 1 {output_filename}")
        os.remove("temp_video.mp4")  # Clean up
        return output_filename

    except Exception as e:
        print(f"Error downloading frame: {e}")
        return None

def extract_tactic_code(image_path):
    """Uses OCR to extract the tactic code from the image."""
    image = cv2.imread(image_path)

    # Crop the top-left corner where the tactic code appears
    height, width, _ = image.shape
    cropped_image = image[50:200, 50:500]  # Adjust as needed

    # Convert image to grayscale & apply thresholding for better OCR
    gray = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
    _, thresholded = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Perform OCR
    text = pytesseract.image_to_string(thresholded)

    # Extract the tactic code pattern
    match = re.search(r'\b[A-Za-z0-9]{8,12}\b', text)  # Adjust pattern based on actual format
    return match.group(0) if match else None

def get_transcript(video_id):
    """Retrieves the transcript of the video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return "\n".join([f"{entry['start']:.2f}: {entry['text']}" for entry in transcript])
    except TranscriptsDisabled:
        return None
    except Exception as e:
        print(f"Error retrieving transcript: {e}")
        return None

def generate_tweet(title, video_url, transcript, tactic_code=None):
    """Generates a tweet based on the extracted data."""
    tweet = f"🚨 {title} 🚨\n\n"

    if "dribbling" in title.lower():
        tweet += "⚡ Learn how to dribble past defenders with ease! ⚡\n\n"
    elif "passing" in title.lower():
        tweet += "✅ Master precision passing & break defenses ✅\n\n"
    else:
        tweet += "🔥 Key insights from the latest FC 25 tutorial 🔥\n\n"

    key_points = transcript.split("\n")[:3] if transcript else ["✅ Watch the full breakdown!"]
    tweet += "\n".join(key_points) + "\n\n"

    if tactic_code:
        tweet += "👇\n🛜 **CODE:** " + tactic_code + "\n\n"

    tweet += f"📺 Watch here: {video_url}\n\n#FC25 #EAFC25 #EASPORTSFC25"

    return tweet

@app.route('/analyze', methods=['POST'])
def analyze_video():
    """API Endpoint: Accepts a YouTube link and analyzes it."""
    data = request.get_json()
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    video_id = video_url.split("v=")[-1].split("&")[0]

    # Fetch video title
    api_key = "YOUR_YOUTUBE_API_KEY"  # Replace with actual API key
    response = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}")
    title = response.json()["items"][0]["snippet"]["title"] if response.ok else "FC 25 Video"

    # Check if this is a tactics video
    is_tactic_video = any(keyword in title.lower() for keyword in TACTIC_KEYWORDS)

    # Extract transcript
    transcript = get_transcript(video_id)

    # Extract tactic code (if applicable)
    tactic_code = None
    if is_tactic_video:
        frame_path = download_frame(video_url)
        if frame_path:
            tactic_code = extract_tactic_code(frame_path)

    # Generate tweet
    tweet = generate_tweet(title, video_url, transcript, tactic_code)
    
    return jsonify({"title": title, "transcript": transcript, "tactic_code": tactic_code, "tweet": tweet})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
