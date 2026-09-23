from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def extract_yt_id(url):
    pattern = r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "MusicHub Free Unified Extractor (YT & TikTok)"
    }), 200

@app.route('/convert', methods=['POST'])
def get_stream_url():
    try:
        data = request.get_json(silent=True)
        if not data or 'url' not in data:
            return jsonify({"error": "server busy"}), 400

        raw_url = str(data.get('url', '')).strip()
        if not raw_url:
            return jsonify({"error": "server busy"}), 400

        # ================= ১. টিকটক ফ্রি মেথড =================
        if "tiktok.com" in raw_url:
            try:
                res = requests.get(f"https://www.tikwm.com/api/?url={raw_url}", timeout=8)
                if res.status_code == 200:
                    t_data = res.json()
                    if t_data.get("code") == 0 and "data" in t_data:
                        song_info = t_data["data"]
                        audio_url = song_info.get("music") or song_info.get("play")
                        if audio_url:
                            return jsonify({
                                "success": True,
                                "platform": "tiktok",
                                "title": song_info.get("title", "TikTok Audio"),
                                "thumbnail": song_info.get("cover") or song_info.get("origin_cover", ""),
                                "stream_url": audio_url
                            }), 200
            except Exception:
                pass
            return jsonify({"error": "server busy"}), 503

        # ================= ২. ইউটিউব ফ্রি মেথড =================
        video_id = extract_yt_id(raw_url)
        if not video_id:
            return jsonify({"error": "server busy"}), 400

        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        title = f"YouTube Audio ({video_id})"

        # টাইটেল ফেচিং
        try:
            meta_res = requests.get(
                f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}",
                timeout=4
            )
            if meta_res.status_code == 200:
                title = meta_res.json().get('title', title)
        except Exception:
            pass

        # স্ট্রিম লিংক খোঁজা (ওপেন মেথড)
        audio_direct_url = None

        # মেথড ক: Cobalt API
        try:
            payload = {
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "downloadMode": "audio",
                "audioFormat": "mp3"
            }
            c_res = requests.post(
                "https://api.cobalt.tools/",
                json=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=5
            )
            if c_res.status_code == 200:
                audio_direct_url = c_res.json().get("url")
        except Exception:
            pass

        # মেথড খ: ফ্রি সিডিএন মিরর
        if not audio_direct_url:
            mirrors = [
                f"https://invidious.jing.rocks/latest_version?id={video_id}&itag=140",
                f"https://inv.tux.pizza/latest_version?id={video_id}&itag=140"
            ]
            for mirror in mirrors:
                try:
                    chk = requests.head(mirror, timeout=3, allow_redirects=True)
                    if chk.status_code in [200, 302, 206]:
                        audio_direct_url = mirror
                        break
                except Exception:
                    continue

        if not audio_direct_url:
            return jsonify({"error": "server busy"}), 503

        return jsonify({
            "success": True,
            "platform": "youtube",
            "title": title,
            "thumbnail": thumbnail,
            "stream_url": audio_direct_url
        }), 200

    except Exception:
        # যেকোনো অভ্যন্তরীণ ক্র্যাশ বা টাইমআউটে সরাসরি 'server busy'
        return jsonify({"error": "server busy"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
