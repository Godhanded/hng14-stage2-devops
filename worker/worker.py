import redis
import time
import os
import signal
import sys

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

running = True


def handle_shutdown(signum, frame):
    global running
    print(f"Received signal {signum}, shutting down gracefully...")
    running = False


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def write_heartbeat():
    with open("/tmp/worker_heartbeat", "w") as f:
        f.write(str(time.time()))


def process_job(job_id):
    print(f"Processing job {job_id}")
    time.sleep(2)
    r.hset(f"job:{job_id}", "status", "completed")
    print(f"Done: {job_id}")


def main():
    print("Worker started, waiting for jobs...")
    write_heartbeat()
    while running:
        write_heartbeat()
        job = r.brpop("job", timeout=5)
        if job:
            _, job_id = job
            process_job(job_id.decode())
    print("Worker stopped.")
    sys.exit(0)


if __name__ == "__main__":
    main()
