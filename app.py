from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import uuid
import glob
import urllib.request
import base64
import traceback

app = Flask(__name__)

# যেকোনো অ্যান্ড্রয়েড অ্যাপ, ওয়েবভিউ বা লোকাল ফাইল থেকে রিকোয়েস্ট পাঠানোর অনুমতি (CORS)
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_audio")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# শর্ট লিংক আনপ্যাক করা (Redirect resolve)
def resolve_final_url(url):
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.geturl()
    except Exception:
        return url

# সার্ভার সচল আছে কি না তা টেস্ট করার রুট
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "service": "Music Converter API",
        "message": "API backend is running successfully."
    }), 200

@app.route('/convert', methods=['POST'])
def convert_video():
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided in request body."}), 400

    raw_url = str(data.get('url', '')).strip()
    if not raw_url:
        return jsonify({"error": "URL cannot be empty."}), 400

    url = resolve_final_url(raw_url)
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 35,
        'retries': 5,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown Track')
            thumb_url = info.get('thumbnail', '')

            downloaded_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{file_id}.*"))
            if not downloaded_files:
                return jsonify({"error": "Audio extraction failed. Please check the URL."}), 500

            audio_path = downloaded_files[0]

        # থাম্বনেইল Base64 এ কনভার্ট
        thumb_b64 = ""
        if thumb_url:
            try:
                req = urllib.request.Request(
                    thumb_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=8) as response:
                    thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(response.read()).decode('utf-8')
            except Exception:
                thumb_b64 = ""

        # অডিও ফাইল Base64 এ কনভার্ট
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode('utf-8')

        # মেমরি ক্লিয়ার রাখতে টেম্প ফাইল ডিলিট
        if os.path.exists(audio_path):
            os.remove(audio_path)

        return jsonify({
            "success": True,
            "title": title,
            "thumbnail": thumb_b64,
            "audio": "data:audio/mp4;base64," + audio_b64
        }), 200

    except Exception as e:
        print("[ERROR]", traceback.format_exc())
        err_msg = str(e)
        if "handshake operation timed out" in err_msg or "timed out" in err_msg:
            err_msg = "Connection timed out. The provider might be throttling or blocking requests."
        elif "Sign in to confirm" in err_msg:
            err_msg = "Bot detection triggered. Try another video link."
        return jsonify({"error": err_msg}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
