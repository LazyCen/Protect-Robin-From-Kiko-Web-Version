import http.server
import socketserver
import sys
import os
import gzip
import io

PORT = 8000

# Cache for compressed files to avoid compressing files on every request: (filepath, mtime) -> compressed_bytes
_compressed_cache = {}

class COOPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # These headers are required for SharedArrayBuffer and Cross-Origin Isolation in Godot 4
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def do_GET(self):
        # Translate requested URL path to local file path
        filepath = self.translate_path(self.path)
        
        # Check if the client supports gzip and the path resolves to an existing file
        accept_encoding = self.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding and os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1].lower()
            # Compress WebAssembly, Godot PCK packages, JavaScript, HTML, and CSS
            if ext in ['.wasm', '.pck', '.js', '.html', '.css']:
                mtime = os.path.getmtime(filepath)
                cache_key = (filepath, mtime)
                
                if cache_key in _compressed_cache:
                    compressed_data = _compressed_cache[cache_key]
                else:
                    print(f"Compressing {os.path.basename(filepath)} with gzip (size: {os.path.getsize(filepath) / 1024 / 1024:.1f} MB)...")
                    try:
                        with open(filepath, 'rb') as f:
                            data = f.read()
                        out = io.BytesIO()
                        with gzip.GzipFile(fileobj=out, mode='wb', compresslevel=6) as f_out:
                            f_out.write(data)
                        compressed_data = out.getvalue()
                        _compressed_cache[cache_key] = compressed_data
                        print(f"Compressed {os.path.basename(filepath)}: {len(data)/1024/1024:.1f} MB -> {len(compressed_data)/1024/1024:.1f} MB")
                    except Exception as e:
                        print(f"Failed to compress {os.path.basename(filepath)}: {e}")
                        super().do_GET()
                        return
                
                # Send compressed response
                self.send_response(200)
                ctype = self.guess_type(filepath)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(compressed_data)))
                self.end_headers()
                self.wfile.write(compressed_data)
                return
                
        # Default non-compressed fallback
        super().do_GET()

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
