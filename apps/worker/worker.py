import time
from dotenv import load_dotenv
from supabase import create_client

from .ig_api import InstagramGraph
from .config import load_worker_config
from .jobs import (
    fetch_pending_conversations,
    fetch_any_pending_conversations,
    preprocess_conversation,
)

# Load environment variables from .env (local development)
load_dotenv()

# Load worker configuration (fails fast if required env vars are missing)
CFG = load_worker_config()

# Supabase client (service role; server-side only)
SB = create_client(CFG.supabase_url, CFG.supabase_service_role_key)

# Instagram Graph API client (used to resolve conversation_ext_id, etc.)
GRAPH = InstagramGraph(CFG.api_version, CFG.access_token)

def threshold_loop():
    """
    Volume-based trigger loop:
    - Poll conversations where pending_count >= threshold_messages (default 10)
    - For each, create a preprocess_run and reset pending state
    """
    while True:
        try:
            convs = fetch_pending_conversations(SB, CFG.threshold_messages)
            for c in convs:
                preprocess_conversation(SB, GRAPH, c, trigger="threshold_10")
        except Exception as e:
            print("[threshold_loop] error:", e)

        time.sleep(CFG.threshold_poll_seconds)


def hourly_loop():
    """
    Time-based sweep loop:
    - Wakes up frequently (hourly_poll_seconds, default 60s)
    - But only runs the sweep when 1 hour has elapsed since last sweep
    """
    # Recommended: start counting from "now" so it doesn't run immediately on boot.
    last_run = time.time()

    while True:
        now = time.time()

        # Run sweep once per hour
        if (now - last_run) >= 3600:
            last_run = now
            try:
                convs = fetch_any_pending_conversations(SB)
                for c in convs:
                    preprocess_conversation(SB, GRAPH, c, trigger="hourly")
            except Exception as e:
                print("[hourly_loop] error:", e)

        time.sleep(CFG.hourly_poll_seconds)


if __name__ == "__main__":
    """
    Run both loops in a single process
    Uses threads to run hourly + threshold loops concurrently.
    """
    import threading

    t1 = threading.Thread(target=threshold_loop, daemon=True)
    t2 = threading.Thread(target=hourly_loop, daemon=True)
    t1.start()
    t2.start()

    print("Worker running (threshold + hourly). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nWorker stopped.")

    