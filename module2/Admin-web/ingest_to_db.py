import hashlib
import mimetypes
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Tuple, Dict, List

import psycopg2
from psycopg2.extras import execute_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "dataset"
ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_env(env_path: Path) -> dict:
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")  # remove optional quotes
        env[key] = value
    return env


def get_db_conn(env: dict):
    host = env.get("DB_HOST") or os.getenv("DB_HOST")
    port = int((env.get("DB_PORT") or os.getenv("DB_PORT") or 5432))
    dbname = env.get("DB_NAME") or os.getenv("DB_NAME")
    user = env.get("DB_USER") or os.getenv("DB_USER")
    password = env.get("DB_PASSWORD") or os.getenv("DB_PASSWORD")

    if not all([host, dbname, user, password]):
        raise RuntimeError("Database configuration is missing. Ensure DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD are set in .env or environment.")

    return psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)


def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_kind') THEN
                    CREATE TYPE file_kind AS ENUM ('audio', 'transcript', 'model_audio');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'audio_variant') THEN
                    CREATE TYPE audio_variant AS ENUM ('original', 'generated');
                END IF;
            END$$;
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id BIGSERIAL PRIMARY KEY,
                kind file_kind NOT NULL,
                relative_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_ext TEXT NOT NULL,
                media_type TEXT,
                size_bytes BIGINT NOT NULL,
                sha256 CHAR(64) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (sha256),
                UNIQUE (relative_path)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transcripts (
                id BIGSERIAL PRIMARY KEY,
                key_name TEXT NOT NULL,
                language TEXT,
                text TEXT NOT NULL,
                file_id BIGINT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (key_name),
                UNIQUE (file_id)
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audio (
                id BIGSERIAL PRIMARY KEY,
                key_name TEXT NOT NULL,
                variant audio_variant NOT NULL,
                model_name TEXT NOT NULL DEFAULT '',
                file_id BIGINT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                sample_rate INTEGER,
                channels INTEGER,
                duration_seconds DOUBLE PRECISION,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (file_id),
                UNIQUE (key_name, variant, model_name)
            );
            """
        )

        cur.execute("CREATE INDEX IF NOT EXISTS idx_files_kind ON files(kind);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_key ON transcripts(key_name);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audio_key_variant ON audio(key_name, variant);")
    conn.commit()


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def infer_media_type(path: Path) -> Optional[str]:
    mt, _ = mimetypes.guess_type(str(path))
    return mt


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class FileRecord:
    kind: str
    relative_path: str
    file_name: str
    file_ext: str
    media_type: Optional[str]
    size_bytes: int
    sha256: str


def gather_file_record(path: Path, kind: str) -> FileRecord:
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    return FileRecord(
        kind=kind,
        relative_path=rel,
        file_name=path.name,
        file_ext=path.suffix.lower().lstrip('.'),
        media_type=infer_media_type(path),
        size_bytes=path.stat().st_size,
        sha256=sha256sum(path),
    )


def upsert_files(conn, records: Iterable[FileRecord], batch_size: int = 100) -> Tuple[int, Dict[str, int]]:
    rows = [(
        r.kind, r.relative_path, r.file_name, r.file_ext, r.media_type, r.size_bytes, r.sha256
    ) for r in records]
    inserted = 0
    path_to_id: Dict[str, int] = {}
    if not rows:
        return inserted, path_to_id
    
    # Process in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO files(kind, relative_path, file_name, file_ext, media_type, size_bytes, sha256)
                VALUES %s
                ON CONFLICT (relative_path) DO UPDATE
                  SET media_type = EXCLUDED.media_type,
                      size_bytes = EXCLUDED.size_bytes,
                      updated_at = NOW()
                RETURNING id, relative_path;
                """,
                batch,
                page_size=min(batch_size, 100),
            )
            for file_id, rel in cur.fetchall():
                path_to_id[rel] = file_id
                inserted += 1
        conn.commit()  # Commit each batch
    return inserted, path_to_id


