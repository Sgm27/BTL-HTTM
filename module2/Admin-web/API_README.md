# Audio Dataset Management API

A FastAPI backend server that provides CRUD operations for the audio dataset database schema defined in `ingest_to_db.py`. This API treats audio and transcript as pairs, supports file uploads, and provides model audio generation capabilities.

## Features

- **Audio-Transcript Pair Management** - Handle audio and transcripts as paired entities
- **File Upload Support** - Automatic saving of audio and transcript files
- **Complete CRUD operations** for Files, Transcripts, and Audio records
- **Model Audio Generation** - Generate audio from transcripts using TTS models
- **RESTful API** with proper HTTP status codes
- **Pagination support** for listing endpoints
- **Filtering capabilities** by various fields
- **File download** capabilities
- **Database statistics** endpoint
- **Health check** endpoints
- **Comprehensive error handling**
- **Interactive API documentation** via Swagger UI

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have a `.env` file with database configuration:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

## Running the Server

```bash
# Development mode (with auto-reload)
python run_server.py

# Or using uvicorn directly
uvicorn run_server:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- **Interactive API docs (Swagger UI)**: `http://localhost:8000/docs`
- **Alternative API docs (ReDoc)**: `http://localhost:8000/redoc`
- **OpenAPI schema**: `http://localhost:8000/openapi.json`

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health check with database connection test

### Audio-Transcript Pairs (Primary Operations)
- `POST /pairs/` - Create a new audio-transcript pair with file upload
- `GET /pairs/{key_name}` - Get pair by key name and variant
- `GET /pairs/` - List pairs with pagination and filtering
- `PUT /pairs/{key_name}` - Update pair with optional new audio file
- `DELETE /pairs/{key_name}` - Delete pair and associated files

### Model Audio Generation
- `POST /generate-audio/` - Generate model audio based on transcript

### Files
- `POST /files/` - Create a new file record
- `GET /files/{file_id}` - Get file by ID
- `GET /files/{file_id}/download` - Download file
- `GET /files/` - List files with pagination and filtering
- `PUT /files/{file_id}` - Update file record
- `DELETE /files/{file_id}` - Delete file record

### Transcripts
- `POST /transcripts/` - Create a new transcript
- `GET /transcripts/{transcript_id}` - Get transcript by ID
- `GET /transcripts/by-key/{key_name}` - Get transcript by key name
- `GET /transcripts/` - List transcripts with pagination and filtering
- `PUT /transcripts/{transcript_id}` - Update transcript
- `DELETE /transcripts/{transcript_id}` - Delete transcript

### Audio
- `POST /audio/` - Create a new audio record
- `GET /audio/{audio_id}` - Get audio record by ID
- `GET /audio/by-key/{key_name}` - Get audio records by key name
- `GET /audio/` - List audio records with pagination and filtering
- `PUT /audio/{audio_id}` - Update audio record
- `DELETE /audio/{audio_id}` - Delete audio record

### Statistics
- `GET /stats/` - Get database statistics and counts

## Example Usage

### Create an Audio-Transcript Pair (Recommended)
```bash
curl -X POST "http://localhost:8000/pairs/" \
  -F "key_name=000001" \
  -F "language=vi" \
  -F "text=Xin chào, đây là một đoạn ghi âm mẫu." \
  -F "audio_variant=original" \
  -F "sample_rate=22050" \
  -F "channels=1" \
  -F "audio_file=@path/to/audio.wav"
```

### Update an Audio-Transcript Pair
```bash
curl -X PUT "http://localhost:8000/pairs/000001?variant=original" \
  -F "text=Updated transcript text" \
  -F "sample_rate=44100" \
  -F "audio_file=@path/to/new_audio.wav"
```

### Get an Audio-Transcript Pair
```bash
curl "http://localhost:8000/pairs/000001?variant=original&model_name="
```

### List All Pairs
```bash
curl "http://localhost:8000/pairs/?limit=10&offset=0&variant=original"
```

### Generate Model Audio from Transcript
```bash
curl -X POST "http://localhost:8000/generate-audio/" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_key": "000001",
    "model_name": "vietnamese_tts_v1",
    "target_sample_rate": 22050,
    "target_channels": 1
  }'
```

### Download a File
```bash
curl "http://localhost:8000/files/1/download" -o downloaded_file.wav
```

### Get Database Statistics
```bash
curl "http://localhost:8000/stats/"
```

### Individual Record Operations (Legacy Support)

#### Create a File Record
```bash
curl -X POST "http://localhost:8000/files/" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "audio",
    "relative_path": "dataset/audio/000001/audio.wav",
    "file_name": "audio.wav",
    "file_ext": "wav",
    "media_type": "audio/wav",
    "size_bytes": 1024000,
    "sha256": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890"
  }'
```

#### Create a Transcript
```bash
curl -X POST "http://localhost:8000/transcripts/" \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "000001",
    "language": "vi",
    "text": "Xin chào, đây là một đoạn ghi âm mẫu.",
    "file_id": 1
  }'
```

## Database Schema

The API works with the following database tables:

### Files Table
- `id` (BIGSERIAL, Primary Key)
- `kind` (file_kind ENUM: 'audio', 'transcript', 'model_audio')
- `relative_path` (TEXT, Unique)
- `file_name` (TEXT)
- `file_ext` (TEXT)
- `media_type` (TEXT)
- `size_bytes` (BIGINT)
- `sha256` (CHAR(64), Unique)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

### Transcripts Table
- `id` (BIGSERIAL, Primary Key)
- `key_name` (TEXT, Unique)
- `language` (TEXT)
- `text` (TEXT)
- `file_id` (BIGINT, Foreign Key to files.id)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

### Audio Table
- `id` (BIGSERIAL, Primary Key)
- `key_name` (TEXT)
- `variant` (audio_variant ENUM: 'original', 'generated')
- `model_name` (TEXT)
- `file_id` (BIGINT, Foreign Key to files.id)
- `sample_rate` (INTEGER)
- `channels` (INTEGER)
- `duration_seconds` (DOUBLE PRECISION)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

## Error Handling

The API provides comprehensive error handling with appropriate HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors, constraint violations)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable (database connection issues)

Error responses include detailed error messages and optional error codes for client-side handling.