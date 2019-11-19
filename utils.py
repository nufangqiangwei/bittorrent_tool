# encoding=utf-8
"""
Kademlia协议原理简介
http://www.yeolar.com/note/2010/03/21/kademlia
https://shuwoom.com/?p=813
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from socket import inet_ntoa
from struct import unpack

# 日志等级
from urllib3.util import parse_url

from BT_struct import FunctionTable
from seting import PER_NID_LEN, NEIGHBOR_END, PER_NODE_LEN, PER_NID_NIP_LEN

LOG_LEVEL = logging.INFO


def get_rand_id():
	"""
	生成随机的节点 id，长度为 20 位
	"""
	return os.urandom(PER_NID_LEN)


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


def thread_pool(q: Queue, pool: ThreadPoolExecutor, func_table: FunctionTable):
	"""
	在这里进行异步对收到的消息的处理
	:param q:
	:param pool:
	:param func_table:
	:return:
	"""
	while True:
		data = q.get()
		if data.get(b"y") == b"r":  # 回复
			func_table.udp_message_response(data)
		elif data.get(b"y") == b"q":  # 请求
			func_table.udp_message_query(data)
		elif data.get(b"y") == b"e":  # 错误
			func_table.udp_message_error(data)
		else:
			pass


def get_url_pargs(url: str):
	scheme, auth, host, port, path, query, fragment = parse_url(url)
	return scheme, auth, host, port, path, query, fragment
