# Simple Python Proxy Server

## Overview
A simple proxy server written in python. It is designed to forward HTTP requests, cache responses and log detailed information about interactions.

## Features
HTTP Request Forwarding: Forwards HTTP requests to their intended destinations.
Caching Mechanism: Caches the responses of requests to improve efficiency.
Detailed Logging: Includes detailed logging for debugging and monitoring, with both console and file output.
Domain Extraction: Extracts and processes domain information from HTTP requests.
Threaded Request Handling: Utilizes threading to handle multiple client requests concurrently.

## Requirements
Python 3.x

## Usage
1) Run the proxy server:
`python3 proxy_server.py`
This will start the proxy server on the default port (8888).

2) Configure your HTTP client to use the proxy server by setting the proxy address to http://localhost:8888/.

3) Make HTTP requests from your client, and observe the requests and responses being logged and cached by the proxy server.

## Configuration
- Logging: The logging level and format can be modified in the setupLogging() function.
- Cache Directory: The directory for caching (default is "cache") can be changed by modifying the cache_dir variable.
- Proxy Prefix: The proxy prefix URL used for domain extraction can be adjusted in the proxy_prefix variable.

## HTTP Test Sites
- pompeiisites.org
- httpforever.com
- http.badssl.com
- info.cern.ch
- neverssl.com
