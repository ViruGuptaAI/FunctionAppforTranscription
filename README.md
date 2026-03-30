# Azure Function App — Speech Transcription Service

An Azure Function App that transcribes audio files using the [Azure AI Speech Fast Transcription API](https://learn.microsoft.com/azure/ai-services/speech-service/fast-transcription-create). Supports multi-language transcription with speaker diarization.

## Features

- **Multi-language support** — Transcribe audio in multiple locales (e.g., `hi-IN`, `en-IN`, `mr-IN`, `gu-IN`)
- **Speaker diarization** — Identifies individual speakers in the audio
- **Managed identity auth** — Uses `DefaultAzureCredential` (no keys/secrets stored)
- **VNet secured** — Connects to Speech and Storage services via private endpoints

## Architecture

```
Client → POST /api/transcribe (with WAV file)
           │
           ▼
    Azure Function App (Flex Consumption, Python 3.13)
           │  VNet Integration
           │
           ├──► Azure Storage (via Private Endpoint)
           │    Runtime storage (blobs, queues, tables)
           │
           └──► Azure AI Speech Service (via Private Endpoint)
                Fast Transcription REST API
```

## Prerequisites

- Azure subscription
- Azure CLI (`az`) installed and logged in
- Python 3.11+
- Azure resources:
  - **Function App** (Flex Consumption plan, Python runtime)
  - **Azure AI Speech Service**
  - **Storage Account** (for Function App runtime)
  - *(Optional – for production)* **VNet** with subnets for VNet integration and private endpoints
  - *(Optional – for production)* **Private DNS Zones**: `privatelink.blob.core.windows.net`, `privatelink.cognitiveservices.azure.com`

> **Note:** VNet integration, private endpoints, and Private DNS Zones are recommended for production to secure traffic between the Function App and backend services. They are **not required** to get started — the function works fine with publicly accessible Speech and Storage resources.

## Azure Configuration

### App Settings

| Setting | Description |
|---------|-------------|
| `SPEECH_ENDPOINT` | Azure AI Speech service endpoint (e.g., `https://<name>.cognitiveservices.azure.com/`) |
| `AzureWebJobsStorage__blobServiceUri` | Storage blob endpoint |
| `AzureWebJobsStorage__queueServiceUri` | Storage queue endpoint |
| `AzureWebJobsStorage__tableServiceUri` | Storage table endpoint |
| `AzureWebJobsStorage__credential` | `managedidentity` |

### RBAC Roles (Managed Identity)

| Role | Scope |
|------|-------|
| `Storage Blob Data Owner` | Storage Account |
| `Storage Queue Data Contributor` | Storage Account |
| `Storage Table Data Contributor` | Storage Account |
| `Cognitive Services User` | Speech Service |

## API Usage

### Endpoint

```
POST https://<function-app>.azurewebsites.net/api/transcribe?code=<function-key>
```

### Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `locales` | `hi-IN,mr-IN,gu-IN,en-IN` | Comma-separated locale codes |
| `diarization` | `true` | Enable speaker diarization |

### Request

Send a WAV file as multipart form-data (`audio` field) or as the raw request body.

**Multipart form-data:**
```bash
curl -X POST "https://<function-app>.azurewebsites.net/api/transcribe?code=<key>&locales=hi-IN,en-IN" \
  -F "audio=@recording.wav"
```

**Raw body:**
```bash
curl -X POST "https://<function-app>.azurewebsites.net/api/transcribe?code=<key>" \
  -H "Content-Type: audio/wav" \
  --data-binary @recording.wav
```

### Response

```json
{
  "combinedText": "Full transcribed text...",
  "phrases": [
    {
      "speaker": 1,
      "locale": "hi-IN",
      "text": "Phrase text...",
      "offset": null,
      "duration": null
    }
  ],
  "duration": null
}
```

## Local Development

1. Clone the repo
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your `SPEECH_ENDPOINT`
4. Run locally:
   ```bash
   func start
   ```

## Deployment

```bash
az functionapp deployment source config-zip \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --src <zip-file-path> \
  --build-remote true
```

## Project Structure

```
├── function_app.py      # Main function code (transcribe endpoint)
├── host.json            # Function host configuration
├── requirements.txt     # Python dependencies
├── local.settings.json  # Local dev settings (not committed)
├── .funcignore          # Files excluded from deployment
├── .gitignore           # Files excluded from git
└── Data/                # Sample audio files for testing
```
