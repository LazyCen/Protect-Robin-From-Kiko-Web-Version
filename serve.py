import http.server
import socketserver
import sys

PORT = 8000

class COOPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # These headers are required for SharedArrayBuffer and Cross-Origin Isolation in Godot 4
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

if __name__ == "__main__":
    # Allow overriding the port via command line argument
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    
    # Enable address reuse to avoid "Address already in use" errors on quick restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), COOPHandler) as httpd:
        print(f"==================================================")
        print(f" Godot Web Export Local Server Running!")
        print(f" Active on: http://localhost:{port}")
        print(f"==================================================")
        print(f"Press Ctrl+C to stop the server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server...")
