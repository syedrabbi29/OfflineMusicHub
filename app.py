from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import traceback
import os

app = Flask(__name__)
# যেকোনো মোবাইল অ্যাপ বা ফ্রন্টএন্ড থেকে কল করার অনুমতি
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "Music Stream URL Extractor",
        "message": "API backend is active."
    }), 200

@app.route('/convert', methods=['POST'])
def get_stream_url():
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400

    raw_url = str(data.get('url', '')).strip()
    if not raw_url:
        return jsonify({"error": "URL cannot be empty"}), 400

    # এখানে কোনো ফাইল ডাউনলোড হবে না, শুধু ডিরেক্ট স্ট্রিম লিংক বের করা হবে
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # download=False দেওয়া হয়েছে যাতে রেন্ডার সার্ভারে ডাউনলোড না হয়
            info = ydl.extract_info(raw_url, download=False)
            
            # সরাসরি অডিও স্ট্রিমিং লিংক নেওয়া হচ্ছে
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
