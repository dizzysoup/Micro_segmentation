import json
import logging
import os 
from dotenv import load_dotenv
from webob import Response  # 加入這行來匯入 Response


from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from acl_rules import parse_acl, update_acl_rules, delete_acl_rules_byip
from ryu.topology.api import get_host  # 引入拓撲 API
from ryu.topology import switches

load_dotenv()

VM_IP = os.getenv("VM_IP", "")
VM_MAC = os.getenv("VM_MAC", "")
USER_IP = os.getenv("USER_IP", "")
USER_MAC = os.getenv("USER_MAC", "")
HOST1_IP = os.getenv("HOST1_IP", "")
HOST2_IP = os.getenv("HOST2_IP", "")
HOST3_IP = os.getenv("HOST3_IP", "")
HOST4_IP = os.getenv("HOST4_IP", "")

HOST1_MAC = os.getenv("HOST1_MAC", "00:00:00:00:00:01")
HOST2_MAC = os.getenv("HOST2_MAC", "00:00:00:00:00:02")
HOST3_MAC = os.getenv("HOST3_MAC", "00:00:00:00:00:03")
HOST4_MAC = os.getenv("HOST4_MAC", "00:00:00:00:00:04")
DPID=int(os.getenv("DPID", 8796758451869)) # 10進制

simple_switch_instance_name = 'simple_switch_api_app'


