import os
import socket
import sys
import threading
import logging
from logging.handlers import RotatingFileHandler


cache_dir = "cache"
proxy_prefix  = 'http://{PROXY URL}:8888/'
last_known_domain = None

def setupLogging():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logger to capture all levels of logs

    # Create a file handler for logging debug and higher level logs
    file_handler = RotatingFileHandler('proxy.log', maxBytes=1e6, backupCount=3)
    file_handler.setLevel(logging.DEBUG)  # Set to capture DEBUG and higher level logs
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Create a console handler for logging info and higher level logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Set to capture INFO and higher level logs
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
setupLogging()

if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

def client_handler(connection_socket):
    try:
        request = connection_socket.recv(4096).decode()
        logging.debug(f"[D] Request received: \n{request.strip()}")

        # Extract URL from the request        
        domain, path = extract_domain_path(request)
        if not domain:
            logging.error("[D] Could not determine the domain for the request.")
            connection_socket.close()
        else:
            logging.debug(f"[D] Domain: {domain}, Path: {path}")

        url = domain + path

        logging.debug(f"[D] URL: {url}")

        file_path = get_cache_file_path(url)

        if is_in_cache(file_path):
            logging.debug(f"[D] Cache hit for {url}")
            response = get_from_cache(file_path)
        else:
            logging.warning(f"[D] Cache miss for {url}")
            response = forward_request(domain, path, request)
            cache_response(file_path, response)

        logging.debug(F"[D] Response: {response}")

        if isinstance(response, bytes):
            connection_socket.sendall(response)
        else:
            connection_socket.sendall(response.encode())
            
    except Exception as e:
        logging.error(f"Error handling client: {e}")
    except KeyboardInterrupt:
        logging.debug("Shutting down proxy server.")
        server_socket.close()
        sys.exit()
    finally:
        connection_socket.close()
        sys.exit()


def get_cache_file_path(url):
    # Generate a file path for the given URL to use in caching.
    safe_url = url.replace('/', '_').replace(':', '_').replace('?', '_')
    # Replacing characters that might not be valid in file names
    return os.path.join(cache_dir, safe_url)

def is_in_cache(file_path):
    #Check if the response for the URL is cached in a file.
    return os.path.exists(file_path)

def get_from_cache(file_path):
    # Retrieve the cached response from a file.
    with open(file_path, 'rb') as file:
        return file.read()

def cache_response(file_path, response):
    # Cache the response in a file.
    if response:
        with open(file_path, 'wb') as file:
            file.write(response)

def is_probably_domain(input_str):
    # Check if the first segment contains a period
    # and doesn't end with a file extension
    first_segment = input_str.split('/', 1)[0]
    if '.' in first_segment:
        # List of common file extensions
        common_extensions = ["html", "css", "js", "png", "jpg", "jpeg", "gif", "txt", "pdf", "xml", "json", "min.js", "min.css", "ico"]
        # Split the first segment by '.' and check the last part
        parts = first_segment.split('.')
        if len(parts) >= 2:
            last_part = parts[-1].lower()
            return last_part not in common_extensions
    return False

def extract_domain_path(request):
    # Extract the domain from the request, using the Referer header if necessary.
    global last_known_domain
    first_line = request.split('\n')[0]
    if(first_line.split(' '))[0] != 'GET':
        logging.error("[D] Request Method is not GET")
        return None, None
    url = first_line.split(' ')[1].lstrip('/')
    headers = request.split('\r\n')
    http_prefix = "http://"
    if url.startswith(http_prefix):
        url = url[len(http_prefix):]
    if '/' in url:
        domain, path = url.split('/', 1)
        path = '/' + path
    else:
        domain = url
        path = '/' 
    from_referer = any(header.lower().startswith('referer:') for header in headers)
    if from_referer:
        domain = get_domain_from_referer(request)
        if is_probably_domain(domain):
            return (domain, first_line.split(' ')[1])
        else:
            return (last_known_domain, first_line.split(' ')[1])
    else:
        last_known_domain = domain
        return (domain,path)

def get_domain_from_referer(request):
    # Extract the domain from the Referer header in the request.
    global proxy_prefix
    headers = request.split('\r\n')
    for header in headers:
        if header.lower().startswith('referer:'):
            referer_header = header.split(': ')[1]
            if referer_header.startswith(proxy_prefix):
                referer_header = referer_header[len(proxy_prefix):]
            if '/' in referer_header:
                logging.debug(f"[D] Referer Header:{referer_header}")
                domain = referer_header.split('/', 1)[0]
            else:
                domain = referer_header
            return domain
    return None

def forward_request(domain, path, request):
    if(':' in domain):
        domain = domain.split(':')[0]
    host = socket.gethostbyname(domain)
    try:
        request_line = f"GET {path} HTTP/1.1\r\n"
        new_request = request_line + f'Host: {domain}\r\nConnection: close\r\n' + '\r\n'.join(request.split('\r\n')[3:])
        logging.debug(f"[D] Forwarding Request: \n{new_request.strip()}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.connect((host, 80))
            server_socket.sendall(new_request.encode())
            # Receive the response
            response = b''
            while True:
                part = server_socket.recv(4096)
                if not part:
                    break  # No more data
                response += part
            logging.debug(f"Total response length: {len(response)} bytes")
            return response
    except Exception as e:
        logging.error(f"Error in forwarding request: {e}")
        return b''  # Return empty response in case of errors

# Setup server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_port = 8888 #random.randint(8080,8888)
server_socket.bind(('', server_port))
server_socket.listen(5)
logging.info(f"Proxy Server running on port {server_port}")

try:
    while True:
        connection_socket, addr = server_socket.accept()
        client_thread = threading.Thread(target=client_handler, args=(connection_socket,))
        client_thread.start()
except KeyboardInterrupt:
    logging.info("Shutting down proxy server.")
    server_socket.close()
