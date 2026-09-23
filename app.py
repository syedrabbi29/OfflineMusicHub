from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import os
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def extract_yt_id(url):
    pattern = r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "service": "MusicHub Converter"}), 200

@app.route('/convert', methods=['POST'])
def convert_audio():
    try:
        data = request.get_json(silent=True)
        if not data or 'url' not in data:
            return jsonify({"error": "server busy"}), 400

        raw_url = str(data.get('url', '')).strip()
        if not raw_url:
            return jsonify({"error": "server busy"}), 400

        # ================= ১. টিকটক (আগের মতো নিখুঁত বেস৬৪ রিটার্ন) =================
        if "tiktok.com" in raw_url:
            try:
                res = requests.get(f"https://www.tikwm.com/api/?url={raw_url}", timeout=10)
                t_json = res.json()
                if t_json.get("code") == 0 and "data" in t_json:
                    d = t_json["data"]
                    audio_link = d.get("music") or d.get("play")
                    
                    # অডিও ডাউনলোড করে base64 করা
                    audio_req = requests.get(audio_link, timeout=15)
                    b64_audio = "data:audio/mp3;base64," + base64.b64encode(audio_req.content).decode('utf-8')

                    return jsonify({
                        "title": d.get("title", "TikTok Audio")[:50],
                        "thumbnail": d.get("cover") or d.get("origin_cover", ""),
                        "audio": b64_audio
                    }), 200
            except Exception:
                return jsonify({"error": "server busy"}), 503

        # ================= ২. ইউটিউব হ্যান্ডলার =================
        yt_id = extract_yt_id(raw_url)
        if not yt_id:
            return jsonify({"error": "server busy"}), 400

        # মেটাডাটা
        title = f"YouTube Audio ({yt_id})"
        thumbnail = f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
        try:
            m = requests.get(f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={yt_id}", timeout=4)
            if m.status_code == 200:
                title = m.json().get('title', title)
        except Exception:
            pass

        # স্ট্রিম ডাউনলোড
        audio_stream_url = None
        mirrors = [
            f"https://invidious.jing.rocks/latest_version?id={yt_id}&itag=140",
            f"https://vid.puffyan.us/latest_version?id={yt_id}&itag=140"
        ]
        for m in mirrors:
            try:
                chk = requests.head(m, timeout=3, allow_redirects=True)
                if chk.status_code in [200, 302, 206]:
                    audio_stream_url = m
                    break
            except Exception:
                continue

        if not audio_stream_url:
            return jsonify({"error": "server busy"}), 503

        # অডিও নামিয়ে বেস৬৪ রিটার্ন
        a_res = requests.get(audio_stream_url, timeout=20)
        b64_yt = "data:audio/mp3;base64," + base64.b64encode(a_res.content).decode('utf-8')

        return jsonify({
            "title": title[:50],
            "thumbnail": thumbnail,
            "audio": b64_yt
        }), 200

    except Exception:
        return jsonify({"error": "server busy"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
