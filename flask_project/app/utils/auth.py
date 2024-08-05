from flask import request, abort

API_KEY = 'kabirhere'

def authenticate():
    api_key = request.headers.get('ApiKey')
    if api_key != API_KEY:
        abort(401, description="Unauthorized")
    return "API Key is verified"
