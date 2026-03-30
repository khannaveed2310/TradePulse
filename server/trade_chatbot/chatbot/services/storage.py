import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "trade-files")


def upload_file_to_supabase(file_path: str) -> str:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not configured (SUPABASE_URL / SUPABASE_KEY missing)")

    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    file_name = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        supabase.storage.from_(BUCKET).upload(file_name, f, {"upsert": "true"})

    try:
        os.remove(file_path)
        print(f"🗑 Local file deleted: {file_path}")
    except OSError:
        pass

    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{file_name}"