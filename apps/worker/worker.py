import time
from dotenv import load_dotenv
from supabase import create_client
from .ig_api import InstagramGraph
from .config import load_worker_config
from .jobs import fetch_pending_conversations, fetch_any_pending_conversations, preprocess_conversation

load_dotenv()

CFG = load_worker_config()
SB = create_client(CFG.supabase_url, CFG.supabase_service_role_key)
GRAPH = InstagramGraph(CFG.api_version, CFG.access_token)
print("ACCESS_TOKEN prefix:", CFG.access_token[:10], "len:", len(CFG.access_token))


def threshold_loop():
    while True:
        try:
            convs = fetch_pending_conversations(SB, CFG.threshold_messages)
            for c in convs:
                preprocess_conversation(SB, GRAPH, c, trigger="threshold_10")
        except Exception as e:
            print("[threshold_loop] error:", e)
        time.sleep(CFG.threshold_poll_seconds)

def hourly_loop():
    # Runs as a loop that wakes up frequently; does hourly sweep by checking elapsed time.
    last_run = 0
    while True:
        now = time.time()
        if (now - last_run) >= 3600:
            last_run = now
            try:
                convs = fetch_any_pending_conversations(SB)
                for c in convs:
                    preprocess_conversation(SB,GRAPH, c, trigger="hourly")
            except Exception as e:
                print("[hourly_loop] error:", e)

        time.sleep(CFG.hourly_poll_seconds)

if __name__ == "__main__":
    # Run both loops in one process (simple MVP).
    # In prod you might split them or use a real job scheduler.
    import threading
    t1 = threading.Thread(target=threshold_loop, daemon=True)
    t2 = threading.Thread(target=hourly_loop, daemon=True)
    t1.start()
    t2.start()
    

    print("Worker running (threshold + hourly). Ctrl+C to stop.")
    while True:
        time.sleep(5)
