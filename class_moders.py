import bencoder
import socket
import time
from queue import Queue
from threading import Thread

from BT_struct import Node, BucKets
from seting import UDP_RECV_BUFFSIZE, SLEEP_TIME, SERVER_HOST
from utils import get_logger, get_rand_id

"""
Thread = 0
udp_server需要一个线程去接收数据，Thread+1
接收到的数据需要一个线程池和一个分配任务的线程 Thread+1 ThreadPoll+1
超时检测机制 Thread+1
udp-http可以调用udp_server去发送数据

异步实现的方法：（暂定）
	将目标函数拆分两部分，第一部分实现发送前，然后接收返回的 t 值，
	第二部分 发送后，将这部分函数做为一个对象和上一部分接收的t值做为一个对象。送往线程池去等待运行
	
线程池
	线程池接收包含 t值和函数对象 当通过管道接收到一条数据的时候，去查找该数据对应的处理函数，然后执行该函数
	
from urllib3.util import parse_url
parse_url()解析url返回协议方法 host port path args 等属性

socket.gethostbyname 通过host获取ip
"""


class UdpServer:
	def __init__(self, bind_ip, bind_port, q: Queue):
		self.logger = get_logger('udp server')
		self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.udp.bind((bind_ip, bind_port))
		Thread(target=self.recv_response, args=(q,)).start()  # 初始化接收数据线程

	def send_message(self, message: dict, address: tuple, t=None) -> str:
		if t is None:
			message['t'] = self.get_t()
			print(message,address)
			self.udp.sendto(bencoder.bencode(message), address)
			return message['t']
		message['t'] = t
		self.udp.sendto(bencoder.bencode(message), address)
		return message['t']

	@staticmethod
	def get_t() -> str:
		"""
		生成一个唯一的t值，用来标记对应的函数
		这里需要搞个线程共享的东西去保存
		:return:
		"""
		return get_rand_id()

	def recv_response(self, q: Queue):
		"""
		循环接受 udp 数据
		"""
		while True:
			try:
				# 接受返回报文
				data, address = self.udp.recvfrom(UDP_RECV_BUFFSIZE)
				# 使用 bdecode 解码返回数据
				print(data)
				msg = self.decode_message(data)
				# 处理返回信息
				q.put(msg)
				time.sleep(SLEEP_TIME)
			except Exception as e:
				self.logger.warning("接收数据错误 " + " - " + str(e))

	def decode_message(self, data):
		data = bencoder.bdecode(data)
		# bencoder.decode_dict()
		return self.is_type(data)

	def is_type(self, obj):
		"""这里这样解码了之后后面的获取node数据可能会出错"""
		if isinstance(obj, dict):
			return self.dict_obj(obj)

		elif isinstance(obj, list):
			return self.list_obj(obj)

		elif isinstance(obj, bytes):
			return self.bytes_obj(obj)
		elif isinstance(obj, int):
			return int
		else:
			print(type(obj))
			return obj

	def dict_obj(self, obj: dict) -> dict:
		a = {}
		for k, v in obj.items():
			a[self.is_type(k)] = self.is_type(v)
		return a

	def list_obj(self, obj: list) -> list:
		a = []
		for i in obj:
			a.append(self.is_type(i))
		return a

	def bytes_obj(self, obj: bytes) -> str:
		return bencoder.bdecode(obj)

	def __del__(self):
		self.udp.close()


class UdpHttpServer:
	"""
	先暂时不实现这个了，遇到有向tracker发送消息就抛弃
	向tracker服务器地址发送消息，因为tracker服务器一般都是接收的http协议但是它走的却是UDP，
	所以在这里将请求包的数据修改成http协议的格式在调用udp-server去发送消息
	"""

	def __init__(self):
		pass

	def ping(self, node_id: str, url: str):
		pass