class SimpleSwitchRest13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    _CONTEXTS = { 'wsgi': WSGIApplication }
    
    dpid = {}
    
     #  手動建立 IP → MAC 對應表
    ip_mac_map = {}
    #  模擬 mac 對 port（依照連線順序手動指定）
    host_ports = { }

    def __init__(self, *args, **kwargs):
        super(SimpleSwitchRest13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.switches = {}
        wsgi = kwargs['wsgi']
        self.switches = {}
        self.ip_mac_map = {
            VM_IP : VM_MAC, # Mininet
            USER_IP: USER_MAC,  # Gateway            
            HOST1_IP: HOST1_MAC,  # h1
            HOST2_IP: HOST2_MAC,  # h2
            HOST3_IP: HOST3_MAC,  # h3
            HOST4_IP: HOST4_MAC,  # h3
        }
        self.host_ports = {
            VM_MAC: 1,  # Mininet
            USER_MAC : 1,
            HOST1_MAC: 2,  # h1
            HOST2_MAC: 3,  # h2
            HOST3_MAC: 4,  # h3
            HOST4_MAC: 5,  # h4
        }
        wsgi.register(SimpleSwitchController, {simple_switch_instance_name: self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        
        self.switches[datapath.id] = datapath
        
        dpid = datapath.id      
        print(f"Switch connected, DPID = {dpid}")   
        self.mac_to_port.setdefault(datapath.id, {})
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # 1️⃣ 其餘一律封鎖（drop）
        match = parser.OFPMatch()  # 匹配所有
        actions = []
        self.add_flow(datapath, 0, match, actions)
        
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=USER_IP, ipv4_dst=VM_IP)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]  
        self.add_flow(datapath, 100, match, actions)
        
        match = parser.OFPMatch(eth_type=0x0800, ipv4_src=VM_IP, ipv4_dst=USER_IP)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]  
        self.add_flow(datapath, 100, match, actions)
        
        #  ARP 泛洪規則
        match = parser.OFPMatch(eth_type=0x0806)
        actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
        self.add_flow(datapath, 200, match, actions)

        
        # 4️⃣ 所有 host 列表（後面迴圈要用）
        hosts = [HOST1_IP, HOST2_IP, HOST3_IP, HOST4_IP] 
        admin_hosts = [VM_IP,USER_IP]
        
        for host_ip in hosts:
            for admin_ip in admin_hosts:
                host_mac = self.ip_mac_map[host_ip]  #針對 ip 取出 mac
                host_port = self.host_ports[host_mac] # 再針對mac 取出port
                
                # 允許 24 → host
                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=host_ip, ipv4_dst=admin_ip)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)] 
                self.add_flow(datapath, 100, match, actions)          

                match = parser.OFPMatch(eth_type=0x0800, ipv4_src=admin_ip, ipv4_dst=host_ip)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]  
                self.add_flow(datapath, 100, match, actions)
                
                match = parser.OFPMatch(eth_type=0x0806, ipv4_src=host_ip, ipv4_dst=admin_ip)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                self.add_flow(datapath, 100, match, actions)
                
                match = parser.OFPMatch(eth_type=0x0806, ipv4_src=admin_ip, ipv4_dst=host_ip)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]  
                self.add_flow(datapath, 100, match, actions)
                
                match = parser.OFPMatch(eth_type=0x88cc, ipv4_src=admin_ip, ipv4_dst=host_ip)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]  
                self.add_flow(datapath, 100, match, actions)
                
                match = parser.OFPMatch(eth_type=0x88cc, ipv4_src=host_ip, ipv4_dst=admin_ip)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                self.add_flow(datapath, 100, match, actions)
        
       
    
        # 載入 其他 DSL 規則 
        self.setup_acl_rules(datapath)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def setup_acl_rules(self, datapath):
        with open("config/acl_rules.txt", "r") as file:
            dsl_rules = file.readlines()

        for rule in dsl_rules:
            rule = rule.strip().split(" ")   
            print(f"寫入流表規則：{rule}")      
            self.setup_flow_for_acl(datapath, rule)
    # 刪除特定IP的所有flows
    def delete_flows_by_ip(self, datapath, ip):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 刪除所有與特定IP相關的flows
        matches = [
            parser.OFPMatch(eth_type=0x0800, ipv4_src=ip),
            parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip),
        ]
        excluded_ips = [VM_IP, USER_IP]
        
        for match in matches:
            for excluded_ip in excluded_ips:
                # 避免刪除 src=ip, dst=excluded 或 dst=ip, src=excluded 的 flow
                if match.get("ipv4_dst") == excluded_ip or match.get("ipv4_src") == excluded_ip:
                    continue
            mod = parser.OFPFlowMod(
                datapath=datapath,
                command=ofproto.OFPFC_DELETE,
                out_port=ofproto.OFPP_ANY,
                out_group=ofproto.OFPG_ANY,
                match=match
            )
            datapath.send_msg(mod)
            self.logger.info(f"🔻 Deleted flow for IP match: {match}")

    def setup_flow_for_acl(self, datapath, parsed_rule):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        
        action = parsed_rule[0]  # allow or deny 
       
        protocol = parsed_rule[1] # TCP , UDP , ICMP
        src_ip = parsed_rule[3]  # Source IP
        dst_ip = parsed_rule[5]  # Destination IP
        
        match = None 
        if protocol == 'TCP' :
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip, ip_proto=6)  # IP 協議 6 是 TCP
        elif protocol == 'UDP':
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip, ip_proto=17)  # IP 協議 17 是 UDP
        elif protocol == 'ICMP':
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip, ip_proto=1)  # IP 協議 1 是 ICMP
        # 根據 action（allow 或 deny）設置動作
        actions = []
        if action == "allow":
            dsc_mac = self.ip_mac_map[dst_ip]  # 針對 ip 取出 mac
            out_port = self.host_ports[dsc_mac]  # 再針對 mac 取出 port            
            # actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),parser.OFPActionOutput(ofproto.OFPP_FLOOD)]  # 允許流量進行
            actions = [parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 100, match, actions)
        elif action == "deny":
            actions = []  # 沒有動作，相當於丟棄該流量        
            self.add_flow(datapath, 999, match, actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        dst = eth.dst
        src = eth.src

        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("Packet in %s %s %s %s", dpid, src, dst, in_port)

        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

class SimpleSwitchController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SimpleSwitchController, self).__init__(req, link, data, **config)
        self.simpl_switch_spp = data[simple_switch_instance_name]

    @route('index', '/', methods=['GET'])
    def index(self, req, **kwargs):
        try:
            with open('templates/index.html', 'r') as file:
                body = file.read()
            return Response(content_type='text/html', body=body)
        except Exception as e:
            return Response(status=500, body="Error loading index.html")
    
    # 新增 "/hosts" 路由，回傳拓撲中所有主機的資訊
    @route('topology', '/ryu/hosts', methods=['GET'])
    def list_topology_hosts(self, req, **kwargs):
        # 從拓撲中獲取所有主機資訊
        all_hosts = get_host(self.simpl_switch_spp, None)  # 獲取所有主機
        for h in all_hosts:
            print(f"[TOPO] host MAC: {h.mac}, IPs: {h.ipv4}, port: {h.port}")
        # 將主機資訊轉換為 JSON 格式
        body = json.dumps([host.to_dict() for host in all_hosts])        
        return Response(content_type='application/json; charset=utf-8', body=body)
    
     # 這裡是新增的 insert_policy API
    @route('insert_policy', '/ryu/policy', methods=['POST'])
    def insert_policy(self, req, **kwargs):
        # 解析 JSON       
        policy_data = json.loads(req.body)       
        print(json.dumps(policy_data, indent=4))
       
        datapath = self.simpl_switch_spp.switches.get(DPID)
        # 進行策略更新等
        update_acl_rules(policy_data)
        # 策略應用
        self.simpl_switch_spp.setup_acl_rules(datapath)
        # 返回成功的回應
        return Response(content_type='application/json; charset=utf-8', body=json.dumps({"status": "success"}))

    # 指定刪除特定IP的policy 
    @route('delete_policy', '/ryu/delete/policy/', methods=['POST'])
    def delete_policy(self, req,  **kwargs):
        body = req.body.decode('utf-8')
        data = json.loads(body)
        rules = data.get("rules", [])
        ip = data.get("ip", None)    
        print(f"刪除的ip為{ip}")
        print(f"要刪除的DSL為: {rules}")
        datapath = self.simpl_switch_spp.switches.get(DPID)
        self.simpl_switch_spp.delete_flows_by_ip(datapath, ip) # 刪除SDN層rules 
        delete_acl_rules_byip(ip) # 刪除DSL層的rules
        # 返回成功的回應
        return Response(content_type='application/json; charset=utf-8', body=json.dumps({"status": "success"}))
       

