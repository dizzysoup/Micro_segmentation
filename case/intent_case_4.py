# =======================================================================
# 情境3.  脫離業務意圖（Intent-based Violation）偵測
# =======================================================================

import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

RED = '\033[91m'
RESET = '\033[0m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
url = "http://sdn.yuntech.poc.com/datacenter/submit_labels"

HOST1_IP = os.getenv('HOST1_IP', '')
HOST2_IP = os.getenv("HOST2_IP", "")
HOST3_IP = os.getenv("HOST3_IP", "")
# 初始化 RPG ==>  初始化
data = {
    "hostInfo" : {
        "ipv4" : [HOST1_IP,]
    },
    "labels" : {        
        "function" : "Null",
        "priority" : "User",
        "type": "Order",
        "application": "Null",
        "environment" : "Null",
        "security" : "normal"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h1 初始化 (function:Web,type:Order) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h1 初始化 (function:Web,type:Order)❌")

data = {
    "hostInfo" : {
        "ipv4" : [HOST2_IP,]
    },
    "labels" : {
        "function" : "Web",
        "priority" : "Null",
        "type": "Order",
        "application": "Null",
        "environment" : "Null",
        "security" : "Null"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h2 初始化 (function:Database,type:Order) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h2 初始化 (function:Database,type:Order) ❌")
    
data = {
    "hostInfo" : {
        "ipv4" : [HOST3_IP,]
    },
    "labels" : {
        "function" : "Backend",
        "priority" : "Null",
        "type": "Null",
        "application": "Null",
        "environment" : "Null",
        "security" : "Null"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h3 初始化 (function:Backend) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h3 初始化 (function:Backend) ❌")


# ---------------------------------- intent 設置 ----------------------------------------
url = "http://sdn.yuntech.poc.com/datacenter/intent"

    
# Allow 的設置

data = {
    "method" : "allow",
    "egresstype" : "priority",
    "egress" : "User",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Web"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} priority: User  === ICMP ===> function : Web ✅")
else :
    print(f" {GREEN}Allow{RESET} priority: User  === ICMP ===> function : Web  ❌")
    

data = {
    "method" : "allow",
    "egresstype" : "priority",
    "egress" : "User",
    "protocol": "TCP",
    "port": 80,
    "ingresstype" : "function",
    "ingress" : "Web"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} priority: User  === TCP 3306 ===> function : Web ✅")
else :
    print(f" {GREEN}Allow{RESET} priority: User  === TCP 3306 ===> function : Web ❌")

data = {
    "method" : "allow",
    "egresstype" : "priority",
    "egress" : "IT",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Web"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} priority: IT  === ICMP ===> function : Web ✅")
else :
    print(f" {GREEN}Allow{RESET} priority: IT  === ICMP ===> function : Web  ❌")
   
data = {
    "method" : "allow",
    "egresstype" : "priority",
    "egress" : "IT",
    "protocol": "TCP",
    "port": 80,
    "ingresstype" : "function",
    "ingress" : "Web"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} priority: IT  === TCP 80 ===> function : Web ✅")
else :
    print(f" {GREEN}Allow{RESET} priority: IT  === TCP 80 ===> function : Web ❌")

data = {
    "method" : "allow",
    "egresstype" : "priority",
    "egress" : "IT",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Backend"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} priority: IT  === ICMP ===> function : Backend ✅")
else :
    print(f" {GREEN}Allow{RESET} priority: IT  === ICMP ===> function : Backend  ❌")

data = {
    "method" : "allow",
    "egresstype" : "priority",
    "egress" : "IT",
    "protocol": "TCP",
    "port": 22,
    "ingresstype" : "function",
    "ingress" : "Backend"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} priority: IT  === TCP 22 ===> function : Backend ✅")
else :
    print(f" {GREEN}Allow{RESET} priority: IT  === TCP 22 ===> function : Backend ❌")

# Deny 的設置
data = {
    "method" : "DENY",
    "egresstype" : "priority",
    "egress" : "User",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Backend"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} priority: User  === ICMP ===> function : Backend ✅")
else :
    print(f" {RED}Deny{RESET} priority: User  === ICMP ===> function : Backend ❌")


data = {
    "method" : "DENY",
    "egresstype" : "priority",
    "egress" : "User",
    "protocol": "TCP",
    "port": 22,
    "ingresstype" : "function",
    "ingress" : "Backend"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} priority: User  === TCP 22 ===> function : Backend ✅")
else :
    print(f" {RED}Deny{RESET} priority: User  === TCP 22 ===> function : Backend ❌")
