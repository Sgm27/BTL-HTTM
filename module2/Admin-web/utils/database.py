import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from .models import (
    File, FileCreate, FileUpdate,
    Transcript, TranscriptCreate, TranscriptUpdate,
    Audio, AudioCreate, AudioUpdate,
    AudioTranscriptPair, AudioTranscriptPairCreate, AudioTranscriptPairUpdate,
    AudioTranscriptBundle
)

# Import database functions from parent directory
sys.path.append(str(Path(__file__).parent.parent))
from ingest_to_db import load_env, get_db_conn, ensure_schema

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class DatabaseManager:
    def __init__(self):
        self.env = load_env(ENV_PATH)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = get_db_conn(self.env)
            ensure_schema(conn)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    # Files CRUD operations
    def create_file(self, file_data: FileCreate) -> File:
        """Create a new file record"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO files (kind, relative_path, file_name, file_ext, media_type, size_bytes, sha256)
                    VALUES (%(kind)s, %(relative_path)s, %(file_name)s, %(file_ext)s, %(media_type)s, %(size_bytes)s, %(sha256)s)
                    RETURNING *;
                    """,
                    file_data.model_dump()
                )
                result = cur.fetchone()
                conn.commit()
                return File(**result)
    
    def get_file(self, file_id: int) -> Optional[File]:
        """Get a file by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM files WHERE id = %s;", (file_id,))
                result = cur.fetchone()
                return File(**result) if result else None
    
    def get_files(self, offset: int = 0, limit: int = 100, kind: Optional[str] = None) -> Tuple[List[File], int]:
        """Get files with pagination and optional filtering by kind"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Count total records
                count_query = "SELECT COUNT(*) FROM files"
                count_params = []
                if kind:
                    count_query += " WHERE kind = %s"
                    count_params.append(kind)
                
                cur.execute(count_query, count_params)
                total = cur.fetchone()['count']
                
                # Get paginated results
                query = "SELECT * FROM files"
                params = []
                if kind:
                    query += " WHERE kind = %s"
                    params.append(kind)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = cur.fetchall()
                files = [File(**row) for row in results]
                return files, total
    
    def update_file(self, file_id: int, file_data: FileUpdate) -> Optional[File]:
        """Update a file record"""
        update_data = {k: v for k, v in file_data.model_dump().items() if v is not None}
        if not update_data:
            return self.get_file(file_id)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                set_clause = ", ".join([f"{k} = %({k})s" for k in update_data.keys()])
                update_data['id'] = file_id
                update_data['updated_at'] = 'NOW()'
                
                cur.execute(
                    f"""
                    UPDATE files 
                    SET {set_clause}, updated_at = NOW()
                    WHERE id = %(id)s
                    RETURNING *;
                    """,
                    update_data
                )
                result = cur.fetchone()
                conn.commit()
                return File(**result) if result else None
    
    def delete_file(self, file_id: int) -> bool:
        """Delete a file record"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM files WHERE id = %s;", (file_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
    
    # Transcripts CRUD operations
    def create_transcript(self, transcript_data: TranscriptCreate) -> Transcript:
        """Create a new transcript record"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO transcripts (key_name, language, text, file_id)
                    VALUES (%(key_name)s, %(language)s, %(text)s, %(file_id)s)
                    RETURNING *;
                    """,
                    transcript_data.model_dump()
                )
                result = cur.fetchone()
                conn.commit()
                return Transcript(**result)
    
    def get_transcript(self, transcript_id: int) -> Optional[Transcript]:
        """Get a transcript by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM transcripts WHERE id = %s;", (transcript_id,))
                result = cur.fetchone()
                return Transcript(**result) if result else None
    
    def get_transcript_by_key(self, key_name: str) -> Optional[Transcript]:
        """Get a transcript by key_name"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM transcripts WHERE key_name = %s;", (key_name,))
                result = cur.fetchone()
                return Transcript(**result) if result else None
    
    def get_transcripts(self, offset: int = 0, limit: int = 100, language: Optional[str] = None) -> Tuple[List[Transcript], int]:
        """Get transcripts with pagination and optional filtering by language"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Count total records
                count_query = "SELECT COUNT(*) FROM transcripts"
                count_params = []
                if language:
                    count_query += " WHERE language = %s"
                    count_params.append(language)
                
                cur.execute(count_query, count_params)
                total = cur.fetchone()['count']
                
                # Get paginated results
                query = "SELECT * FROM transcripts"
                params = []
                if language:
                    query += " WHERE language = %s"
                    params.append(language)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = cur.fetchall()
                transcripts = [Transcript(**row) for row in results]
                return transcripts, total
    
    def update_transcript(self, transcript_id: int, transcript_data: TranscriptUpdate) -> Optional[Transcript]:
        """Update a transcript record"""
        update_data = {k: v for k, v in transcript_data.model_dump().items() if v is not None}
        if not update_data:
            return self.get_transcript(transcript_id)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                set_clause = ", ".join([f"{k} = %({k})s" for k in update_data.keys()])
                update_data['id'] = transcript_id
                
                cur.execute(
                    f"""
                    UPDATE transcripts 
                    SET {set_clause}, updated_at = NOW()
                    WHERE id = %(id)s
                    RETURNING *;
                    """,
                    update_data
                )
                result = cur.fetchone()
                conn.commit()
                return Transcript(**result) if result else None
    
    def delete_transcript(self, transcript_id: int) -> bool:
        """Delete a transcript record"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM transcripts WHERE id = %s;", (transcript_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
    
    # Audio CRUD operations
    def create_audio(self, audio_data: AudioCreate) -> Audio:
        """Create a new audio record"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO audio (key_name, variant, model_name, file_id, sample_rate, channels, duration_seconds)
                    VALUES (%(key_name)s, %(variant)s, %(model_name)s, %(file_id)s, %(sample_rate)s, %(channels)s, %(duration_seconds)s)
                    RETURNING *;
                    """,
                    audio_data.model_dump()
                )
                result = cur.fetchone()
                conn.commit()
                return Audio(**result)
    
    def get_audio(self, audio_id: int) -> Optional[Audio]:
        """Get an audio record by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM audio WHERE id = %s;", (audio_id,))
                result = cur.fetchone()
                return Audio(**result) if result else None
    
    def get_audio_by_key(self, key_name: str, variant: Optional[str] = None, model_name: Optional[str] = None) -> List[Audio]:
        """Get audio records by key_name and optional filters"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM audio WHERE key_name = %s"
                params = [key_name]
                
                if variant:
                    query += " AND variant = %s"
                    params.append(variant)
                
                if model_name is not None:
                    query += " AND model_name = %s"
                    params.append(model_name)
                
                cur.execute(query, params)
                results = cur.fetchall()
                return [Audio(**row) for row in results]
    
    def get_audio_list(self, offset: int = 0, limit: int = 100, variant: Optional[str] = None) -> Tuple[List[Audio], int]:
        """Get audio records with pagination and optional filtering by variant"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Count total records
                count_query = "SELECT COUNT(*) FROM audio"
                count_params = []
                if variant:
                    count_query += " WHERE variant = %s"
                    count_params.append(variant)
                
                cur.execute(count_query, count_params)
                total = cur.fetchone()['count']
                
                # Get paginated results
                query = "SELECT * FROM audio"
                params = []
                if variant:
                    query += " WHERE variant = %s"
                    params.append(variant)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = cur.fetchall()
                audio_list = [Audio(**row) for row in results]
                return audio_list, total
    
    def update_audio(self, audio_id: int, audio_data: AudioUpdate) -> Optional[Audio]:
        """Update an audio record"""
        update_data = {k: v for k, v in audio_data.model_dump().items() if v is not None}
        if not update_data:
            return self.get_audio(audio_id)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                set_clause = ", ".join([f"{k} = %({k})s" for k in update_data.keys()])
                update_data['id'] = audio_id
                
                cur.execute(
                    f"""
                    UPDATE audio 
                    SET {set_clause}, updated_at = NOW()
                    WHERE id = %(id)s
                    RETURNING *;
                    """,
                    update_data
                )
                result = cur.fetchone()
                conn.commit()
                return Audio(**result) if result else None
    
    def delete_audio(self, audio_id: int) -> bool:
        """Delete an audio record"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM audio WHERE id = %s;", (audio_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
    
    # Audio-Transcript Pair operations
    def create_audio_transcript_pair(self, pair_data: AudioTranscriptPairCreate, audio_file_data: FileCreate, transcript_file_data: FileCreate) -> AudioTranscriptPair:
        """Create a new audio-transcript pair with associated files"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Create audio file record
                cur.execute(
                    """
                    INSERT INTO files (kind, relative_path, file_name, file_ext, media_type, size_bytes, sha256)
                    VALUES (%(kind)s, %(relative_path)s, %(file_name)s, %(file_ext)s, %(media_type)s, %(size_bytes)s, %(sha256)s)
                    RETURNING *;
                    """,
                    audio_file_data.model_dump()
                )
                audio_file = cur.fetchone()
                
                # Create transcript file record
                cur.execute(
                    """
                    INSERT INTO files (kind, relative_path, file_name, file_ext, media_type, size_bytes, sha256)
                    VALUES (%(kind)s, %(relative_path)s, %(file_name)s, %(file_ext)s, %(media_type)s, %(size_bytes)s, %(sha256)s)
                    RETURNING *;
                    """,
                    transcript_file_data.model_dump()
                )
                transcript_file = cur.fetchone()
                
                # Create transcript record
                cur.execute(
                    """
                    INSERT INTO transcripts (key_name, language, text, file_id)
                    VALUES (%(key_name)s, %(language)s, %(text)s, %(file_id)s)
                    RETURNING *;
                    """,
                    {
                        'key_name': pair_data.key_name,
                        'language': pair_data.language,
                        'text': pair_data.text,
                        'file_id': transcript_file['id']
                    }
                )
                transcript = cur.fetchone()
                
                # Create audio record
                cur.execute(
                    """
                    INSERT INTO audio (key_name, variant, model_name, file_id, sample_rate, channels, duration_seconds)
                    VALUES (%(key_name)s, %(variant)s, %(model_name)s, %(file_id)s, %(sample_rate)s, %(channels)s, %(duration_seconds)s)
                    RETURNING *;
                    """,
                    {
                        'key_name': pair_data.key_name,
                        'variant': pair_data.audio_variant,
                        'model_name': pair_data.model_name,
                        'file_id': audio_file['id'],
                        'sample_rate': pair_data.sample_rate,
                        'channels': pair_data.channels,
                        'duration_seconds': pair_data.duration_seconds
                    }
                )
                audio = cur.fetchone()
                
                conn.commit()
                
                return AudioTranscriptPair(
                    key_name=pair_data.key_name,
                    language=pair_data.language,
                    text=pair_data.text,
                    audio_id=audio['id'],
                    transcript_id=transcript['id'],
                    audio_file_id=audio_file['id'],
                    transcript_file_id=transcript_file['id'],
                    variant=audio['variant'],
                    model_name=audio['model_name'],
                    sample_rate=audio['sample_rate'],
                    channels=audio['channels'],
                    duration_seconds=audio['duration_seconds'],
                    audio_created_at=audio['created_at'],
                    transcript_created_at=transcript['created_at']
                )
    
    def get_audio_transcript_pair(self, key_name: str, variant: str = "original", model_name: str = "") -> Optional[AudioTranscriptPair]:
        """Get an audio-transcript pair by key_name and variant"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        t.key_name, t.language, t.text, t.id as transcript_id, t.file_id as transcript_file_id, t.created_at as transcript_created_at,
                        a.id as audio_id, a.variant, a.model_name, a.file_id as audio_file_id, 
                        a.sample_rate, a.channels, a.duration_seconds, a.created_at as audio_created_at
                    FROM transcripts t
                    JOIN audio a ON t.key_name = a.key_name
                    WHERE t.key_name = %s AND a.variant = %s AND a.model_name = %s
                    """,
                    (key_name, variant, model_name)
                )
                result = cur.fetchone()
                if result:
                    return AudioTranscriptPair(**result)
                return None
    
    def get_audio_transcript_pairs(self, offset: int = 0, limit: int = 100, variant: Optional[str] = None) -> Tuple[List[AudioTranscriptPair], int]:
        """Get audio-transcript pairs with pagination"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Count total pairs
                count_query = """
                    SELECT COUNT(DISTINCT t.key_name) 
                    FROM transcripts t 
                    JOIN audio a ON t.key_name = a.key_name
                """
                count_params = []
                if variant:
                    count_query += " WHERE a.variant = %s"
                    count_params.append(variant)
                
                cur.execute(count_query, count_params)
                total = cur.fetchone()['count']
                
                # Get paginated pairs
                query = """
                    SELECT 
                        t.key_name, t.language, t.text, t.id as transcript_id, t.file_id as transcript_file_id, t.created_at as transcript_created_at,
                        a.id as audio_id, a.variant, a.model_name, a.file_id as audio_file_id, 
                        a.sample_rate, a.channels, a.duration_seconds, a.created_at as audio_created_at
                    FROM transcripts t
                    JOIN audio a ON t.key_name = a.key_name
                """
                params = []
                if variant:
                    query += " WHERE a.variant = %s"
                    params.append(variant)
                
                query += " ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                results = cur.fetchall()
                pairs = [AudioTranscriptPair(**row) for row in results]
                return pairs, total

    def get_audio_transcript_bundle(self, key_name: str) -> Optional[AudioTranscriptBundle]:
        """Get transcript and all associated audios for a key_name"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch transcript
                cur.execute(
                    """
                    SELECT id as transcript_id, key_name, language, text, file_id as transcript_file_id, created_at as transcript_created_at
                    FROM transcripts
                    WHERE key_name = %s
                    """,
                    (key_name,)
                )
                tr = cur.fetchone()
                if not tr:
                    return None
                # Fetch audios
                cur.execute(
                    """
                    SELECT * FROM audio
                    WHERE key_name = %s
                    ORDER BY CASE WHEN variant = 'original' THEN 0 ELSE 1 END, model_name
                    """,
                    (key_name,)
                )
                audios = [Audio(**row) for row in cur.fetchall()]
                return AudioTranscriptBundle(
                    key_name=tr['key_name'],
                    language=tr['language'],
                    text=tr['text'],
                    transcript_id=tr['transcript_id'],
                    transcript_file_id=tr['transcript_file_id'],
                    transcript_created_at=tr['transcript_created_at'],
                    audios=audios
                )
    
    def update_audio_transcript_pair(self, key_name: str, pair_data: AudioTranscriptPairUpdate, variant: str = "original", model_name: str = "") -> Optional[AudioTranscriptPair]:
        """Update an audio-transcript pair"""
        update_data = {k: v for k, v in pair_data.model_dump().items() if v is not None}
        if not update_data:
            return self.get_audio_transcript_pair(key_name, variant, model_name)
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Update transcript if needed
                transcript_updates = {}
                for field in ['key_name', 'language', 'text']:
                    if field in update_data:
                        transcript_updates[field] = update_data[field]
                
                if transcript_updates:
                    set_clause = ", ".join([f"{k} = %({k})s" for k in transcript_updates.keys()])
                    transcript_updates['old_key_name'] = key_name
                    cur.execute(
                        f"""
                        UPDATE transcripts 
                        SET {set_clause}, updated_at = NOW()
                        WHERE key_name = %(old_key_name)s
                        """,
                        transcript_updates
                    )
                
                # Update audio if needed
                audio_updates = {}
                for field in ['key_name', 'audio_variant', 'model_name', 'sample_rate', 'channels', 'duration_seconds']:
                    if field == 'audio_variant' and 'audio_variant' in update_data:
                        audio_updates['variant'] = update_data['audio_variant']
                    elif field in update_data:
                        audio_updates[field] = update_data[field]
                
                if audio_updates:
                    set_clause = ", ".join([f"{k} = %({k})s" for k in audio_updates.keys()])
                    audio_updates['old_key_name'] = key_name
                    audio_updates['old_variant'] = variant
                    audio_updates['old_model_name'] = model_name
                    cur.execute(
                        f"""
                        UPDATE audio 
                        SET {set_clause}, updated_at = NOW()
                        WHERE key_name = %(old_key_name)s AND variant = %(old_variant)s AND model_name = %(old_model_name)s
                        """,
                        audio_updates
                    )
                
                conn.commit()
                
                # Return updated pair
                new_key_name = update_data.get('key_name', key_name)
                new_variant = update_data.get('audio_variant', variant)
                new_model_name = update_data.get('model_name', model_name)
                return self.get_audio_transcript_pair(new_key_name, new_variant, new_model_name)
    
    def delete_audio_transcript_pair(self, key_name: str, variant: str = "original", model_name: str = "") -> bool:
        """Delete an audio-transcript pair and associated files"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Get file IDs before deletion
                cur.execute(
                    """
                    SELECT t.file_id as transcript_file_id, a.file_id as audio_file_id
                    FROM transcripts t
                    JOIN audio a ON t.key_name = a.key_name
                    WHERE t.key_name = %s AND a.variant = %s AND a.model_name = %s
                    """,
                    (key_name, variant, model_name)
                )
                result = cur.fetchone()
                if not result:
                    return False
                
                transcript_file_id, audio_file_id = result
                
                # Delete audio record (this will cascade delete via foreign key)
                cur.execute(
                    "DELETE FROM audio WHERE key_name = %s AND variant = %s AND model_name = %s",
                    (key_name, variant, model_name)
                )
                
                # Delete transcript record if this is the only audio for this transcript
                cur.execute(
                    "SELECT COUNT(*) FROM audio WHERE key_name = %s",
                    (key_name,)
                )
                remaining_audio_count = cur.fetchone()[0]
                
                if remaining_audio_count == 0:
                    cur.execute("DELETE FROM transcripts WHERE key_name = %s", (key_name,))
                
                # Files will be automatically deleted via CASCADE
                conn.commit()
                return True


# Global database manager instance
db_manager = DatabaseManager()