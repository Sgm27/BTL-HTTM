#!/usr/bin/env python3
"""
FastAPI Backend Server for Audio Dataset Management

This server provides CRUD operations for managing files, transcripts, and audio records
in the database schema defined by ingest_to_db.py.
"""

from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File as FastAPIFile, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from pathlib import Path

from utils.database import db_manager
from utils.file_storage import file_storage
from utils.models import (
    File, FileCreate, FileUpdate, FileListResponse,
    Transcript, TranscriptCreate, TranscriptUpdate, TranscriptListResponse,
    Audio, AudioCreate, AudioUpdate, AudioListResponse,
    AudioTranscriptPair, AudioTranscriptPairCreate, AudioTranscriptPairUpdate,
    AudioTranscriptBundle,
    ModelAudioGenerationRequest, ModelAudioGenerationResponse,
    FileUploadResponse, ErrorResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Audio Dataset Management API",
    description="CRUD API for managing audio files, transcripts, and metadata",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}
    )


# Serve the HTML interface
@app.get("/", response_class=HTMLResponse, tags=["Web Interface"])
async def serve_web_interface():
    """Serve the web interface"""
    html_file = Path(__file__).parent / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    else:
        return HTMLResponse("<h1>Web interface not found</h1>", status_code=404)

# API Health check endpoint
@app.get("/api/", tags=["Health"])
async def root():
    """API health check endpoint"""
    return {"message": "Audio Dataset Management API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    try:
        # Test database connection
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )


# Files endpoints
@app.post("/files/", response_model=File, tags=["Files"])
async def create_file(file_data: FileCreate):
    """Create a new file record"""
    try:
        return db_manager.create_file(file_data)
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create file: {str(e)}")


@app.get("/files/{file_id}", response_model=File, tags=["Files"])
async def get_file(file_id: int):
    """Get a file by ID"""
    file = db_manager.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@app.get("/files/", response_model=FileListResponse, tags=["Files"])
