from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = "\n".join([f"{entry['start']}: {entry['text']}" for entry in transcript])
        return transcript_text
    except:
        return None

def fetch_auto_captions(video_url):
    ydl_opts = {
        'writesubtitles': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'quiet': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(video_url, download=False)
            subtitles = info_dict.get("subtitles")
            if subtitles and 'en' in subtitles:
                transcript = subtitles['en'][0]['url']
                return transcript
        except:
            return None
    return None

@app.route('/get_transcript', methods=['GET'])
def transcript_api():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing video URL"}), 400
    
    video_id = video_url.split("v=")[-1]
    transcript = get_transcript(video_id)
    if not transcript:
        transcript = fetch_auto_captions(video_url)
    
    if transcript:
        return jsonify({"transcript": transcript})
    else:
        return jsonify({"error": "Transcript not available"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
