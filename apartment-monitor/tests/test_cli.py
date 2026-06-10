import http.server
import socketserver
import subprocess
import sys
import textwrap
import threading


class AvailabilityHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"""
        <html><body><article class='unit-card'>
        <h2>Mission Bay Unit 7A</h2>
        <p>2 beds / 2 baths</p>
        <p>$4,850 per month</p>
        <p>Available now</p>
        </article></body></html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def test_cli_run_once_reports_matching_local_listing(tmp_path):
    with socketserver.TCPServer(("127.0.0.1", 0), AvailabilityHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = tmp_path / "config.yaml"
        config.write_text(
            textwrap.dedent(
                f"""
                interval_minutes: 15
                state_path: state.json
                neighborhoods: [Mission Bay]
                criteria:
                  - label: 2B2B under $5K
                    bedrooms: 2
                    min_bathrooms: 2
                    max_price: 5000
                sources:
                  - id: local-fixture
                    name: Local Fixture
                    kind: webpage
                    url: http://127.0.0.1:{server.server_address[1]}/availability
                    neighborhood: Mission Bay
                    render_js: false
                """
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "apartment_monitor.cli",
                "--config",
                str(config),
                "run-once",
                "--no-slack",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        server.shutdown()

    assert "1 new apartment match" in result.stdout
    assert "Mission Bay Unit 7A" in result.stdout
    assert "$4,850" in result.stdout
