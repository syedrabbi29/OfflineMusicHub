from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import os
import re
import logging

app = Flask(__name__)

# =========================
# CONFIG
# =========================

CORS(app, resources={
    r"/*": {
        "origins": "*"
    }
})

MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB
REQUEST_TIMEOUT = (5, 20)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MusicHub")


# =========================
# HELPERS
# =========================

def error_response(message="server busy", status=503):
    return jsonify({
        "success": False,
        "error": message
    }), status


def extract_yt_id(url):
    patterns = [
        r"(?:youtube\.com/watch\?v=)([\w-]{11})",
        r"(?:youtu\.be/)([\w-]{11})",
        r"(?:youtube\.com/embed/)([\w-]{11})",
        r"(?:youtube\.com/shorts/)([\w-]{11})",
        r"(?:youtube\.com/v/)([\w-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


def download_to_base64(url, mime="audio/mpeg"):
    """
    Downloads an audio file with a size limit
    and converts it to Base64.
    """

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code != 200:
            logger.warning(
                "Audio request failed: %s",
                response.status_code
            )
            return None

        content_length = response.headers.get("Content-Length")

        if content_length:
            try:
                if int(content_length) > MAX_AUDIO_SIZE:
                    logger.warning("Audio too large")
                    return None
            except ValueError:
                pass

        chunks = []
        total = 0

        for chunk in response.iter_content(chunk_size=64 * 1024):

            if not chunk:
                continue

            total += len(chunk)

            if total > MAX_AUDIO_SIZE:
                logger.warning("Audio exceeded size limit")
                return None

            chunks.append(chunk)

        audio_data = b"".join(chunks)

        if not audio_data:
            return None

        return (
            f"data:{mime};base64,"
            + base64.b64encode(audio_data).decode("utf-8")
        )

    except requests.RequestException as e:
        logger.error("Download error: %s", e)
        return None

    except Exception as e:
        logger.error("Unexpected audio error: %s", e)
        return None


# =========================
# HOME
# =========================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "status": "online",
        "service": "MusicHub Converter",
        "version": "2.0"
    }), 200


# =========================
# HEALTH CHECK
# =========================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "healthy"
    }), 200


# =========================
# CONVERT
# =========================

@app.route("/convert", methods=["POST"])
def convert_audio():

    try:

        # -------------------------
        # JSON CHECK
        # -------------------------

        data = request.get_json(silent=True)

        if not data:
            return error_response(
                "Invalid request",
                400
            )

        raw_url = str(
            data.get("url", "")
        ).strip()

        if not raw_url:
            return error_response(
                "URL is required",
                400
            )

        # Prevent extremely long malicious input
        if len(raw_url) > 2048:
            return error_response(
                "Invalid URL",
                400
            )

        logger.info(
            "Conversion request received: %s",
            raw_url[:150]
        )

        # =========================
        # TIKTOK
        # =========================

        if "tiktok.com" in raw_url.lower():

            try:

                api_url = (
                    "https://www.tikwm.com/api/"
                    "?url=" + requests.utils.quote(
                        raw_url,
                        safe=""
                    )
                )

                response = requests.get(
                    api_url,
                    timeout=REQUEST_TIMEOUT,
                    headers={
                        "User-Agent": "Mozilla/5.0"
                    }
                )

                if response.status_code != 200:
                    return error_response()

                t_json = response.json()

                if t_json.get("code") != 0:
                    return error_response()

                d = t_json.get("data") or {}

                audio_link = (
                    d.get("music")
                    or d.get("play")
                )

                if not audio_link:
                    return error_response()

                audio = download_to_base64(
                    audio_link,
                    "audio/mpeg"
                )

                if not audio:
                    return error_response()

                title = (
                    d.get("title")
                    or "TikTok Audio"
                )

                thumbnail = (
                    d.get("cover")
                    or d.get("origin_cover")
                    or ""
                )

                return jsonify({
                    "success": True,
                    "platform": "tiktok",
                    "title": str(title)[:100],
                    "thumbnail": thumbnail,
                    "audio": audio
                }), 200

            except Exception as e:

                logger.error(
                    "TikTok error: %s",
                    e
                )

                return error_response()


        # =========================
        # YOUTUBE
        # =========================

        yt_id = extract_yt_id(raw_url)

        if yt_id:

            title = f"YouTube Audio ({yt_id})"

            thumbnail = (
                f"https://img.youtube.com/vi/"
                f"{yt_id}/hqdefault.jpg"
            )

            # -------------------------
            # METADATA
            # -------------------------

            try:

                metadata_url = (
                    "https://noembed.com/embed"
                    "?url=https://www.youtube.com/watch?v="
                    + yt_id
                )

                metadata = requests.get(
                    metadata_url,
                    timeout=(3, 5),
                    headers={
                        "User-Agent": "Mozilla/5.0"
                    }
                )

                if metadata.status_code == 200:

                    meta_json = metadata.json()

                    title = (
                        meta_json.get("title")
                        or title
                    )

            except Exception as e:

                logger.warning(
                    "Metadata failed: %s",
                    e
                )

            # ------------------------------------------------
            # IMPORTANT:
            # Do not depend on random Invidious mirrors here.
            #
            # A reliable YouTube media URL should come from
            # an authorized media source/service.
            # ------------------------------------------------

            return jsonify({
                "success": False,
                "platform": "youtube",
                "title": str(title)[:100],
                "thumbnail": thumbnail,
                "error": "youtube_media_source_unavailable"
            }), 503


        # =========================
        # UNKNOWN URL
        # =========================

        return error_response(
            "Unsupported URL",
            400
        )


    except Exception as e:

        logger.exception(
            "Unexpected server error: %s",
            e
        )

        return error_response()


# =========================
# ERROR HANDLERS
# =========================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "endpoint_not_found"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({
        "success": False,
        "error": "method_not_allowed"
    }), 405


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "success": False,
        "error": "server_error"
    }), 500


# =========================
# RUN
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    logger.info(
        "MusicHub starting on port %s",
        port
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
