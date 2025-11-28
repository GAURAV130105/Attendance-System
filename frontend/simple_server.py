from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
import socket

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except:
        return False

def run_server(port=5000):
    if not check_port(port):
        print(f"Port {port} is already in use. Trying another port...")
        for p in range(5001, 5010):
            if check_port(p):
                port = p
                break
        else:
            print("Could not find an available port. Please close other applications and try again.")
            sys.exit(1)

    server_address = ('0.0.0.0', port)
    
    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            super().end_headers()

    try:
        httpd = HTTPServer(server_address, Handler)
        print(f"Server started at http://127.0.0.1:{port}")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
        httpd.socket.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_server()