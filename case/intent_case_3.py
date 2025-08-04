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
# 初始化 RPG ==>  初始化
data = {
    "hostInfo" : {
        "ipv4" : [HOST1_IP,]
    },
    "labels" : {        
        "function" : "Null",
        "priority" : "Null",
        "type": "Order",
        "application": "Null",
        "environment" : "Null",
        "security" : "normal"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h1 初始化 (type:Order,security:normal) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h1 初始化 (type:Order,security:normal)❌")

data = {
    "hostInfo" : {
        "ipv4" : [HOST2_IP,]
    },
    "labels" : {
        "function" : "Null",
        "priority" : "Null",
        "type": "Order",
        "application": "Null",
        "environment" : "Null",
        "security" : "normal"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h2 初始化 (type:Order,security:normal) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h2 初始化 (type:Order,security:normal) ❌")

# ---------------------------------- intent 設置 ----------------------------------------
url = "http://sdn.yuntech.poc.com/datacenter/intent"

# Allow 的設置
data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "TCP",
    "port" : "3306",
    "ingresstype" : "type",
    "ingress" : "Order"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} security: normal  ===TCP 3306 ===> type : Order ✅")
else :
    print(f" {GREEN}Allow{RESET} security: normal ===TCP 3306 ===> type : Order ❌")
    
# Allow 的設置
data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "ICMP",
    "ingresstype" : "type",
    "ingress" : "Order"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} security: normal  === ICMP ===> type : Order ✅")
else :
    print(f" {GREEN}Allow{RESET} security: normal === ICMP ===> type : Order ❌")
    

# Deny 的設置
data = {
    "method" : "deny",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "ICMP",
    "ingresstype" : "security",
    "ingress" : "quarantined"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} security: normal ===ICMP===> security : quarantined ✅")
else :
    print(f" {RED}Deny{RESET} security: normal ===ICMP===> security : quarantined ❌")

# Deny TCP 3306 
data = {
    "method" : "deny",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "TCP",
    "port" : "3306",
    "ingresstype" : "type",
    "ingress" : "quarantined"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} security: normal ===TCP 3306===> security : quarantined ✅")
else :
    print(f" {RED}Deny{RESET} security: normal ===TCP 3306===> security : quarantined ❌")

data = {
    "method" : "deny",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "TCP",
    "ingresstype" : "security",
    "ingress" : "quarantined"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} security: normal ===TCP===> security : quarantined ✅")
else :
    print(f" {RED}Deny{RESET} security: normal ===TCP===> security : quarantined ❌")
    
