# =======================================================================
# 情境2.  偵測到該服務模組有 CVE 資安漏洞，暫時下線封鎖
# =======================================================================

import requests
import json



RED = '\033[91m'
RESET = '\033[0m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
url = "http://sdn.yuntech.poc.com/datacenter/submit_labels"
# 初始化 RPG ==>  初始化
data = {
    "hostInfo" : {
        "ipv4" : ["192.168.173.101",]
    },
    "labels" : {        
        "function" : "Web",
        "priority" : "Null",
        "type": "Null",
        "application": "Null",
        "environment" : "Null",
        "security" : "normal"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h1 初始化 (function:Web,security:normal) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h1 初始化 (function:Web,security:normal)❌")

data = {
    "hostInfo" : {
        "ipv4" : ["192.168.173.102",]
    },
    "labels" : {
        "function" : "Database",
        "priority" : "Null",
        "type": "Null",
        "application": "Null",
        "environment" : "Null",
        "security" : "normal"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h2 初始化 (function:Database,security:normal) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h2 初始化 (function:Database,security:normal) ❌")
    
data = {
    "hostInfo" : {
        "ipv4" : ["192.168.173.103",]
    },
    "labels" : {
        "function" : "Honeypot",
        "priority" : "Null",
        "type": "Null",
        "application": "Null",
        "environment" : "Null",
        "security" : "vulnerable"
    }    
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {YELLOW}初始化{RESET} h3 初始化 (function:Honeypot,security:vulnerable) ✅")
else :
    print(f" {YELLOW}初始化{RESET} h3 初始化 (function:Honeypot,security:vulnerable) ❌")
url = "http://sdn.yuntech.poc.com/datacenter/intent"
# Deny 策略

data = {
    "method" : "deny",
    "egresstype" : "security",
    "egress" : "vulnerable",
    "protocol": "ICMP",
    "ingresstype" : "security",
    "ingress" : "normal"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} security: vulnerable ===ICMP===> security : normal ✅")
else :
    print(f" {RED}Deny{RESET} security: vulnerable ===ICMP===> security : normal❌")

data = {
    "method" : "deny",
    "egresstype" : "security",
    "egress" : "vulnerable",
    "protocol": "ICMP",
    "ingresstype" : "security",
    "ingress" : "quarantined"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {RED}Deny{RESET} security: vulnerable ===ICMP===> security : quarantined ✅")
else :
    print(f" {RED}Deny{RESET} security: vulnerable ===ICMP===> security : quarantined ❌")
    
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

# Allow 的設置
data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Web"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} security: normal  ===ICMP===> function : web ✅")
else :
    print(f" {GREEN}Allow{RESET} security: normal ===ICMP===> function : web ❌")
    
# ICMP 
data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Database"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} security: vulnerable ===ICMP===> function : database ✅")
else :
    print(f" {GREEN}Allow{RESET} security: vulnerable ===ICMP===> function : database ❌")

# ICMP vulnerable ICMP => Honeypot
data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "vulnerable",
    "protocol": "ICMP",
    "ingresstype" : "function",
    "ingress" : "Honeypot"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} security: vulnerable ===ICMP===> function : Honeypot ✅")
else :
    print(f" {GREEN}Allow{RESET} security: vulnerable ===ICMP===> function : Honeypot ❌")  
    
# TCP
data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "normal",
    "protocol": "TCP",
    "port": 3306,
    "ingresstype" : "function",
    "ingress" : "Database"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} Type: Order ===TCP 3306===> Function : Database ✅")
else :
    print(f" {GREEN}Allow{RESET} Type: Order ===TCP 3306===> Function : Database ❌")
    

data = {
    "method" : "allow",
    "egresstype" : "security",
    "egress" : "vulnerable",
    "protocol": "TCP",
    "port": 3306,
    "ingresstype" : "function",
    "ingress" : "Honeypot"
}
response = requests.post(url, json=data)
if response.status_code == 200:
    print(f" {GREEN}Allow{RESET} Security: vulnerable ===TCP 3306===> function : Honeypot ✅")
else :
    print(f" {GREEN}Allow{RESET} Security: vulnerable ===TCP 3306===> function : Honeypot ❌")