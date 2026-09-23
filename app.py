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
        "service": "MusicHub Live Multi-Extractor"
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

        # ================= ১. টিকটক প্রসেসিং =================
        if "tiktok.com" in raw_url:
            try:
                res = requests.get(
                    f"https://www.tikwm.com/api/?url={raw_url}",
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=10
                )
                if res.status_code == 200:
                    t_json = res.json()
                    if t_json.get("code") == 0 and "data" in t_json:
                        d = t_json["data"]
                        return jsonify({
                            "success": True,
                            "platform": "tiktok",
                            "title": d.get("title", "TikTok Audio"),
                            "thumbnail": d.get("cover") or d.get("origin_cover", ""),
                            "stream_url": d.get("music") or d.get("play")
                        }), 200
            except Exception:
                pass
            return jsonify({"error": "server busy"}), 503

        # ================= ২. ইউটিউব প্রসেসিং =================
        video_id = extract_yt_id(raw_url)
        if not video_id:
            return jsonify({"error": "server busy"}), 400

        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        title = f"YouTube Audio ({video_id})"

        try:
            meta_res = requests.get(
                f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}",
                timeout=4
            )
            if meta_res.status_code == 200:
                title = meta_res.json().get('title', title)
        except Exception:
            pass

        audio_stream_url = None

        # মেথড ১: Y2Mate Direct API Relay
        try:
            init_url = "https://www.y2mate.com/mates/analyzeV2/ajax"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
            payload = {
                "k_query": f"https://www.youtube.com/watch?v={video_id}",
                "k_page": "home",
                "hl": "en",
                "q_auto": "0"
            }
            r1 = requests.post(init_url, data=payload, headers=headers, timeout=6)
            if r1.status_code == 200:
                r1_data = r1.json()
                # অডিও কি (Key) বের করা
                links = r1_data.get("links", {}).get("mp3", {})
                first_key = None
                for k in links:
                    first_key = links[k].get("k")
                    if first_key:
                        break
                
                if first_key:
                    conv_url = "https://www.y2mate.com/mates/convertV2/index"
                    conv_payload = {
                        "vid": video_id,
                        "k": first_key
                    }
                    r2 = requests.post(conv_url, data=conv_payload, headers=headers, timeout=8)
                    if r2.status_code == 200:
                        r2_data = r2.json()
                        d_link = r2_data.get("dlink")
                        if d_link:
                            audio_stream_url = d_link
        except Exception:
            pass

        # মেথড ২: Piped API Fallback
        if not audio_stream_url:
            piped_instances = [
                "https://pipedapi.kavin.rocks",
                "https://api.piped.privacydev.net",
                "https://piped-api.lunar.icu"
            ]
            for inst in piped_instances:
                try:
                    res = requests.get(f"{inst}/streams/{video_id}", timeout=4)
                    if res.status_code == 200:
                        stream_data = res.json()
                        audio_streams = stream_data.get("audioStreams", [])
                        if audio_streams:
                            audio_stream_url = audio_streams[-1].get("url")
                            break
                except Exception:
                    continue

        if not audio_stream_url:
            return jsonify({"error": "server busy"}), 503

        return jsonify({
            "success": True,
            "platform": "youtube",
            "title": title,
            "thumbnail": thumbnail,
            "stream_url": audio_stream_url
        }), 200

    except Exception:
        return jsonify({"error": "server busy"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