class KademliaCall:
	"""http://www.bittorrent.org/beps/bep_0005.html
	t这个字段放到最终发送端去添加，因为多处生成这个字段无法保证它是在以发送出去的数据包当中是不重复的"""

	def __init__(self, mynodeid, server_port, q: Queue):
		self.mynodeid = mynodeid
		self.udpserver = UdpServer(SERVER_HOST, server_port, q)


	def ping(self, node_id: str, addres: tuple, t=None) -> str:
		"""
		{"t":"aa", "y":"q","q":"ping", "a":{"id":"abcdefghij0123456789"}}
		ping这个请求需要一个超时机制，如果时间到了还没有收到请求就认为该节点超时

		Ping请求包含一个参数id，它是一个20字节的字符串包含了发送者网络字节序的nodeID。
		对应的ping回复也包含一个参数id，包含了回复者的nodeID。
		:t 当回复消息的时候需要传递t值回复对方，但是自己主动发送消息的时候不需要传入所以该值应当为None
		"""
		if t is None:
			message = {"y": "q", "q": "ping", "a": {"id": node_id}}
			return self.udpserver.send_message(message, addres)

		message = {"t": "aa", "y": "r", "r": {"id": node_id}}
		self.udpserver.send_message(message, addres, t)

	def find_node(self, node_id: str, addres: tuple) -> str:
		"""
		因为在最开始初始化的时候可能会像tracker发送find_node请求所以添加了个addres选项
		{"t":"aa", "y":"q","q":"find_node", "a":{"id":"abcdefghij0123456789","target":"mnopqrstuvwxyz123456"}}
		:return:
		"""
		message = {"y": "q", "q": "find_node", "a": {"id": self.mynodeid, 'target': node_id}}
		return self.udpserver.send_message(message, addres)

	def get_peers(self, addres: tuple, info_hash: str) -> str:
		"""
		Getpeers与torrent文件的info_hash有关。这时KPRC协议中的”q”=”get_peers”。get_peers请求包含2个参数。
		第一个参数是id，包含了请求node的nodeID。
		第二个参数是info_hash，它代表torrent文件的infohash。
		如果被请求的节点有对应info_hash的peers，他将返回一个关键字values,这是一个列表类型的字符串。
		每一个字符串包含了"CompactIP-address/portinfo"格式的peers信息。
		如果被请求的节点没有这个infohash的peers，那么他将返回关键字nodes，
		这个关键字包含了被请求节点的路由表中离info_hash最近的K个nodes，
		使用"Compactnodeinfo"格式回复。在这两种情况下，关键字token都将被返回。
		token关键字在今后的annouce_peer请求中必须要携带。Token是一个短的二进制字符串。
		参数: {"id"&nbsp;: "<querying nodes id>","info_hash"&nbsp;: "<20-byte infohash of targettorrent>"}
	回复:{"id"&nbsp;: "<queried nodes id>","token"&nbsp;:"<opaque write token>","values"&nbsp;: ["<peer 1 info string>",
			"<peer 2 info string>"]}
	or:{"id"&nbsp;: "<queried nodes id>","token"&nbsp;:"<opaque write token>","nodes"&nbsp;: "<compact node info>"}

	{"t":"aa", "y":"q","q":"get_peers", "a":{"id":"abcdefghij0123456789","info_hash":"mnopqrstuvwxyz123456"}}
	{"t":"aa", "y":"r", "r":{"id":"abcdefghij0123456789", "token":"aoeusnth","values": ["axje.u", "idhtnm"]}}
	{"t":"aa", "y":"r", "r":{"id":"abcdefghij0123456789", "token":"aoeusnth","nodes": "def456..."}}
		:return:
		"""
		message = {"y": "q", "q": "get_peers", "a": {"id": self.mynodeid, "info_hash": info_hash}}
		return self.udpserver.send_message(message, addres)


