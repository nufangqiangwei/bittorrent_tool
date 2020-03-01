# encoding=utf-8
"""
Kademlia协议原理简介
http://www.yeolar.com/note/2010/03/21/kademlia
https://shuwoom.com/?p=813
"""
import base64
import hashlib
import logging
import os
from bencoder import bdecode, bencode
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from socket import inet_ntoa, inet_aton
from struct import unpack, pack

# 日志等级
from urllib3.util import parse_url

from BT_struct import Node, FunctionTable, MyError
from seting import PER_NID_LEN, NEIGHBOR_END, PER_NODE_LEN, PER_NID_NIP_LEN

LOG_LEVEL = logging.INFO


def get_rand_id(lens=PER_NID_LEN):
	"""
	生成随机的节点 id，长度为 20 位
	"""
	return os.urandom(lens)


def get_neighbor(target):
	"""
	生成随机 target 周边节点 id，在 Kademlia 网络中，距离是通过异或(XOR)计算的，
	结果为无符号整数。distance(A, B) = |A xor B|，值越小表示越近。

	:param target: 节点 id
	"""
	return target[:NEIGHBOR_END] + get_rand_id()[NEIGHBOR_END:]


def get_nodes_info(nodes):
	"""
	解析 find_node 回复中 nodes 节点的信息

	:param nodes: 节点
	"""
	length = len(nodes)
	# 每个节点单位长度为 26 为，node = node_id(20位) + node_ip(4位) + node_port(2位)
	if (length % PER_NODE_LEN) != 0:
		return []

	for i in range(0, length, PER_NODE_LEN):
		nid = nodes[i: i + PER_NID_LEN]
		# 利用 inet_ntoa 可以返回节点 ip
		ip = inet_ntoa(nodes[i + PER_NID_LEN: i + PER_NID_NIP_LEN])
		# 解包返回节点端口
		port = unpack("!H", nodes[i + PER_NID_NIP_LEN: i + PER_NODE_LEN])[0]
		yield (nid, ip, port)


def get_logger(logger_name):
	"""
	返回日志实例
	"""
	logger = logging.getLogger(logger_name)
	logger.setLevel(LOG_LEVEL)
	fh = logging.StreamHandler()
	fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
	logger.addHandler(fh)
	return logger


def nodemessage_change_string(nodes: list or Node) -> bytes:
	"""
	将传入的node中的node_id node_ip node_port 信息转换成bytes
	:param nodes: [Node,Node]
	:return:
	"""
	return_bytes = bytes
	if isinstance(nodes, list):
		for node in nodes:
			return_bytes += node.nodeid
			return_bytes += inet_aton(node.ip)
			return_bytes += pack("!H", node.port)
	elif isinstance(nodes, Node):
		return_bytes += nodes.nodeid
		return_bytes += inet_aton(nodes.ip)
		return_bytes += pack("!H", nodes.port)
	return return_bytes


def bt_to_hase(file_path):
	"""
	种子转磁链
	:param file_path: 种子地址
	"""
	with open(file_path, 'rb') as f:
		torrent = f.read()
	# 使用b编码去解码这个种子当中的信息
	metadata = bdecode(torrent)
	# 获取种子中的info信息并转换成字符串
	hashcontents = bencode(metadata[b'info'])
	# 使用sha1计算这个字符串的哈希值
	digest = hashlib.sha1(hashcontents).digest()
	# 将哈希值使用b16编码成40位并字母小写变成字符串
	b16Hash = base64.b16encode(digest)
	b16Hash = b16Hash.lower()
	b16Hash = str(b16Hash, "utf-8")
	return 'magnet:?xt=urn:btih:' + b16Hash


def btih_to_sha1(btih: str):
	"""
	磁链转 info_hash
	"""
	sha1_data = base64.b32decode(btih.upper())
	return sha1_data


def get_url_pargs(url: str):
	scheme, auth, host, port, path, query, fragment = parse_url(url)
	return scheme, auth, host, port, path, query, fragment


def thread_pool(q: Queue, pool: ThreadPoolExecutor, func_table: FunctionTable):
	"""
	在这里进行异步对收到的消息的处理
	:param q:
	:param pool:
	:param func_table:
	:return:
	"""
	while True:
		data, addres = q.get()
		if data.get(b"y") == b"r":  # 回复
			pool.submit(func_table.udp_message_response, (data, addres))
		elif data.get(b"y") == b"q":  # 请求
			pool.submit(func_table.udp_message_query, (data, addres))
		elif data.get(b"y") == b"e":  # 错误
			pool.submit(func_table.udp_message_error, (data, addres))
		else:
			pass


def check_node_id(func):
	def check(*args, **kwargs):
		node_id = args[0]
		if len(node_id) != 20:
			raise MyError('node_id的长度不正确，正确的长度应该为20位')
		return func(*args, **kwargs)

	return check
