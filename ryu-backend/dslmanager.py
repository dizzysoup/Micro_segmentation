import json
import requests
import websockets
from dotenv import load_dotenv
import os 
from urllib.parse import quote

load_dotenv()
RPG_FILE = os.getenv("RPG_FILE", "rpg_case_1.json")
# 查詢RPG
def load_rpg(ip):   
    with open(RPG_FILE, 'r') as file:
        data = json.load(file)
    result = next((entry for entry in data if entry["ip"] == ip), None)
    print(result)
    return result

# 根據條件過濾出符合的 IP
def get_matching_ips(type,label):     
    with open(RPG_FILE, 'r') as file:
        data = json.load(file)              
    # 假設：type = "function"  、label = "Web"，
   
    matching_ips = [entry['ip'] for entry in data if entry.get(type, "").lower() == label.lower()]
    return matching_ips

# 把策略更新到ryu  
def update_policy_to_ryu():
    result = []
    with open('dsl.txt', 'r') as dsl_file:
        dsls = dsl_file.readlines()
        
        for dsl in dsls:
            parts = dsl.split("},")
            
            method_and_ips = parts[0].strip().split(" ")            
            method = method_and_ips[0].split("{")[0]  # allow           
            protocol = method_and_ips[0].split("{")[1].split(",")[0] # TCP
            
            egress_ip = method_and_ips[1].split(",")[0]  # 192.168.173.102
            ingress_ip = method_and_ips[2]  # 192.168.173.101
            
            policy = {
                "egress_ip": egress_ip,
                "ingress_ip": ingress_ip,
                "protocol": protocol,
                "method": method
            }
            
            print(policy)
            result.append(policy)
            
            # TCP 是雙向的，所以要加入反向策略
            if protocol == 'TCP' :
                reverse_policy = {
                    "egress_ip": ingress_ip,
                    "ingress_ip": egress_ip,
                    "protocol": protocol,
                    "method": method
                }
                result.append(reverse_policy)
    url = "http://sdn.yuntech.poc.com/ryu/policy"
    print(json.dumps(result,indent=4))
    try:
        # 使用 POST 請求將解析後的結果發送為 JSON
        response = requests.post(url, json=result)
        
        # 檢查回應狀態
        if response.status_code == 200:
            print("Policy successfully updated.")
        else:
            print(f"Failed to update policy. Status code: {response.status_code}")
            print("Response:", response.text)
    
    except requests.exceptions.RequestException as e:
        # 捕捉任何請求異常
        print(f"An error occurred: {e}")

# 把策略更新到iptables
async def update_policy_to_iptables():
    result = []    
    with open('dsl.txt', 'r') as dsl_file:
        dsls = dsl_file.readlines()
        
        for dsl in dsls:
            parts = dsl.split("},")
            
            method_and_ips = parts[0].strip().split(" ")            
            method = method_and_ips[0].split("{")[0]  # allow           
            protocol = method_and_ips[0].split("{")[1].split(",")[0] # TCP
            
            port = parts[1].strip("{}").split(",")[0] # 3306
            if(port == " ") : continue
            
            egress_ip = method_and_ips[1]  # 192.168.173.102 來源
            ingress_ip = method_and_ips[2]  # 192.168.173.103 接收端
            
            policy = {
                "egress_ip": egress_ip,                
                "protocol": protocol,
                "port" : port,
                "method": method
            }            
            result.append(policy)
    # 開啟websocket，要把策略更新到host上的iptables
    
    uri = f'ws://{ingress_ip}:8766'
    print(f"開啟websocket連線:{uri}")
    # 資料發送
    async with websockets.connect(uri) as websocket: 
        # 將字典編碼為JSON
        json_data = json.dumps(result)

        # 透過WebSocket發送JSON訊息
        await websocket.send(json_data)
        print(f'Sent message: {json_data}')

        response = await websocket.recv()
        print(f'Received response: {response}')
    
# 將intent 轉換成dsl
async def transform_intent_to_dsl(intent):  
    
    try:
        with open('dsl.txt', 'r') as existing_file:
            existing_lines = set(existing_file.readlines())
    except FileNotFoundError:
        existing_lines = set()
          
    # 開啟 dsl.txt 準備寫入    
    with open('dsl.txt', 'a') as dsl_file:   
        parts = intent.strip().split(",")  
           
        # 構建 DSL 格式
        # 假設格式為 allow{TCP, 192.168.173.102, 192.168.173.103 },{ 80, (function:Web),(function:Database) }
        egresstype = parts[0].split(" ")[1].split(":")[0]
        egresslabel = parts[0].split(" ")[1].split(":")[1]           
            
        ingresstype =  parts[2].split(" ")[1].split(":")[0]
        ingresslabel = parts[2].split(" ")[1].split(":")[1]
            
        allow = parts[0].split(" ")[0]
        protocol = parts[1].split(":")[0].strip()  # TCP or UDP or ICMP
        egressips = get_matching_ips(egresstype,egresslabel)       
        ingressips = get_matching_ips(ingresstype,ingresslabel)
          
        port = parts[1].split(":")[1].strip()  # 3306  
            
        for egress_ip in egressips:
            for ingress_ip in ingressips:                    
                # 組合為需要的 DSL 格式
                if egress_ip != ingress_ip:
                    dsl_line = f"{allow}{{{protocol}, {egress_ip}, {ingress_ip} }},{{ {port}, ({egresstype}:{egresslabel}),({ingresstype}:{ingresslabel}) }}\n"
                    if dsl_line not in existing_lines:
                       dsl_file.write(dsl_line)
    if protocol == 'ICMP' :      
        update_policy_to_ryu() # policy 更新到RyuController
    if protocol == 'TCP' :
        await update_policy_to_iptables() # policy 更新到iptables
        update_policy_to_ryu() # policy 更新到RyuController
        

