from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# Enums for database types
FileKind = Literal['audio', 'transcript', 'model_audio']
AudioVariant = Literal['original', 'generated']


# Base models for database records
class FileBase(BaseModel):
    kind: FileKind
    relative_path: str
    file_name: str
    file_ext: str
    media_type: Optional[str] = None
    size_bytes: int
    sha256: str = Field(..., min_length=64, max_length=64)


class FileCreate(FileBase):
    pass


class FileUpdate(BaseModel):
    kind: Optional[FileKind] = None
    relative_path: Optional[str] = None
    file_name: Optional[str] = None
    file_ext: Optional[str] = None
    media_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = Field(None, min_length=64, max_length=64)


class File(FileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Transcript models
class TranscriptBase(BaseModel):
    key_name: str
    language: Optional[str] = None
    text: str
    file_id: int


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptUpdate(BaseModel):
    key_name: Optional[str] = None
    language: Optional[str] = None
    text: Optional[str] = None
    file_id: Optional[int] = None


class Transcript(TranscriptBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Audio models
class AudioBase(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    key_name: str
    variant: AudioVariant
    model_name: str = ""
    file_id: int
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    duration_seconds: Optional[float] = None


class AudioCreate(AudioBase):
    pass


class AudioUpdate(BaseModel):
    key_name: Optional[str] = None
    variant: Optional[AudioVariant] = None
    model_name: Optional[str] = None
    file_id: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    duration_seconds: Optional[float] = None


class Audio(AudioBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Response models
class FileListResponse(BaseModel):
    files: list[File]
    total: int
    offset: int
    limit: int


class TranscriptListResponse(BaseModel):
    transcripts: list[Transcript]
    total: int
    offset: int
    limit: int


class AudioListResponse(BaseModel):
    audio: list[Audio]
    total: int
    offset: int
    limit: int


# Audio-Transcript Pair models
class AudioTranscriptPairBase(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    key_name: str
    language: Optional[str] = None
    text: str
    audio_variant: AudioVariant = "original"
    model_name: str = ""
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    duration_seconds: Optional[float] = None


class AudioTranscriptPairCreate(AudioTranscriptPairBase):
    pass


class AudioTranscriptPairUpdate(BaseModel):
    key_name: Optional[str] = None
    language: Optional[str] = None
    text: Optional[str] = None
    audio_variant: Optional[AudioVariant] = None
    model_name: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    duration_seconds: Optional[float] = None


class AudioTranscriptPair(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}
    
    key_name: str
    language: Optional[str]
    text: str
    audio_id: int
    transcript_id: int
    audio_file_id: int
    transcript_file_id: int
    variant: AudioVariant
    model_name: str
    sample_rate: Optional[int]
    channels: Optional[int]
    duration_seconds: Optional[float]
    audio_created_at: datetime
    transcript_created_at: datetime


class AudioTranscriptBundle(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}
    
    key_name: str
    language: Optional[str]
    text: str
    transcript_id: int
    transcript_file_id: int
    transcript_created_at: datetime
    audios: list[Audio]


# Model Audio Generation Request
class ModelAudioGenerationRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    transcript_key: str
    model_name: str
    target_sample_rate: Optional[int] = 22050
    target_channels: Optional[int] = 1


class ModelAudioGenerationResponse(BaseModel):
    success: bool
    message: str
    audio_id: Optional[int] = None
    file_id: Optional[int] = None
    file_path: Optional[str] = None


# File Upload models
class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: int
    file_path: str
    sha256: str


# Error response model
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None