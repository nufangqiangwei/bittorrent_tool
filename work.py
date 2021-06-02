import time
from queue import Queue

from BT_struct import FunctionTable, MyError
from class_models import KademliaCall, RoutingTable, BtHashTable
from seting import SERVER_PORT, TRACKER_SERVER
from utils import get_rand_id, get_nodes_info


def error_message_type(message, address=None):
    print(message)
    print(address)


class MyCallBackFunc(FunctionTable):
    def __init__(self, routingtable: RoutingTable, bthashtable: BtHashTable):
        self.routingtable = routingtable
        self.bthashtable = bthashtable
        self.mynodeid = self.routingtable.mynodeid
        self.response_dict = {
            b'ping': self.ping_response,
            b'get_peers': self.get_peers_response,
            b'find_node': self.find_node_response,
        }
        self.request_dict = {
            b'ping': self.ping_request,
            b'get_peers': self.get_peers_request,
            b'find_node': self.find_node_request,
        }

    def udp_message_response(self, message: dict, addres: tuple):
        self.response_dict.get(message.get(b'q'), error_message_type)(message)

    def udp_message_query(self, message: dict, addres: tuple):
        self.request_dict.get(message.get(b'q'), error_message_type)(message, addres)

    def ping_response(self, data):
        """ping这个请求需要一个超时机制，如果时间到了还没有收到请求就认为该节点超时
        but 我没想好如何做个主动超时机制，所有我就模仿redis的超时机制，先记录这个节点超时了，等查询到这个节点的时候再去删除
        然后又出个新问题，因为我是在nodes满了的时候又需要添加node的时候才回去检测有没有过期的node，这样发起ping的
        那个node必定是被抛弃的"""
        node_id = data['t']['id']
        buckets = self.routingtable.cipher_nodeid(node_id=node_id)
        for node in buckets.nodes:
            if node_id == node.nodeid:
                node.ping_time = int(time.time())
                node.is_ping = False

    def find_node_response(self, data):
        for node in get_nodes_info(data[b"r"][b"nodes"]):
            self.routingtable.append_node(node)

    def get_peers_response(self, data):
        pass

    def ping_request(self, data, addres):
        t = data['t']
        self.routingtable.kademliacall.ping(self.mynodeid, addres, t)

    def get_peers_request(self, data, addres):
        t = data[b't']
        try:
            info_data = self.bthashtable.get(data[b'a'][b'info_hash'])
        except MyError:
            info_data = self.routingtable.get_node(data[b'a'][b'id'])

        self.routingtable.kademliacall.get_peers(addres, '', t, info_data)

    def find_node_request(self, data, addres):
        t = data[b't']
        node_id = data[b'a'][b'target']
        nodes = self.routingtable.get_node(node_id)
        self.routingtable.kademliacall.find_node(self.mynodeid, addres, t, nodes)


this_node_id = get_rand_id()
q = Queue()
communicate = KademliaCall(this_node_id, SERVER_PORT, q)
table = RoutingTable(this_node_id, communicate)
bthashtable = BtHashTable()
MyCallBackFunc(table, bthashtable)
for tracker in TRACKER_SERVER:
    communicate.find_node(node_id=get_rand_id(), addres=tracker)
a = 0
while True:
    try:
        print(q.get(timeout=10))
    except:
        print('队列超时')
    a += 1
    if a == 3:
        print('退出')
        break
print('结束')
