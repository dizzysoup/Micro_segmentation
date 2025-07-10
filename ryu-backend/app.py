from flask import Flask,jsonify,request, session
from dslmanager import transform_intent_to_dsl,reevaluate_dsl,load_rpg
from host_even_receiver import launch_ws_server
import threading
from db import get_db_connection
from dotenv import load_dotenv
import json
import re
import asyncio
import os 
import jwt
import datetime
import redis 

app = Flask(__name__)
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.flushdb()
load_dotenv()

# 模擬讀取 intent.txt 和 epg.json 的路徑
INTENT_FILE = 'intent.txt'
RPG_FILE = os.getenv('RPG_FILE', 'rpg_case_1.json')
JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXP_DELTA_SECONDS = int(os.getenv('JWT_EXP_DELTA_SECONDS', 120))  
JWT_ISSUER = os.getenv('JWT_ISSUER', 'SDC_Server')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

app.secret_key = FLASK_SECRET_KEY
app.permanent_session_lifetime = datetime.timedelta(minutes=30)

# 讀取 intent.txt
def read_intent_file():
    try:
        with open(INTENT_FILE, 'r') as file:
            intents = file.readlines()
        return [intent.strip() for intent in intents]  # 移除每行末尾的換行符
    except Exception as e:
        print(f"Error reading {INTENT_FILE}: {e}")
        return []

# 讀取 epg.json
def read_epg_json():
    try:
        with open(RPG_FILE, 'r') as file:
            epg_data = json.load(file)
        return epg_data
    except Exception as e:
        print(f"Error reading {RPG_FILE}: {e}")
        return []

# 讀取 label.json 檔案的函數
def load_labels(category):
    with open('label.json', 'r') as file:
        data = json.load(file)
    return data.get(category)

# 把資料插入到EPG之中
def insert_epg(ip , info):   
    # 🔽 寫入epg.json
    new_entry = {
        "ip": ip,
        "function": info.get("function", "Null"),
        "priority": info.get("priority", "Null"),
        "type": info.get("type", "Null"),
        "application": info.get("application", "Null"),
        "environment": info.get("environment", "Null")
    }
    try:
        with open(RPG_FILE, 'r') as file:
            epg_data = json.load(file)
    except FileNotFoundError:
        epg_data = []

    updated = False
    for entry in epg_data:
        if entry['ip'] == ip:
            entry.update(new_entry)
            updated = True
            break

    if not updated:
        epg_data.append(new_entry)

    with open(RPG_FILE, 'w') as file:
        json.dump(epg_data, file, indent=4)
    

# 取得特定標籤 ex : function,type,environment,application
@app.route('/datacenter/label/<category>', methods=['GET'])
def get_label(category):
    labels = load_labels(category)
    return jsonify(labels)
    
# 為 IP 去填上標籤，組成RPG
@app.route('/datacenter/submit_labels', methods=['POST'])
async def submit_labels():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # 提取 host 資料
    host_info = data.get("hostInfo", {})
    ipv4 = host_info.get('ipv4', 'N/A')[0]
    print(f"建立{ipv4} 的RPG")
    if ipv4 == 'N':
        return jsonify({"error": "No valid IP address provided"}), 400
    labels = data.get('labels', {})

    new_data = {
        "ip": ipv4,
        "function": labels.get("function", "Null"),
        "priority": labels.get("priority", "Null"),
        "type": labels.get("type", "Null"),
        "application": labels.get("application", "Null"),
        "environment" : labels.get("environment","Null"),
        "security" : labels.get("security","Null")
    }
    label_changed = False
    try:
        with open(RPG_FILE, 'r') as file:
            epg_data = json.load(file)
    except FileNotFoundError:
        # 如果檔案不存在，初始化為空列表
        epg_data = []
    ip_found = False
   
    diff_labels = {}
    index = 0
    
    for entry in epg_data:        
        if entry['ip'] == ipv4:            
            ip_found = True
            for key in new_data:
                old_val = entry.get(key)
                new_val = new_data[key]
                if old_val != new_val:
                    diff_labels[index] = {"before": old_val, "after": new_val}
                    index = index + 1
                    label_changed = True # 標籤有變更
                    break
            entry.update(new_data)  # 如果 IP 存在，更新該條目
            ip_found = True
            break
    if not ip_found:
        epg_data.append(new_data)
        label_changed = True # 標籤有變更
        
    # 將更新後的資料寫回 epg.json
    with open(RPG_FILE, 'w') as file:        
        json.dump(epg_data, file, indent=4)
    
    # DSL 有改變，需重新評估
    if label_changed:
       print(f"🔁 {ipv4} Label has changed, triggering DSL reevaluation")
       print(f"🔁 {ipv4} diff_labels: {diff_labels}")
       await reevaluate_dsl(ipv4,diff_labels) 

    return jsonify({"status": "success", "message": "Labels received and processed."})