def upsert_transcripts(conn, items: Iterable[Tuple[str, str, int]], language: Optional[str] = None, batch_size: int = 100) -> int:
    # items: (key_name, text, file_id)
    rows = [(k, language, t, fid) for k, t, fid in items]
    if not rows:
        return 0
    
    # Process in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO transcripts(key_name, language, text, file_id)
                VALUES %s
                ON CONFLICT (key_name) DO UPDATE
                  SET text = EXCLUDED.text,
                      language = COALESCE(EXCLUDED.language, transcripts.language),
                      file_id = EXCLUDED.file_id,
                      updated_at = NOW();
                """,
                batch,
                page_size=min(batch_size, 100),
            )
        conn.commit()  # Commit each batch
    return len(rows)


def upsert_audio(conn, items: Iterable[Tuple[str, str, Optional[str], int]], batch_size: int = 100) -> int:
    # items: (key_name, variant, model_name, file_id)
    rows = list(items)
    if not rows:
        return 0
    
    # Process in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO audio(key_name, variant, model_name, file_id)
                VALUES %s
                ON CONFLICT (file_id) DO NOTHING;
                """,
                batch,
                page_size=min(batch_size, 100),
            )
        conn.commit()  # Commit each batch
    return len(rows)


def iter_transcript_paths(limit: Optional[int]) -> Iterable[Path]:
    base = DATASET_DIR / "transcripts"
    count = 0
    if not base.exists():
        return
    for p in sorted(base.glob("*.txt")):
        yield p
        count += 1
        if limit and count >= limit:
            break


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def iter_original_audio_paths(limit: Optional[int]) -> Iterable[Path]:
    base = DATASET_DIR / "audio"
    count = 0
    if not base.exists():
        return
    # expect folder per key, files inside
    for folder in sorted([p for p in base.iterdir() if p.is_dir()]):
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() == ".wav":
                yield p
                count += 1
                if limit and count >= limit:
                    return


def iter_model_audio_paths(limit: Optional[int]) -> Iterable[Tuple[str, Path]]:
    base = DATASET_DIR / "models"
    count = 0
    if not base.exists():
        return
    for model_dir in sorted([p for p in base.iterdir() if p.is_dir()]):
        model_name = model_dir.name
        for p in sorted(model_dir.rglob("*.wav")):
            yield model_name, p
            count += 1
            if limit and count >= limit:
                return


def key_from_transcript(path: Path) -> str:
    return path.stem


def key_from_original_audio(path: Path) -> str:
    # Expect structure dataset/audio/000123/<files>
    try:
        return path.parent.name
    except Exception:
        return path.stem


def key_from_model_audio(path: Path) -> str:
    return path.stem


@dataclass
class IngestConfig:
    dry_run: bool = False
    limit: Optional[int] = None
    verbose: bool = False
    drop_all: bool = False
    batch_size: int = 100


