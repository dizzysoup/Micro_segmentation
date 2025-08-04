import asyncio
import websockets
import json
import socket
import os 
import signal
import time 
import requests
# ================= WebSocket Server 接收主機事件 =================

global limit
limit = 3 
# 讀取DSL
def load_dsl_rules(file_path="dsl.txt"):
    rules = []
    with open(file_path, "r") as f:
        for line in f:
            if not line.strip().startswith("allow"):
                continue
            try:
                # 解析語法：allow{TCP, A, B},{ 3306, (security:xxx),(type:xxx) }
                part1, part2 = line.strip().split("},{")
                proto, src, dst = part1.replace("allow{", "").split(",")
                port = part2.split(",")[0].strip()
                port = int(port) if port else None
                rules.append({
                    "protocol": proto.strip(),
                    "src_ip": src.strip(),
                    "dst_ip": dst.strip().rstrip(" }"),
                    "port": port
                })
            except Exception as e:
                print(f"[!] DSL parsing error: {e}")
    return rules

# 檢查event 是否allow
def is_event_allowed(event, rules):
    if event["dst_port"] in [8765, 8766]:
        return True
    for rule in rules:
        if (
            rule["protocol"].upper() == event["protocol"].upper()
            and rule["src_ip"] == event["src_ip"]
            and rule["dst_ip"] == event["dst_ip"]
            and (rule["port"] is None or rule["port"] == event["dst_port"])
        ):
            return True
    return False

# 寫入到 log.txt
def log_event_to_file(event):
    print(event)
    with open("log.txt", "a") as f:
        f.write(json.dumps(event) + "\n")



# 🔍 檢查某個 TCP port 是否正在被使用
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# 🧼 嘗試釋放 port（僅限 Linux，利用 lsof + kill）
def free_port(port):
    print(f"[⚠️] Port {port} is occupied, trying to free it...")
    try:
        # 取得佔用該 port 的 PID
        output = os.popen(f"lsof -i :{port} -sTCP:LISTEN -t").read()
        if output:
            pids = output.strip().split("\n")
            for pid in pids:
                os.kill(int(pid), signal.SIGTERM)
                print(f"[✔] Terminated process PID {pid} using port {port}")
        else:
            print(f"[❌] No process found using port {port}")
    except Exception as e:
        print(f"[❌] Failed to free port: {e}")

async def handle_event(websocket):
    rules = load_dsl_rules()  # 每次連線前載入最新 dsl.txt   
    global limit
    async for message in websocket:
        try:
            event = json.loads(message)
            print(f"[✅] Received event from host: {event}")

            # TODO: 你可以在這裡加入 intent 白名單檢查邏輯
            allowed = is_event_allowed(event, rules)
            if allowed:
                response = {"status": "received", "intent_check": "allowed"}
                print(f"[✅] Received event from host, matches DSL rule: {event}")
            else:
                limit -= 1
                print(limit)
                response = {
                    "status": "received",
                    "intent_check": "⚠ not allowed",
                    "action": "block_suggested",
                    "reason": "Intent not defined in DSL"
                }
                if limit <= 0:
                    print(f"[❌] Too many connection attempts, blocking: {event}")
                    url = "http://sdn.yuntech.poc.com/datacenter/submit_labels"
                    
                    data = {
                        "hostInfo" : {
                            "ipv4" : [event["src_ip"],]
                        },
                        "labels" : {
                            "function" : "Null",
                            "priority" : "Null",
                            "type": "Order",
                            "application": "Null",
                            "environment" : "Null",
                            "security" : "quarantined"
                        }    
                    }
                    response = requests.post(url, json=data)
                else : 
                    print(f"[❌] Received event from host, not in DSL rules, block suggested: {event}")
                log_event_to_file(event)  # ✅ 寫入 log.txt
            await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosedOK as e:
            print(f"[ℹ️] Host connection closed normally: {e}")
        except Exception as e:
            print(f"[❌] WebSocket error: {e}")

async def start_websocket_server():
    print("[*] Starting WebSocket Server on 0.0.0.0:8765")
    async with websockets.serve(handle_event, "0.0.0.0", 8765):
        await asyncio.Future()

def launch_ws_server():
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        if is_port_in_use(8765):
            free_port(8765)
            time.sleep(1)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_websocket_server())

