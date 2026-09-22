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

    # যেসকল ভিডিওতে আলাদা অডিও থাকে না, তাদের জন্য ফরম্যাট ফলব্যাক
    ydl_opts = {
        'format': 'ba/b/bestaudio/best',  # সেরা অডিও, না পেলে সেরা স্ট্রিম
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
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

            # যদি সরাসরি URL না মেলে, উপলব্ধ ফরম্যাটগুলো ফিল্টার করবে
            if not stream_url:
                formats = info.get('formats', [])
                # অডিও ফরম্যাট খোঁজা
                for f in reversed(formats):
                    if f.get('acodec') != 'none' and f.get('url'):
                        stream_url = f.get('url')
                        break
                # যদি শুধু অডিও না পাওয়া যায়, তবে যেকোনো সক্রিয় স্ট্রিম ইউআরএল নেওয়া
                if not stream_url and formats:
                    stream_url = formats[-1].get('url', '')

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
