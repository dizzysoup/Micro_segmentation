# ==================================================
#  Agent 會向PDP 請求憑證
# ==================================================

import http.client
import json
import argparse
import socket

def get_local_ip():
    try:
        # 嘗試連線到外部地址（不會真的發送資料，只是借用 socket 建立）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def request_cert(user_id: str):
    conn = http.client.HTTPConnection("sdn.yuntech.poc.com")

    payload = json.dumps({
        "user" : user_id        
    })

    ip = get_local_ip()
    
    headers = {
        'Content-Type': 'application/json',
        "X-Forwarded-For" : ip
    }

    URL = f"http://sdn.yuntech.poc.com/datacenter/request_cert"
    try:
        conn.request("POST", URL, body=payload, headers=headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        print(f"[{res.status}] {data}")
        return data
    except Exception as e:
        print(f"Request failed: {e}")
        return None
    finally:
        conn.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Request certificate for a user.")    
    parser.add_argument("--user", required=True, help="User ID to request certificate for")
    args = parser.parse_args()

    request_cert(args.user)
