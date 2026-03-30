import azure.functions as func
import logging
import json
import os
import requests

from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

SPEECH_SCOPE = "https://cognitiveservices.azure.com/.default"
API_VERSION = "2024-11-15"


def get_access_token() -> str:
    credential = DefaultAzureCredential()
    token = credential.get_token(SPEECH_SCOPE)
    return token.token


@app.route(route="transcribe", methods=["POST"])
def transcribe(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Transcribe function triggered.")

    speech_endpoint = os.environ.get("SPEECH_ENDPOINT")
    if not speech_endpoint:
        return func.HttpResponse(
            json.dumps({"error": "SPEECH_ENDPOINT is not configured."}),
            status_code=500,
            mimetype="application/json"
        )

    # Read optional query params
    locales_param = req.params.get("locales", "hi-IN,mr-IN,gu-IN,en-IN")
    locales = [loc.strip() for loc in locales_param.split(",")]
    diarization = req.params.get("diarization", "true").lower() == "true"

    # Get the WAV file from the request body
    try:
        file = req.files.get("audio")
        if file:
            audio_bytes = file.stream.read()
        else:
            audio_bytes = req.get_body()

        if not audio_bytes:
            return func.HttpResponse(
                json.dumps({"error": "No audio data provided. Send a WAV file as 'audio' in form-data or as the raw request body."}),
                status_code=400,
                mimetype="application/json"
            )
    except Exception as e:
        logging.error(f"Error reading audio from request: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to read audio data: {str(e)}"}),
            status_code=400,
            mimetype="application/json"
        )

    # Build the definition JSON for Fast Transcription API
    definition = {"locales": locales}
    if diarization:
        definition["diarization"] = {"enabled": True}

    # Call the Fast Transcription REST API
    try:
        token = get_access_token()
        url = f"{speech_endpoint.rstrip('/')}/speechtotext/transcriptions:transcribe?api-version={API_VERSION}"

        files_payload = {
            "audio": ("audio.wav", audio_bytes, "audio/wav"),
            "definition": (None, json.dumps(definition), "application/json"),
        }
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.post(url, files=files_payload, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"Transcription API error: {e} - {e.response.text if e.response else ''}")
        return func.HttpResponse(
            json.dumps({"error": f"Transcription failed: {str(e)}"}),
            status_code=502,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Transcription failed: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

    # Build response
    combined_text = ""
    combined_phrases = result.get("combinedPhrases", [])
    if combined_phrases:
        combined_text = combined_phrases[0].get("text", "")

    phrases = []
    for phrase in result.get("phrases", []):
        phrases.append({
            "speaker": phrase.get("speaker"),
            "locale": phrase.get("locale"),
            "text": phrase.get("text"),
            "offset": phrase.get("offset"),
            "duration": phrase.get("duration"),
        })

    response_body = {
        "combinedText": combined_text,
        "phrases": phrases,
        "duration": result.get("duration"),
    }

    return func.HttpResponse(
        json.dumps(response_body, ensure_ascii=False),
        status_code=200,
        mimetype="application/json"
    )
