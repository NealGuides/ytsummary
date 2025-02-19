import os
import re
import requests
import yt_dlp
import cv2
import pytesseract
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# 🔹 Extracts Transcript from YouTube Video
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return "\n".join([f"{entry['start']:.2f}: {entry['text']}" for entry in transcript])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching transcript: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

@app.route('/get_transcript', methods=['GET'])
def transcript_api():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    video_id = url.split("v=")[-1].split("&")[0]
    transcript = get_transcript(video_id)
    return jsonify({"transcript": transcript})

# 🔹 Extracts Tactic Code from Video (Using Image Processing)
def extract_tactic_code(video_url):
    try:
        output_file = "frame.jpg"
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.mp4',
            'quiet': True
        }

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Capture a frame at ~4 sec mark
        cap = cv2.VideoCapture("video.mp4")
        cap.set(cv2.CAP_PROP_POS_MSEC, 4000)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("Failed to capture video frame.")
            return None

        # Save frame as image and extract text
        cv2.imwrite(output_file, frame)
        img = cv2.imread(output_file)
        roi = img[50:150, 50:300]  # Crop top-left where code appears
        text = pytesseract.image_to_string(roi, config='--psm 6')

        tactic_code = re.search(r'\b[A-Za-z0-9]{8,12}\b', text)

        # Clean up temporary files
        os.remove("video.mp4")
        os.remove(output_file)

        return tactic_code.group(0) if tactic_code else None

    except yt_dlp.utils.DownloadError as e:
        print(f"Error downloading video: {e}")
        return jsonify({"error": f"Error downloading video: {e}"}), 500
    except cv2.error as e:
        print(f"Error processing video frame: {e}")
        os.remove("video.mp4")  # Clean up video file in case of error
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        os.remove("video.mp4")  # Clean up video file in case of error
        os.remove(output_file)
        return None

@app.route('/get_tactic_code', methods=['GET'])
def tactic_code_api():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        video_title = requests.get(f"https://www.youtube.com/oembed?url={url}&format=json").json().get("title", "")
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error fetching video title: {e}"}), 500

    # Check if the title contains relevant tactic keywords
    if any(keyword in video_title.lower() for keyword in ["tactic", "custom tactics", "formation"]):
        tactic_code = extract_tactic_code(url)
        if tactic_code:
            return jsonify({"tactic_code": f"👇\n🛜 CODE: {tactic_code}"}), 200
        return jsonify({"error": "Tactic code not found in video"}), 404

    return jsonify({"message": "This video does not contain a tactic code."}), 200

# ✅ Flask Server Configuration
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)  # Port 3000 is better for Replit