# 查詢特定RP中的RPG內容
@app.route('/datacenter/epg/<ip>', methods=['GET'])
def get_epg(ip):
    rpg_values = load_rpg(ip)
    return jsonify(rpg_values)

# 意圖增加
''' 
  { 
    "method" : "allow",
    "egress" : "Web",
    "egresstype" : "function",
    "port" : 3306,
    "protocol" : "TCP",
    "ingress" : "Database",
    "ingresstype" : "function"
   }
'''
@app.route('/datacenter/intent', methods=['POST'])
async def post_intent():
    data = request.get_json()
    
    method = data.get('method' , '')  # allow or deny
    egresstype = data.get('egresstype','') #value
    egress = data.get('egress','')  # function, type, environment, application .. etc 
    protocol = data.get('protocol','') # TCP、UDP、ICMP
    ingresstype = data.get('ingresstype','') #  value
    ingress = data.get('ingress','') #function, type, environment, application .. etc
    port = data.get('port','') # 3306,22,80..etc..  
    
    new_entry = f"{method} {egresstype}:{egress}, {protocol}:{port}, {ingresstype}:{ingress} \n"     
    print("插入的意圖為")
    print(new_entry)
    # 將意圖寫入 intent.txt
    with open('intent.txt', 'a') as intent_file:
        intent_file.write(new_entry)    

    await transform_intent_to_dsl(new_entry) # intent 轉換成DSL
    return "Intent deployed success.", 200

# 取得所有DSL，用於前端面板模擬
@app.route('/datacenter/dsl', methods=['GET'])
def get_all_dsl():
    function_labels = set()
    edges = []
    line_counter = 1
    
    # 收集edges
    with open('intent.txt', 'r') as intent_file:
        for line in intent_file:
            parts = line.strip().split(',')
            action_label = parts[0].strip().split(' ')
            action = action_label[0].lower()  # deny or allow
            source_label = action_label[1].strip().lower()
            
            protocol_port = parts[1].strip().lower()
            if ':' in protocol_port:
                protocol, port = protocol_port.split(':', 1)
            else:
                protocol, port = protocol_port, ''
            target_label = parts[2].strip().lower()
             
            function_labels.add(source_label)
            function_labels.add(target_label) 
            label = protocol.upper() +" " +  port
            edges.append({
                "id": f"e{line_counter}-2",
                "source": source_label,
                "target": target_label,
                "label": label,
                "action": action
            })
            line_counter += 1
    node_data = []
    label_map = {}
    count_map = {}
    # 收集nodes
    seen = set()
    for label_value in function_labels:
        if label_value in seen:
            continue
        seen.add(label_value)
        idx = len(node_data) + 1
        # 自動判斷 type（根據冒號前的字）
        if ':' in label_value:
            label_type, label_real = label_value.split(':', 1)
        else:
            label_type, label_real = 'unknown', label_value
       
        node_data.append({
            "id": str(idx),
            "type": label_type,
            "label": label_real,
            "count" : 0 
        })
        label_map[label_value] = str(idx)
        count_map[idx] = 0  # 初始化計數為 0

    # 把 source / target 轉成 ID
    for edge in edges:
        edge["source"] = label_map.get(edge["source"], edge["source"])
        edge["target"] = label_map.get(edge["target"], edge["target"])
        count_map[int(edge["source"])] += 1

    for node in node_data:        
        node["count"] = count_map[int(node["id"])]

    data = {
        "nodes": node_data,
        "edges": edges
    }
    return jsonify(data)


