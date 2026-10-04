"""Railway production entrypoint for the Traffic Violation web service."""
import os

from traffic_violation_system.web.server import TrafficAPIHandler, ThreadingHTTPServer

def main():
    port = int(os.environ.get("PORT", "5000"))
    TrafficAPIHandler.initialize_services()
    server = ThreadingHTTPServer(("0.0.0.0", port), TrafficAPIHandler)
    print(f"Traffic Violation Web Server listening on 0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
