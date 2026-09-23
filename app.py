from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import traceback
import os
import random

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# আপনার ৪টি Webshare প্রক্সি লিস্ট
PROXIES = [
    "http://wtwpshfw:4mozjw97rm1d@31.59.20.176:6754",
    "http://wtwpshfw:4mozjw97rm1d@45.38.107.97:6014",
    "http://wtwpshfw:4mozjw97rm1d@198.105.121.200:6462",
    "http://wtwpshfw:4mozjw97rm1d@64.137.96.74:6641"
]

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "Music Stream URL Extractor with Webshare Proxies",
        "total_proxies": len(PROXIES)
    }), 200

@app.route('/convert', methods=['POST'])
def get_stream_url():
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400

    raw_url = str(data.get('url', '')).strip()
    if not raw_url:
        return jsonify({"error": "URL cannot be empty"}), 400

    # প্রক্সি লিস্ট এলোমেলো (shuffle) করে নেওয়া যাতে প্রতি রিকোয়েস্টে আলাদা প্রক্সি ট্রাই হয়
    shuffled_proxies = random.sample(PROXIES, len(PROXIES))
    last_error = "Unknown error"

    for current_proxy in shuffled_proxies:
        ydl_opts = {
            'format': 'ba/b/bestaudio/best',
            'proxy': current_proxy,  # Webshare আইপি দিয়ে রিকোয়েস্ট যাবে
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 20,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(raw_url, download=False)
                
                stream_url = info.get('url', '')
                title = info.get('title', 'Unknown Track')
                thumbnail = info.get('thumbnail', '')

                # যদি ডিরেক্ট URL না মেলে, উপলব্ধ ফরম্যাট থেকে নেওয়া
                if not stream_url:
                    formats = info.get('formats', [])
                    for f in reversed(formats):
                        if f.get('acodec') != 'none' and f.get('url'):
                            stream_url = f.get('url')
                            break
                    if not stream_url and formats:
                        stream_url = formats[-1].get('url', '')

                if stream_url:
                    return jsonify({
                        "success": True,
                        "title": title,
                        "thumbnail": thumbnail,
                        "stream_url": stream_url
                    }), 200

        except Exception as e:
            last_error = str(e)
            print(f"[PROXY FAILED] {current_proxy} -> Error: {last_error}")
            continue  # একটি প্রক্সিতে সমস্যা হলে পরের প্রক্সিতে চেষ্টা করবে

    print("[ALL PROXIES FAILED]", traceback.format_exc())
    return jsonify({"error": f"Failed to extract stream: {last_error}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