# 登入、請求憑證
# 將該ip 的label 變為User
@app.route('/datacenter/request_cert', methods=['POST'])
async def request_cert():
    data = request.get_json()
    ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
    print(f"Request from IP: {ip}")
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # 提取 USER 資料
    user = data.get("user", {})
    # 檢查 user 資訊
    
    # 產生 ID token(JWT)    
    now = datetime.datetime.utcnow()
    payload = {
        'iss': JWT_ISSUER,
        'exp': now + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS),
        'iat': now,
        'sub': user,
    }
    id_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    print(f"JWT ID Token: {id_token}")
    
    # 儲存到Redis ： 使用hash結構
    r.hset(f"user_session:{user}", mapping={
        "ip" : ip,
        "id_token": id_token,
        "login_time": now.isoformat()
    })
    
    # 修改 RPG_FILE 中對應 IP 的 priority 為 "IT"
    with open(RPG_FILE, 'r') as file:
        rpg_data = json.load(file)
        for entry in rpg_data:
            if entry.get("ip") == ip:               
                old_val = entry.get("priority", "Null")
                entry["priority"] = "IT"
                updated = True
                break
    # 寫入回 RPG_FILE
    
    if updated:
        with open(RPG_FILE, 'w') as file:
            json.dump(rpg_data, file, indent=4)
        # 標籤值做改變了，故呼叫reevaluate_dsl 函式，進行重新評估
        # reevaluate_dsl 會先把原本的所有 ip 值
        diff_labels = {0: {"before": old_val, "after": "IT"}}
        await reevaluate_dsl(ip,diff_labels)            
    return jsonify({
        "status": "success",
        "id_token": id_token,
        "message": f"Certificate requested for user {id_token}."
    })

# 查看目前存放在Redis內的所有資訊
@app.route('/datacenter/session/status', methods=['GET'])
def session_status():
    # 尋找所有 user_session:* 的 key
    keys = r.keys("user_session:*")
    
    sessions = []

    for key in keys:
        user_id = key.split(":")[1]  # 取出 user_id
        data = r.hgetall(key)
        sessions.append({
            "user_id": user_id,
            "ip" : data.get("ip"),
            "id_token": data.get("id_token"),
            "login_time": data.get("login_time")
        })

    return jsonify({
        "total_sessions": len(sessions),
        "active_sessions": sessions
    }), 200

# 登出   
@app.route('/datacenter/logout', methods=['POST'])
def logout_user():
    data = request.get_json()
    user_id = data.get("user_id")
    ip = data.get("ip")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400
    
    with open(RPG_FILE, 'r') as file:
        rpg_data = json.load(file)
        for entry in rpg_data:
            if entry.get("ip") == ip:
                print(ip)
                entry["priority"] = "Null"
                updated = True
                break
    if updated:
        with open(RPG_FILE, 'w') as file:
            json.dump(rpg_data, file, indent=4) 

    redis_key = f"user_session:{user_id}"
    if r.exists(redis_key):
        r.delete(redis_key)
        return jsonify({"status": "logged out", "user_id": user_id}), 200
    else:
        return jsonify({"error": "Session not found"}), 404

 
# ✅ 在 Flask 主程式之前就啟動 WebSocket Server（背景執行）
ws_thread = threading.Thread(target=launch_ws_server, daemon=True)
ws_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=False)