class IngestService:
    def __init__(self, conn, project_root: Path, dataset_dir: Path, verbose: bool = False, batch_size: int = 100):
        self.conn = conn
        self.project_root = project_root
        self.dataset_dir = dataset_dir
        self.verbose = verbose
        self.batch_size = batch_size

    def log(self, message: str):
        if self.verbose:
            print(message)

    def ensure_schema(self):
        ensure_schema(self.conn)

    def drop_all_tables(self):
        with self.conn.cursor() as cur:
            # Drop in dependency order
            cur.execute("DROP TABLE IF EXISTS audio CASCADE;")
            cur.execute("DROP TABLE IF EXISTS transcripts CASCADE;")
            cur.execute("DROP TABLE IF EXISTS files CASCADE;")
        self.conn.commit()

    def upsert_files(self, records: Iterable[FileRecord]) -> Tuple[int, Dict[str, int]]:
        return upsert_files(self.conn, records, self.batch_size)

    def upsert_transcripts(self, items: Iterable[Tuple[str, str, int]], language: Optional[str] = None) -> int:
        return upsert_transcripts(self.conn, items, language, self.batch_size)

    def upsert_audio(self, items: Iterable[Tuple[str, str, Optional[str], int]]) -> int:
        # Normalize None model_name to '' to satisfy NOT NULL + unique index
        normalized = []
        for key_name, variant, model_name, file_id in items:
            normalized.append((key_name, variant, model_name or '', file_id))
        return upsert_audio(self.conn, normalized, self.batch_size)

    def iter_transcript_paths(self, limit: Optional[int]) -> List[Path]:
        base = self.dataset_dir / "transcripts"
        paths: List[Path] = []
        if not base.exists():
            return paths
        for p in sorted(base.glob("*.txt")):
            paths.append(p)
            if limit and len(paths) >= limit:
                break
        return paths

    def iter_original_audio_paths(self, limit: Optional[int]) -> List[Path]:
        base = self.dataset_dir / "audio"
        paths: List[Path] = []
        if not base.exists():
            return paths
        for folder in sorted([p for p in base.iterdir() if p.is_dir()]):
            for p in sorted(folder.iterdir()):
                if p.suffix.lower() == ".wav":
                    paths.append(p)
                    if limit and len(paths) >= limit:
                        return paths
        return paths

    def iter_model_audio_paths(self, limit: Optional[int]) -> List[Tuple[str, Path]]:
        base = self.dataset_dir / "models"
        results: List[Tuple[str, Path]] = []
        if not base.exists():
            return results
        for model_dir in sorted([p for p in base.iterdir() if p.is_dir()]):
            model_name = model_dir.name
            for p in sorted(model_dir.rglob("*.wav")):
                results.append((model_name, p))
                if limit and len(results) >= limit:
                    return results
        return results

    def ingest(self, config: IngestConfig):
        transcript_files = self.iter_transcript_paths(config.limit)
        transcript_records = []
        for p in transcript_files:
            try:
                record = gather_file_record(p, kind="transcript")
                transcript_records.append(record)
            except Exception as e:
                raise Exception(f"Error processing transcript file {p}: {e}")
        self.log(f"Found {len(transcript_records)} transcript files")
        if not config.dry_run and transcript_records:
            try:
                _, path_to_id = self.upsert_files(transcript_records)
                self.log(f"Successfully upserted {len(path_to_id)} file records")
            except Exception as e:
                raise Exception(f"Error upserting transcript files to database: {e}")
            tr_items = []
            for p in transcript_files:
                try:
                    rel = p.relative_to(self.project_root).as_posix()
                    if rel not in path_to_id:
                        raise Exception(f"Path {rel} not found in path_to_id mapping")
                    tr_items.append((key_from_transcript(p), read_text_file(p), path_to_id[rel]))
                except Exception as e:
                    raise Exception(f"Error processing transcript {p}: {e}")
            try:
                upserted = self.upsert_transcripts(tr_items, language="vi")
                self.log(f"Upserted {upserted} transcripts")
            except Exception as e:
                raise Exception(f"Error upserting transcripts to database: {e}")

        original_files = self.iter_original_audio_paths(config.limit)
        original_records = [gather_file_record(p, kind="audio") for p in original_files]
        self.log(f"Found {len(original_records)} original WAV audio files")
        if not config.dry_run and original_records:
            _, path_to_id = self.upsert_files(original_records)
            audio_items = []
            for p in original_files:
                rel = p.relative_to(self.project_root).as_posix()
                audio_items.append((key_from_original_audio(p), 'original', None, path_to_id[rel]))
            upserted = self.upsert_audio(audio_items)
            self.log(f"Upserted {upserted} original audio entries")

        model_files = self.iter_model_audio_paths(config.limit)
        model_records = [gather_file_record(p, kind="model_audio") for _, p in model_files]
        self.log(f"Found {len(model_records)} model-generated WAV audio files")
        if not config.dry_run and model_records:
            _, path_to_id = self.upsert_files(model_records)
            gen_items = []
            for model_name, p in model_files:
                rel = p.relative_to(self.project_root).as_posix()
                gen_items.append((key_from_model_audio(p), 'generated', model_name, path_to_id[rel]))
            upserted = self.upsert_audio(gen_items)
            self.log(f"Upserted {upserted} generated audio entries")


def run_ingest(config: IngestConfig) -> int:
    env = load_env(ENV_PATH)
    if config.verbose:
        print(f"Using .env at {ENV_PATH}")
        print(f"Dataset directory: {DATASET_DIR}")
    try:
        conn = get_db_conn(env)
    except Exception as e:
        print(f"Failed to connect to DB: {e}", file=sys.stderr)
        return 2
    try:
        service = IngestService(conn, PROJECT_ROOT, DATASET_DIR, verbose=config.verbose, batch_size=config.batch_size)
        if config.drop_all:
            service.log("Dropping all tables before ensuring schema...")
            service.drop_all_tables()
        service.ensure_schema()
        service.ingest(config)
    except Exception as e:
        conn.rollback()
        print(f"Ingestion failed: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if config.verbose:
        print("Done.")
    return 0


if __name__ == "__main__":
    # Example direct run without CLI args: adjust variables as needed
    example_config = IngestConfig(
        dry_run=False,
        limit=None,
        verbose=True,
        drop_all=True,
    )
    raise SystemExit(run_ingest(example_config))