async def get_files(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    kind: Optional[str] = Query(None, description="Filter by file kind")
):
    """Get files with pagination and optional filtering"""
    try:
        files, total = db_manager.get_files(offset=offset, limit=limit, kind=kind)
        return FileListResponse(
            files=files,
            total=total,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get files: {str(e)}")


@app.put("/files/{file_id}", response_model=File, tags=["Files"])
async def update_file(file_id: int, file_data: FileUpdate):
    """Update a file record"""
    try:
        updated_file = db_manager.update_file(file_id, file_data)
        if not updated_file:
            raise HTTPException(status_code=404, detail="File not found")
        return updated_file
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update file: {str(e)}")


@app.delete("/files/{file_id}", tags=["Files"])
async def delete_file(file_id: int):
    """Delete a file record"""
    try:
        deleted = db_manager.delete_file(file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found")
        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to delete file: {str(e)}")


# Transcripts endpoints
@app.post("/transcripts/", response_model=Transcript, tags=["Transcripts"])
async def create_transcript(transcript_data: TranscriptCreate):
    """Create a new transcript record"""
    try:
        return db_manager.create_transcript(transcript_data)
    except Exception as e:
        logger.error(f"Error creating transcript: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create transcript: {str(e)}")


@app.get("/transcripts/{transcript_id}", response_model=Transcript, tags=["Transcripts"])
async def get_transcript(transcript_id: int):
    """Get a transcript by ID"""
    transcript = db_manager.get_transcript(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@app.get("/transcripts/by-key/{key_name}", response_model=Transcript, tags=["Transcripts"])
async def get_transcript_by_key(key_name: str):
    """Get a transcript by key_name"""
    transcript = db_manager.get_transcript_by_key(key_name)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@app.get("/transcripts/", response_model=TranscriptListResponse, tags=["Transcripts"])
async def get_transcripts(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    language: Optional[str] = Query(None, description="Filter by language")
):
    """Get transcripts with pagination and optional filtering"""
    try:
        transcripts, total = db_manager.get_transcripts(offset=offset, limit=limit, language=language)
        return TranscriptListResponse(
            transcripts=transcripts,
            total=total,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting transcripts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcripts: {str(e)}")


@app.put("/transcripts/{transcript_id}", response_model=Transcript, tags=["Transcripts"])
async def update_transcript(transcript_id: int, transcript_data: TranscriptUpdate):
    """Update a transcript record"""
    try:
        updated_transcript = db_manager.update_transcript(transcript_id, transcript_data)
        if not updated_transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        return updated_transcript
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transcript: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update transcript: {str(e)}")


@app.delete("/transcripts/{transcript_id}", tags=["Transcripts"])
async def delete_transcript(transcript_id: int):
    """Delete a transcript record"""
    try:
        deleted = db_manager.delete_transcript(transcript_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Transcript not found")
        return {"message": "Transcript deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transcript: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to delete transcript: {str(e)}")


# Audio endpoints
@app.post("/audio/", response_model=Audio, tags=["Audio"])
async def create_audio(audio_data: AudioCreate):
    """Create a new audio record"""
    try:
        return db_manager.create_audio(audio_data)
    except Exception as e:
        logger.error(f"Error creating audio: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create audio: {str(e)}")


@app.get("/audio/{audio_id}", response_model=Audio, tags=["Audio"])
async def get_audio(audio_id: int):
    """Get an audio record by ID"""
    audio = db_manager.get_audio(audio_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Audio record not found")
    return audio


@app.get("/audio/by-key/{key_name}", response_model=List[Audio], tags=["Audio"])
async def get_audio_by_key(
    key_name: str,
    variant: Optional[str] = Query(None, description="Filter by audio variant"),
    model_name: Optional[str] = Query(None, description="Filter by model name")
):
    """Get audio records by key_name and optional filters"""
    try:
        audio_list = db_manager.get_audio_by_key(key_name, variant, model_name)
        return audio_list
    except Exception as e:
        logger.error(f"Error getting audio by key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audio: {str(e)}")


@app.get("/audio/", response_model=AudioListResponse, tags=["Audio"])
async def get_audio_list(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    variant: Optional[str] = Query(None, description="Filter by audio variant")
):
    """Get audio records with pagination and optional filtering"""
    try:
        audio_list, total = db_manager.get_audio_list(offset=offset, limit=limit, variant=variant)
        return AudioListResponse(
            audio=audio_list,
            total=total,
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting audio list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audio list: {str(e)}")


@app.put("/audio/{audio_id}", response_model=Audio, tags=["Audio"])
async def update_audio(audio_id: int, audio_data: AudioUpdate):
    """Update an audio record"""
    try:
        updated_audio = db_manager.update_audio(audio_id, audio_data)
        if not updated_audio:
            raise HTTPException(status_code=404, detail="Audio record not found")
        return updated_audio
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating audio: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update audio: {str(e)}")


@app.delete("/audio/{audio_id}", tags=["Audio"])
async def delete_audio(audio_id: int):
    """Delete an audio record"""
    try:
        deleted = db_manager.delete_audio(audio_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Audio record not found")
        return {"message": "Audio record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting audio: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to delete audio: {str(e)}")


# Audio-Transcript Pair endpoints
@app.post("/pairs/", response_model=AudioTranscriptPair, tags=["Audio-Transcript Pairs"])
async def create_audio_transcript_pair(
    key_name: str = Form(...),
    language: Optional[str] = Form(None),
    text: str = Form(...),
    audio_variant: str = Form("original"),
    model_name: str = Form(""),
    sample_rate: Optional[int] = Form(None),
    channels: Optional[int] = Form(None),
    duration_seconds: Optional[float] = Form(None),
    audio_file: UploadFile = FastAPIFile(...),
):
    """Create a new audio-transcript pair with file upload"""
    try:
        # Save audio file
        audio_file_data, audio_path = await file_storage.save_audio_file(
            audio_file, key_name, audio_variant, model_name
        )
        
        # Save transcript file
        transcript_file_data, transcript_path = await file_storage.save_transcript_file(
            text, key_name
        )
        
        # Create pair data
        pair_data = AudioTranscriptPairCreate(
            key_name=key_name,
            language=language,
            text=text,
            audio_variant=audio_variant,
            model_name=model_name,
            sample_rate=sample_rate,
            channels=channels,
            duration_seconds=duration_seconds
        )
        
        # Create database records
        pair = db_manager.create_audio_transcript_pair(pair_data, audio_file_data, transcript_file_data)
        return pair
        
    except Exception as e:
        logger.error(f"Error creating audio-transcript pair: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to create pair: {str(e)}")


@app.get("/pairs/{key_name}", response_model=AudioTranscriptPair, tags=["Audio-Transcript Pairs"])
async def get_audio_transcript_pair(
    key_name: str,
    variant: str = Query("original", description="Audio variant"),
    model_name: str = Query("", description="Model name for generated audio")
):
    """Get an audio-transcript pair by key name"""
    pair = db_manager.get_audio_transcript_pair(key_name, variant, model_name)
    if not pair:
        raise HTTPException(status_code=404, detail="Audio-transcript pair not found")
    return pair


@app.get("/pairs/", response_model=List[AudioTranscriptPair], tags=["Audio-Transcript Pairs"])
async def get_audio_transcript_pairs(
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    variant: Optional[str] = Query(None, description="Filter by audio variant")
):
    """Get audio-transcript pairs with pagination"""
    try:
        pairs, total = db_manager.get_audio_transcript_pairs(offset=offset, limit=limit, variant=variant)
        return pairs
    except Exception as e:
        logger.error(f"Error getting pairs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pairs: {str(e)}")


@app.get("/pairs/bundle/{key_name}", response_model=AudioTranscriptBundle, tags=["Audio-Transcript Pairs"])
async def get_audio_transcript_bundle(key_name: str):
    """Get a transcript and all of its audios by key name"""
    try:
        bundle = db_manager.get_audio_transcript_bundle(key_name)
        if not bundle:
            raise HTTPException(status_code=404, detail="Transcript not found")
        return bundle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bundle for key {key_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bundle: {str(e)}")


@app.put("/pairs/{key_name}", response_model=AudioTranscriptPair, tags=["Audio-Transcript Pairs"])
async def update_audio_transcript_pair(
    key_name: str,
    variant: str = Query("original", description="Audio variant"),
    model_name: str = Query("", description="Model name for generated audio"),
    new_key_name: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    new_variant: Optional[str] = Form(None),
    new_model_name: Optional[str] = Form(None),
    sample_rate: Optional[int] = Form(None),
    channels: Optional[int] = Form(None),
    duration_seconds: Optional[float] = Form(None),
    audio_file: Optional[UploadFile] = FastAPIFile(None),
):
    """Update an audio-transcript pair with optional new audio file"""
    try:
        # If new audio file is provided, save it
        if audio_file:
            target_key = new_key_name or key_name
            target_variant = new_variant or variant
            target_model = new_model_name or model_name
            
            audio_file_data, audio_path = await file_storage.save_audio_file(
                audio_file, target_key, target_variant, target_model
            )
            
            # Update the file record in database
            # This would require additional logic to handle file updates
            logger.info(f"New audio file saved to {audio_path}")
        
        # Update transcript file if text changed
        if text:
            target_key = new_key_name or key_name
            transcript_file_data, transcript_path = await file_storage.save_transcript_file(
                text, target_key
            )
            logger.info(f"Transcript updated at {transcript_path}")
        
        # Update pair data
        pair_data = AudioTranscriptPairUpdate(
            key_name=new_key_name,
            language=language,
            text=text,
            audio_variant=new_variant,
            model_name=new_model_name,
            sample_rate=sample_rate,
            channels=channels,
            duration_seconds=duration_seconds
        )
        
        updated_pair = db_manager.update_audio_transcript_pair(key_name, pair_data, variant, model_name)
        if not updated_pair:
            raise HTTPException(status_code=404, detail="Audio-transcript pair not found")
        return updated_pair
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pair: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update pair: {str(e)}")


@app.delete("/pairs/{key_name}", tags=["Audio-Transcript Pairs"])
async def delete_audio_transcript_pair(
    key_name: str,
    variant: str = Query("original", description="Audio variant"),
    model_name: str = Query("", description="Model name for generated audio")
):
    """Delete an audio-transcript pair and associated files"""
    try:
        # Get the pair info to find file paths before deletion
        pair = db_manager.get_audio_transcript_pair(key_name, variant, model_name)
        if not pair:
            raise HTTPException(status_code=404, detail="Audio-transcript pair not found")
        
        # Delete from database
        deleted = db_manager.delete_audio_transcript_pair(key_name, variant, model_name)
        if not deleted:
            raise HTTPException(status_code=404, detail="Audio-transcript pair not found")
        
        # Clean up files
        audio_path = file_storage.get_audio_file_path(key_name, variant, model_name)
        transcript_path = file_storage.get_transcript_file_path(key_name)
        
        file_storage.delete_file(audio_path)
        if variant == "original":  # Only delete transcript for original audio
            file_storage.delete_file(transcript_path)
        
        return {"message": "Audio-transcript pair deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pair: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to delete pair: {str(e)}")


# File Download endpoints
@app.get("/files/{file_id}/download", tags=["Files"])
async def download_file(file_id: int):
    """Download a file by ID"""
    try:
        file_record = db_manager.get_file(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Import PROJECT_ROOT from ingest_to_db
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent))
        from ingest_to_db import PROJECT_ROOT
        
        file_path = PROJECT_ROOT / file_record.relative_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=str(file_path),
            filename=file_record.file_name,
            media_type=file_record.media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


# Model Audio Generation endpoint
@app.post("/generate-audio/", response_model=ModelAudioGenerationResponse, tags=["Model Audio Generation"])
async def generate_model_audio(request: ModelAudioGenerationRequest):
    """Generate model audio based on transcript text"""
    try:
        # Get the transcript
        transcript = db_manager.get_transcript_by_key(request.transcript_key)
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # This is a placeholder for actual audio generation
        # In a real implementation, you would:
        # 1. Load the specified TTS model
        # 2. Generate audio from the transcript text
        # 3. Save the generated audio file
        # 4. Create database records
        
        logger.info(f"Audio generation requested for transcript '{request.transcript_key}' using model '{request.model_name}'")
        
        # For now, return a placeholder response
        return ModelAudioGenerationResponse(
            success=False,
            message=f"Audio generation not implemented yet. Would generate audio for transcript '{request.transcript_key}' using model '{request.model_name}'",
            audio_id=None,
            file_id=None,
            file_path=None
        )
        
        # TODO: Implement actual audio generation logic here
        # Example implementation structure:
        """
        # Load TTS model
        model = load_tts_model(request.model_name)
        
        # Generate audio
        audio_data = model.synthesize(
            text=transcript.text,
            sample_rate=request.target_sample_rate,
            channels=request.target_channels
        )
        
        # Save generated audio file
        audio_path = file_storage.get_audio_file_path(
            request.transcript_key, 
            "generated", 
            request.model_name
        )
        save_audio_to_file(audio_data, audio_path)
        
        # Create file record
        audio_file_data = gather_file_record(audio_path, "model_audio")
        file_record = db_manager.create_file(audio_file_data)
        
        # Create audio record
        audio_data = AudioCreate(
            key_name=request.transcript_key,
            variant="generated",
            model_name=request.model_name,
            file_id=file_record.id,
            sample_rate=request.target_sample_rate,
            channels=request.target_channels,
            duration_seconds=calculate_duration(audio_data)
        )
        audio_record = db_manager.create_audio(audio_data)
        
        return ModelAudioGenerationResponse(
            success=True,
            message="Audio generated successfully",
            audio_id=audio_record.id,
            file_id=file_record.id,
            file_path=str(audio_path)
        )
        """
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating model audio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")


# Statistics endpoints
@app.get("/stats/", tags=["Statistics"])
async def get_database_stats():
    """Get database statistics"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Count files by kind
                cur.execute("SELECT kind, COUNT(*) as count FROM files GROUP BY kind ORDER BY kind")
                files_by_kind = dict(cur.fetchall())
                
                # Count transcripts by language
                cur.execute("SELECT language, COUNT(*) as count FROM transcripts GROUP BY language ORDER BY language")
                transcripts_by_language = dict(cur.fetchall())
                
                # Count audio by variant
                cur.execute("SELECT variant, COUNT(*) as count FROM audio GROUP BY variant ORDER BY variant")
                audio_by_variant = dict(cur.fetchall())
                
                # Total counts
                cur.execute("SELECT COUNT(*) FROM files")
                total_files = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM transcripts")
                total_transcripts = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM audio")
                total_audio = cur.fetchone()[0]
                
                return {
                    "total_files": total_files,
                    "total_transcripts": total_transcripts,
                    "total_audio": total_audio,
                    "files_by_kind": files_by_kind,
                    "transcripts_by_language": transcripts_by_language,
                    "audio_by_variant": audio_by_variant
                }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "run_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )