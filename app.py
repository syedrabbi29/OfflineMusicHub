from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import traceback
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

COOKIE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "Music Stream URL Extractor",
        "cookies_loaded": os.path.exists(COOKIE_PATH)
    }), 200

@app.route('/convert', methods=['POST'])
def get_stream_url():
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400

    raw_url = str(data.get('url', '')).strip()
    if not raw_url:
        return jsonify({"error": "URL cannot be empty"}), 400

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 25,
        'nocheckcertificate': True,
        # 'The page needs to be reloaded' এড়াতে মোবাইল ক্লায়েন্ট ফোর্স করা
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 14; US) gzip',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    if os.path.exists(COOKIE_PATH):
        ydl_opts['cookiefile'] = COOKIE_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(raw_url, download=False)
            
            stream_url = info.get('url', '')
            title = info.get('title', 'Unknown Track')
            thumbnail = info.get('thumbnail', '')

            if not stream_url:
                return jsonify({"error": "Direct audio stream could not be extracted."}), 500

            return jsonify({
                "success": True,
                "title": title,
                "thumbnail": thumbnail,
                "stream_url": stream_url
            }), 200

    except Exception as e:
        print("[ERROR]", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