class RoutingTable:
	"""
	路由和dht四种基本通讯格式文档如下
	http://www.bittorrent.org/beps/bep_0005.html
	"""

	def __init__(self, mynodeid, kademliacall: KademliaCall):
		"""
		使用字典保存所有的K桶
		__buckets_dict = {buckets_munber:<class:BucKets object>}
		"""
		self.__buckets_dict = {}
		self.mynodeid = mynodeid
		self.kademliacall = kademliacall

	def append_node(self, node: Node):
		"""
		1.如果该 K 桶的记录项小于 8个，则直接把 新node(IP address, UDP port, Node ID) 信息插入队列尾部
		2.如果该 K 桶的记录项大于等于 8 个，则选择头部的记录项（假如是节点 原node）进行 RPC_PING 操作
			a.如果 原node 没有响应，则从 K 桶中移除 原node 的信息，并把 新node 的信息插入队列尾部
			b.如果 原node 有响应，则把 原node 的信息移到队列尾部，同时忽略 新node 的信息
		"""
		if node.nodeid == self.mynodeid:
			return
		buckets = self.cipher_nodeid(node.nodeid)

		if node.nodeid in buckets.node_id_set:
			self.append_node(buckets, node, is_add=False)
			return

		if buckets.nodes_munber < 8:
			self.append_node(buckets, node)
			return

		old_node = None
		now_time = int(time.time())
		for bucket_node in buckets.nodes:
			# 因为使用的是类似redis的过期策略，所以每次添加数据的时候需要手动验证是否已经过期了
			if bucket_node.is_ping and (now_time - bucket_node.ping_time > 10):
				# 该节点已经超时了
				self.remove_node(buckets, bucket_node)
				self.append_node(buckets, node)
				return
			if not bucket_node.is_ping and old_node is None:
				# 当这个这个节点没有发送ping请求而且old_node还没有第一个还没有发送ping请求的节点
				old_node = bucket_node
		if old_node is None:
			# 当前k桶的所有节点全部发送ping请求了，但是也都还没超时,暂时没想到做啥，先抛弃这个节点
			return
		self.ping_node(old_node)
		return

	# if not self.kademliacall.ping(old_node.nodeid, (old_node.ip, old_node.port)):
	# 	# ping操作超时，删除该节点将新节点加入
	# 	buckets.nodes.append(node)
	# 	buckets.node_id_set.add(node.nodeid)
	# 	buckets.node_id_set.remove(old_node.nodeid)
	# 	buckets.last_update_time = time.time()
	# 	return
	#
	# buckets.nodes.append(old_node)
	# buckets.last_update_time = time.time()

	def get_node(self, node_id: str) -> list or Node:
		"""
		在路由表中获取给定的node或者最近的八个node
		:param node_id:
		:return:
		"""
		buckets = self.cipher_nodeid(node_id)
		if node_id in buckets.node_id_set:
			for node in buckets.nodes:
				if node_id == node.nodeid:
					return node
		if buckets.nodes_munber == 8:
			return buckets.nodes
		keys_list = list(self.__buckets_dict.keys())
		keys_list.sort()
		return buckets.nodes.extend(self.get_dight_nodes(keys_list, buckets.serial_number, 8 - buckets.nodes_munber))

	def get_dight_nodes(self, keys_list, buckets_index, munber) -> list:
		buckets_index = keys_list.index(buckets_index)
		buckets_muber = keys_list[buckets_index + 1]
		buckets = self.__buckets_dict[buckets_muber]
		if buckets.nodes_munber >= munber:
			return buckets.nodes[0:munber]
		else:
			return buckets.nodes.extend(self.get_dight_nodes(keys_list, buckets_muber, munber - buckets.nodes_munber))

	def cipher_nodeid(self, node_id) -> BucKets:
		"""
		计算目标node应该存在哪一个K桶当中，返回K桶的编号
		:param node_id:
		"""
		mun = 20
		for mynode, targetnode in zip(self.mynodeid, node_id):
			k = bin(mynode ^ targetnode)
			if '1' not in k:
				mun -= 1
				continue
			# 补全到都是八位在进行循环排查
			k = k[2:]
			k = '0' * (8 - len(k)) + k
			for index, i in enumerate(k):
				if '1' == i:
					buckets = self.__buckets_dict.get(mun * 8 - index + 1)
					if buckets is None:  # 这个K桶还未创建的话就创建一个返回
						return self.new_buckets(mun * 8 - index + 1)
					return buckets

	def new_buckets(self, number: int) -> BucKets:
		self.__buckets_dict[number] = BucKets(number)
		return self.__buckets_dict[number]

	@staticmethod
	def remove_node(buckets: BucKets, node: Node):
		buckets.nodes.remove(node)
		buckets.node_id_set.remove(node.nodeid)
		buckets.last_update_time = int(time.time())
		buckets.nodes_munber -= 1

	@staticmethod
	def append_node(buckets: BucKets, node: Node, is_add=True):
		"""
		向K桶添加一个新的node
		:param buckets:K桶对象
		:param node: 需要添加的节点
		:param is_add:  是否是新节点，新节点就在k桶包含的bode这个值上加一
		:return:
		"""
		buckets.node_id_set.add(node.nodeid)
		buckets.last_update_time = int(time.time())
		if is_add:
			buckets.nodes.append(node)
			buckets.nodes_munber += 1
		else:
			buckets.nodes.remove(node)
			buckets.nodes.append(node)

	def ping_node(self, node: Node):
		self.kademliacall.ping(node.nodeid, (node.ip, node.port))
		node.is_ping = True
		node.ping_time = int(time.time())


class DiscoverTimeoutObject:
	"""
	定义十一个列表，每次最新的数据都存在zero列表当中
	每秒将所有的列表交换一次 0->1->2->3->4->5->6->7->8->9 10数据过期删除
	这样zero当中都是最新的数据
	这个线程只做移动数据的操作不进行其他操作，防止出现长时间运行之后时间对不上
	"""

	def __init__(self, q: Queue):
		self.q = q
		self.node_addres = dict()
		self.timelistzero = list()
		self.timelistone = list()
		self.timelisttwo = list()
		self.timelistthree = list()
		self.timelistfour = list()
		self.timelistfive = list()
		self.timelistsix = list()
		self.timelistseven = list()
		self.timelistdight = list()
		self.timelistnine = list()
		self.timelistten = list()

	def run(self):
		while True:
			method, data = self.q.get()
			if method == 'put':
				pass
			else:
				pass
			"""检测是否到检查时间"""
