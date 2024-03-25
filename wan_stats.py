import http.server
import socketserver
import json

# Configuration variables
wan_interface = 'ppp0'
listen_port = 9999

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/stats':
            network_data = self.get_network_data()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(network_data).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

    def get_network_data(self):
        try:
            with open('/proc/net/dev', 'r') as f:
                for line in f:
                    if line.startswith(wan_interface + ':'):
                        data = line.split()
                        if len(data) >= 10:
                            data_received, data_sent = map(int, (data[1], data[9]))
                            return {"data_received": data_received, "data_sent": data_sent}
                        else:
                            return {"error": "Insufficient fields in /proc/net/dev"}
                return {"error": f"Interface {wan_interface} not found"}
        except Exception as e:
            return {"error": str(e)}

def run(server_class=http.server.HTTPServer, handler_class=MyHttpRequestHandler, port=listen_port):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
