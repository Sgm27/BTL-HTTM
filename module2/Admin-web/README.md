# 🎵 Audio Dataset Management System

A complete web-based system for managing audio-transcript pairs with automatic file handling and TTS model integration.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- PostgreSQL database
- Git

### 2. Installation

```bash
# Clone the repository (if needed)
cd Admin-web/

# Install dependencies
pip install -r requirements.txt

# Or use the startup script (recommended)
./start_server.sh
```

### 3. Database Configuration

Create a `.env` file in the `Admin-web/` directory:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

### 4. Start the Server

**Option A: Using the startup script (recommended)**
```bash
./start_server.sh
```

**Option B: Manual start**
```bash
python run_server.py
```

### 5. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## 🌟 Features

### Web Interface
- **📊 View Data**: Browse all audio-transcript pairs with filtering
- **⬆️ Upload**: Create new pairs with drag-and-drop file upload
- **🤖 Generate Audio**: Generate model audio from existing transcripts
- **📈 Statistics**: View database statistics and analytics
- **📥 Download**: Download audio and transcript files
- **🗑️ Delete**: Remove pairs and associated files

### API Features
- **Pair-based Operations**: Audio and transcript are managed as pairs
- **Automatic File Storage**: Files are automatically saved to organized directories
- **CRUD Operations**: Complete Create, Read, Update, Delete for all entities
- **File Downloads**: Direct file download endpoints
- **Statistics**: Database analytics and counts
- **Model Audio Generation**: Framework for TTS model integration

## 📁 Project Structure

```
Admin-web/
├── run_server.py           # Main FastAPI server
├── index.html              # Web interface
├── start_server.sh         # Startup script
├── test_api.py            # API testing script
├── requirements.txt        # Python dependencies
├── API_README.md          # Detailed API documentation
├── ingest_to_db.py        # Database ingestion (from parent)
└── utils/
    ├── __init__.py
    ├── models.py          # Pydantic data models
    ├── database.py        # Database operations
    └── file_storage.py    # File handling utilities
```

## 🔧 Usage Examples

### Web Interface Usage

1. **Upload a New Pair**:
   - Go to "Upload" tab
   - Fill in key name and transcript text
   - Select language and audio settings
   - Drag & drop or select audio file
   - Click "Upload Pair"

2. **View and Manage Data**:
   - Go to "View Data" tab
   - Browse pairs with filtering options
   - Download audio/transcript files
   - Delete unwanted pairs

3. **Generate Model Audio**:
   - Go to "Generate Audio" tab
   - Enter transcript key and model name
   - Set target audio parameters
   - Submit generation request

### API Usage

```bash
# Upload a new pair
curl -X POST "http://localhost:8000/pairs/" \
  -F "key_name=sample_001" \
  -F "language=vi" \
  -F "text=Xin chào, đây là bản ghi âm mẫu." \
  -F "audio_variant=original" \
  -F "sample_rate=22050" \
  -F "audio_file=@audio.wav"

# Get a specific pair
curl "http://localhost:8000/pairs/sample_001?variant=original"

# List all pairs
curl "http://localhost:8000/pairs/"

# Download an audio file
curl "http://localhost:8000/files/1/download" -o audio.wav

# Get statistics
curl "http://localhost:8000/stats/"

# Generate model audio
curl -X POST "http://localhost:8000/generate-audio/" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_key": "sample_001",
    "model_name": "vietnamese_tts_v1",
    "target_sample_rate": 22050,
    "target_channels": 1
  }'
```

## 📊 Database Schema

The system uses three main tables:

### Files Table
- Stores metadata for all files (audio, transcripts, model audio)
- Unique constraints on SHA256 hash and file path
- Automatic timestamps

### Transcripts Table
- Stores transcript text and metadata  
- Links to transcript files via foreign key
- Unique constraint on key_name

### Audio Table
- Stores audio metadata and properties
- Links to audio files via foreign key
- Supports original and generated variants
- Tracks model information for generated audio

## 🔄 File Organization

Files are automatically organized in the following structure:

```
dataset/
├── audio/                 # Original audio files
│   └── {key_name}/
│       └── audio.wav
├── transcripts/           # Transcript files
│   └── {key_name}.txt
└── models/               # Generated audio files
    └── {model_name}/
        └── {key_name}.wav
```

## 🛠️ Development

### Running Tests
```bash
# Test API endpoints
python test_api.py

# Or test manually with curl
curl "http://localhost:8000/health"
```

### Adding New Models
To integrate new TTS models, modify the `generate_model_audio` endpoint in `run_server.py`:

1. Load your TTS model
2. Generate audio from transcript text
3. Save the generated audio file
4. Create database records

### Customization
- **File Storage**: Modify `utils/file_storage.py` for different storage backends
- **Database**: Extend `utils/database.py` for additional operations
- **Web Interface**: Customize `index.html` for different UI requirements

## 🔒 Security Notes

- **CORS**: Currently allows all origins (development mode)
- **File Upload**: Validates file types and sizes
- **Database**: Uses parameterized queries to prevent SQL injection
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

## 📝 TODO / Future Enhancements

- [ ] User authentication and authorization
- [ ] File size limits and validation
- [ ] Audio format conversion
- [ ] Batch operations
- [ ] Audio playback in web interface
- [ ] Advanced search and filtering
- [ ] Export/import functionality
- [ ] Real-time TTS model integration
- [ ] Audio waveform visualization

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Check `.env` file configuration
   - Ensure PostgreSQL is running
   - Verify database credentials

2. **File Upload Error**:
   - Check file permissions in dataset directory
   - Ensure adequate disk space
   - Verify file format is supported

3. **Port Already in Use**:
   - Change port in `run_server.py`: `uvicorn.run(..., port=8001)`
   - Or kill existing process: `pkill -f "run_server.py"`

4. **CORS Issues**:
   - Check browser console for CORS errors
   - Ensure server is running on correct host/port

### Logs and Debugging

- Server logs are displayed in terminal
- Check browser developer tools for frontend issues
- Use API documentation at `/docs` for endpoint testing

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review API documentation at `/docs`
3. Check server logs for error messages
4. Test with `test_api.py` script

---

**Happy audio dataset management! 🎵**