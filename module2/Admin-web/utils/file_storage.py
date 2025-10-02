import hashlib
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from fastapi import UploadFile

# Import from parent directory
import sys
sys.path.append(str(Path(__file__).parent.parent))
from ingest_to_db import PROJECT_ROOT, DATASET_DIR, sha256sum, infer_media_type, gather_file_record

from .models import FileCreate, FileUploadResponse


class FileStorageManager:
    def __init__(self, base_path: Path = DATASET_DIR):
        self.base_path = base_path
        self.audio_path = base_path / "audio"
        self.transcript_path = base_path / "transcripts"
        self.model_path = base_path / "models"
        
        # Ensure directories exist
        self.audio_path.mkdir(parents=True, exist_ok=True)
        self.transcript_path.mkdir(parents=True, exist_ok=True)
        self.model_path.mkdir(parents=True, exist_ok=True)
    
    async def save_uploaded_file(self, file: UploadFile, target_path: Path) -> Tuple[str, int]:
        """Save an uploaded file and return its SHA256 hash and size"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save file
        with open(target_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Calculate hash and size
        file_hash = sha256sum(target_path)
        file_size = target_path.stat().st_size
        
        return file_hash, file_size
    
    def get_audio_file_path(self, key_name: str, variant: str = "original", model_name: str = "", file_ext: str = "wav") -> Path:
        """Get the path where an audio file should be stored"""
        if variant == "original":
            return self.audio_path / key_name / f"audio.{file_ext}"
        else:  # generated
            return self.model_path / model_name / f"{key_name}.{file_ext}"
    
    def get_transcript_file_path(self, key_name: str, file_ext: str = "txt") -> Path:
        """Get the path where a transcript file should be stored"""
        return self.transcript_path / f"{key_name}.{file_ext}"
    
    async def save_audio_file(self, file: UploadFile, key_name: str, variant: str = "original", model_name: str = "") -> Tuple[FileCreate, Path]:
        """Save an audio file and return FileCreate data"""
        file_ext = file.filename.split('.')[-1].lower() if file.filename else "wav"
        target_path = self.get_audio_file_path(key_name, variant, model_name, file_ext)
        
        file_hash, file_size = await self.save_uploaded_file(file, target_path)
        
        rel_path = target_path.relative_to(PROJECT_ROOT).as_posix()
        media_type = infer_media_type(target_path)
        
        file_data = FileCreate(
            kind="audio" if variant == "original" else "model_audio",
            relative_path=rel_path,
            file_name=target_path.name,
            file_ext=file_ext,
            media_type=media_type,
            size_bytes=file_size,
            sha256=file_hash
        )
        
        return file_data, target_path
    
    async def save_transcript_file(self, content: str, key_name: str) -> Tuple[FileCreate, Path]:
        """Save a transcript file and return FileCreate data"""
        target_path = self.get_transcript_file_path(key_name)
        
        # Write transcript content
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        
        # Calculate hash and size
        file_hash = sha256sum(target_path)
        file_size = target_path.stat().st_size
        
        rel_path = target_path.relative_to(PROJECT_ROOT).as_posix()
        
        file_data = FileCreate(
            kind="transcript",
            relative_path=rel_path,
            file_name=target_path.name,
            file_ext="txt",
            media_type="text/plain",
            size_bytes=file_size,
            sha256=file_hash
        )
        
        return file_data, target_path
    
    def delete_file(self, file_path: Path) -> bool:
        """Delete a file from storage"""
        try:
            if file_path.exists():
                file_path.unlink()
                # Remove empty parent directories
                try:
                    file_path.parent.rmdir()
                except OSError:
                    pass  # Directory not empty, which is fine
                return True
            return False
        except Exception:
            return False
    
    def get_file_info(self, file_path: Path) -> Optional[dict]:
        """Get information about a file"""
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "media_type": infer_media_type(file_path)
        }


# Global file storage manager instance
file_storage = FileStorageManager()