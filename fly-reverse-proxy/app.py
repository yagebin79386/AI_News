from flask import Flask, request, Response
import requests

app = Flask(__name__)

BACKEND_ROOT = "https://news-crypto.fly.dev"
BACKEND_AI = "https://news-ai-yagebin.fly.dev/"  # update with your second app

@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    if request.path.startswith("/ai"):
        target = BACKEND_AI
        forward_path = request.full_path.replace("/ai", "", 1)
    else:
        target = BACKEND_ROOT
        forward_path = request.full_path

    # Forward the request
    url = f"{target}{forward_path}"
    method = request.method
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    data = request.get_data()

    resp = requests.request(method, url, headers=headers, data=data, cookies=request.cookies, allow_redirects=False)

    return Response(resp.content, resp.status_code, resp.headers.items())
