"""Session Processor - HTTP endpoint for batch processing."""

import json
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class ProcessorHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path in ("/health", "/"):
            self._send_json(200, {"status": "healthy", "service": "nike-session-processor"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path in ("/", "/process"):
            try:
                from .main import SessionMonitor
                logger.info("Starting batch session processing...")
                monitor = SessionMonitor()
                processed = monitor.check_and_notify()
                self._send_json(200, {"success": True, "processed_count": processed})
            except Exception as e:
                logger.error(f"Failed to process sessions: {e}", exc_info=True)
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")


def run_processor(host: str = "0.0.0.0", port: int = 8080):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    server = HTTPServer((host, port), ProcessorHandler)
    logger.info(f"Starting Nike Session Processor on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nike Session Processor Service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    args = parser.parse_args()
    run_processor(args.host, args.port)
