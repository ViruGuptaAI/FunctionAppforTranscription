import azure.functions as func
import logging
import json
import os
import io

from dotenv import load_dotenv
load_dotenv()

from azure.ai.transcription import TranscriptionClient
from azure.ai.transcription.models import TranscriptionContent, TranscriptionOptions
from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def get_transcription_client() -> TranscriptionClient:
    speech_endpoint = os.environ["SPEECH_ENDPOINT"]
    return TranscriptionClient(
        endpoint=speech_endpoint,
        credential=DefaultAzureCredential()
    )


@app.route(route="transcribe", methods=["POST"])
def transcribe(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Transcribe function triggered.")

    # Read optional query params
    locales_param = req.params.get("locales", "hi-IN,mr-IN,gu-IN,en-IN")
    locales = [loc.strip() for loc in locales_param.split(",")]
    diarization = req.params.get("diarization", "true").lower() == "true"

    # Get the WAV file from the request body
    try:
        # Try multipart form upload first
        file = req.files.get("audio")
        if file:
            audio_bytes = file.stream.read()
        else:
            # Fall back to raw body
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

    # Build transcription options
    if diarization:
        options = TranscriptionOptions(
            locales=locales,
            diarization_options={"enabled": True}
        )
    else:
        options = TranscriptionOptions(locales=locales)

    # Call the Fast Transcription API
    try:
        client = get_transcription_client()
        audio_stream = io.BytesIO(audio_bytes)
        content = TranscriptionContent(definition=options, audio=audio_stream)
        result = client.transcribe(content)
    except Exception as e:
        logging.error(f"Transcription failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Transcription failed: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

    # Build response
    combined_text = ""
    if result.combined_phrases:
        combined_text = result.combined_phrases[0].text

    phrases = []
    for phrase in result.phrases:
        phrases.append({
            "speaker": phrase.speaker,
            "locale": phrase.locale,
            "text": phrase.text,
            "offset": phrase.offset,
            "duration": phrase.duration
        })

    response_body = {
        "combinedText": combined_text,
        "phrases": phrases,
        "duration": result.duration
    }

    return func.HttpResponse(
        json.dumps(response_body, ensure_ascii=False),
        status_code=200,
        mimetype="application/json"
    )
