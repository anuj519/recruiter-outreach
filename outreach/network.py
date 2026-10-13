import socket
import time


def wait_for_network(host="oauth2.googleapis.com", timeout_minutes=10):
    """Scheduled runs often start the moment the Mac wakes, before Wi-Fi reconnects. Wait for DNS to work."""
    deadline = time.monotonic() + timeout_minutes * 60
    while True:
        try:
            socket.getaddrinfo(host, 443)
            return
        except OSError:
            if time.monotonic() > deadline:
                raise SystemExit(f"No network after {timeout_minutes} minutes; giving up this run.")
            print("Waiting for network...", flush=True)
            time.sleep(15)
