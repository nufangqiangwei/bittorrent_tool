import time
from queue import Queue

from BT_struct import FunctionTable
from class_moders import KademliaCall, RoutingTable
from seting import SERVER_PORT, TRACKER_SREVER
from utils import get_rand_id, get_nodes_info


class MyCallBackFunc(FunctionTable):
	def __init__(self, time_out_q: Queue, routingtable: RoutingTable):
		super(FunctionTable, self).__init__()
		self.ping_timeout_q = time_out_q
		self.routingtable = routingtable
		self.mynodeid = self.routingtable.mynodeid
		self.response_dict = dict(
			ping=self.ping_response,
			get_peers=self.get_peers_response,
			find_node=self.find_node_response,
		)
		self.request_dict = dict(
			ping=self.ping_request,
			get_peers=self.get_peers_request,
			find_node=self.find_node_request,
		)

	def udp_message_response(self, message: dict):
		self.response_dict.get(message.get(b'q'))(message)

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
		for node in get_nodes_info(data["r"]["nodes"]):
			self.routingtable.append_node(node)

	def get_peers_response(self, data):
		pass

	def ping_request(self, data, addres):
		t = data['t']
		self.routingtable.kademliacall.ping(self.mynodeid, addres, t)

	def get_peers_request(self, data, addres):
		pass

	def find_node_request(self, data, addres):
		node_id = data['a']['target']
		self.routingtable.get_node(node_id)


def init():
	this_node_id = get_rand_id()
	q = Queue()
	communicate = KademliaCall(this_node_id, SERVER_PORT, q)
	table = RoutingTable(this_node_id, communicate)

	return q, communicate


q, communicate = init()
for tracker in TRACKER_SREVER:
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
