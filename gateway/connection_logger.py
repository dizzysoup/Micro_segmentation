from netfilterqueue import NetfilterQueue
import datetime
import asyncio
import websockets
import json
import threading

# ===== WebSocket 設定 =====
SDC_WEBSOCKET_URI = "ws://sdn.yuntech.poc.com:8765"  

# ===== 將事件寫入 log.txt =====
def log_event(event):
    
    with open("log.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} | {event}\n")

# ===== 將事件傳送到 WebSocket（非同步）=====
async def send_event_ws(event):
    try:
        async with websockets.connect(SDC_WEBSOCKET_URI) as websocket:
            await websocket.send(json.dumps(event))
            print(f"[→] 傳送事件至 SDC：{event}")
    except Exception as e:
        print(f"[!] WebSocket 傳送失敗：{e}")

# 同步轉非同步的中介（讓 callback 能送出 async 任務）
def send_event_async(event):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(send_event_ws(event))
    else:
        loop.run_until_complete(send_event_ws(event))

# ===== 封包處理 callback =====
def packet_callback(packet):
    payload = packet.get_payload()

    src_ip = ".".join(map(str, payload[12:16]))
    dst_ip = ".".join(map(str, payload[16:20]))
    src_port = int.from_bytes(payload[20:22], byteorder='big')
    dst_port = int.from_bytes(payload[22:24], byteorder='big')
    protocol_num = payload[9]

    if protocol_num == 6 and payload[47] & 0x02:
        event = {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "dst_port": dst_port,
            "protocol": "TCP",
            "event": "new_connection"
        }
        print(f"[+] 偵測連線：{event}")
        log_event(event)
        send_event_async(event)

    packet.accept()

# ===== 啟動 NetfilterQueue =====
nfqueue = NetfilterQueue()
nfqueue.bind(1, packet_callback)

try:
    print("[*] 連線偵測啟動，請確保已設定 iptables 規則")
    nfqueue.run()
except KeyboardInterrupt:
    print("[*] 偵測已中止")
finally:
    nfqueue.unbind()