# 將intent 轉換成dsl (特定ip)
async def transform_intent_to_dsl_ip(intent,ip):  
   
    try:
        with open('dsl.txt', 'r') as existing_file:
            existing_lines = set(existing_file.readlines())
    except FileNotFoundError:
        existing_lines = set()
          
    # 開啟 dsl.txt 準備寫入    
    with open('dsl.txt', 'a') as dsl_file: 
        # deny security:normal, TCP:3306, security:quarantined 
        parts = intent.strip().split(",")  
        # deny security:normal  TCP:3306 type:quarantined  
        
           
        # 構建 DSL 格式
        # security
        egresstype = parts[0].split(" ")[1].split(":")[0]
        # normal
        egresslabel = parts[0].split(" ")[1].split(":")[1]           
        #  type:quarantined 
        ingresstype =  parts[2].split(" ")[1].split(":")[0]
        ingresslabel = parts[2].split(" ")[1].split(":")[1]
            
        allow = parts[0].split(" ")[0]
        protocol = parts[1].split(":")[0].strip()  # TCP or UDP or ICMP
        egressips = get_matching_ips(egresstype,egresslabel)       
        ingressips = get_matching_ips(ingresstype,ingresslabel)
        
        print("鎖定意圖為" + intent)
        print("留出ip有")
        print(egressips)
        print("留入ip有")
        print(ingressips)
        
        port = parts[1].split(":")[1].strip()  # 3306  
            
        for egress_ip in egressips:
            for ingress_ip in ingressips:                    
                # 組合為需要的 DSL 格式，且該條目至少要跟目標ip一致
                if egress_ip != ingress_ip and (egress_ip == ip or ingress_ip == ip):
                    dsl_line = f"{allow}{{{protocol}, {egress_ip}, {ingress_ip} }},{{ {port}, ({egresstype}:{egresslabel}),({ingresstype}:{ingresslabel}) }}\n"
                    print("寫入的DSL規則為")
                    print(dsl_line)
                    if dsl_line not in existing_lines:
                       dsl_file.write(dsl_line)
    if protocol == 'ICMP' :      
        update_policy_to_ryu() # policy 更新到RyuController
    if protocol == 'TCP' :
        await update_policy_to_iptables() # policy 更新到iptables
        update_policy_to_ryu() # policy 更新到RyuController
        

# 重新評估DSL 的規則
# 當一個 IP 的 Label 改變，就重新產生這個 IP 的所有 DSL，避免規則過期而未撤銷
async def reevaluate_dsl(ip,deff_labels):
    print("改變的標籤為")
    print(deff_labels)
    
    with open('dsl.txt', 'r') as dsl_file:
        dsl_lines = dsl_file.readlines()
    # ➤ 尋找受影響規則
    affected_rules = []
    
   # 1️⃣ 找出與該 IP 有關的 DSL 規則
    affected_rules = [line for line in dsl_lines if ip in line]
    print("改變的DSL為")
    print(affected_rules)
    
    # Ryu 把 該ip 的條目全數刪除
  
    try:
        url = f"http://sdn.yuntech.poc.com/ryu/delete/policy/"
        response = requests.post(url , json={"ip" : ip,"rules" : affected_rules})
        if response.status_code == 200:
            print(f"🗑 Removed DSL: {affected_rules}")
        else:
            print(f"⚠️ Failed to remove DSL: {affected_rules} ({response.status_code})")
    except Exception as e:
        print(f"⚠️ Error contacting Ryu: {e}")
    
    # 2️⃣ 移除受影響的規則
    updated_dsl_lines = [line for line in dsl_lines if line not in affected_rules]

    with open('dsl.txt', 'w') as dsl_file:
        dsl_file.writelines(updated_dsl_lines)
    print(f"[INFO] 已從 DSL 中移除與 {ip} 相關的規則")
    
    # 3️⃣ 重新產生該 IP 的所有 DSL(從IP、RPG、對應Intents)    
    with open('intent.txt', 'r') as intent_file:
        intents = intent_file.readlines()
    print(f"重新寫入{ip}的DSL")
    for intent in intents:
        await transform_intent_to_dsl_ip(intent,ip) # intent 轉換成DSL (只轉換特定ip)