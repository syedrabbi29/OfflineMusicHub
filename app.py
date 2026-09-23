from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def extract_video_id(url):
    pattern = r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "MusicHub Free Direct Stream API"
    }), 200

@app.route('/convert', methods=['POST'])
def get_stream_url():
    # কোনো ব্যতিক্রম ঘটলে যাতে ফ্রন্টএন্ডে কোনো টেকনিক্যাল এরর না গিয়ে 'server busy' যায়
    try:
        data = request.get_json(silent=True)
        if not data or 'url' not in data:
            return jsonify({"error": "server busy"}), 400

        raw_url = str(data.get('url', '')).strip()
        video_id = extract_video_id(raw_url)

        if not video_id:
            return jsonify({"error": "server busy"}), 400

        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        title = f"YouTube Audio ({video_id})"

        # ১. ভিডিও মেটাডাটা (Title) সংগ্রহ
        try:
            meta_res = requests.get(
                f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}",
                timeout=4
            )
            if meta_res.status_code == 200:
                t_json = meta_res.json()
                title = t_json.get('title', title)
        except Exception:
            pass

        # ২. ডিরেক্ট অডিও স্ট্রিম লিঙ্ক সংগ্রহ (ওপেন পাবলিক সিডিএন মেথড)
        audio_direct_url = None

        # মেথড ক: Cobalt API
        try:
            c_payload = {
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "downloadMode": "audio",
                "audioFormat": "mp3"
            }
            c_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            c_res = requests.post("https://api.cobalt.tools/", json=c_payload, headers=c_headers, timeout=6)
            if c_res.status_code == 200:
                c_data = c_res.json()
                if c_data.get("url"):
                    audio_direct_url = c_data.get("url")
        except Exception:
            pass

        # মেথড খ: অল্টারনেটিভ ফ্রি সিডিএন
        if not audio_direct_url:
            mirrors = [
                f"https://invidious.jing.rocks/latest_version?id={video_id}&itag=140",
                f"https://inv.tux.pizza/latest_version?id={video_id}&itag=140",
                f"https://vid.puffyan.us/latest_version?id={video_id}&itag=140"
            ]
            for mirror in mirrors:
                try:
                    chk = requests.head(mirror, timeout=3, allow_redirects=True)
                    if chk.status_code in [200, 302, 206]:
                        audio_direct_url = mirror
                        break
                except Exception:
                    continue

        # স্ট্রিম না পাওয়া গেলে কাস্টম 'server busy' মেসেজ
        if not audio_direct_url:
            return jsonify({"error": "server busy"}), 503

        return jsonify({
            "success": True,
            "title": title,
            "thumbnail": thumbnail,
            "stream_url": audio_direct_url
        }), 200

    except Exception:
        # ব্যাকএন্ডে যে কোনো অনাকাঙ্ক্ষিত এরর ঘটলে শুধু 'server busy' রিটার্ন হবে
        return jsonify({"error": "server busy"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
