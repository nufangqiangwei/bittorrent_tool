"""
node的id是20位的一个对象,将这20位的对象转换成160位的二进制数据
然后对这160位的二进制数据进行异或运算，就是同位上的数字相同就为0，不同就为1
然后对这个运算的结果计算第一位是1的位数，这个位数减1就是这个node应该在的K桶
因为所有的距离计算都是以自己的node_id做为起点，所以位数越高的K桶就是离自己越远的
每个K桶只储存八个node，当向这个K桶添加node的时候如果没有满就在末尾添加
满了的话就看有没有失效的node，没有失效的就将这个node抛弃
"""


class Node:
	def __init__(self, nodeid, ip, port, now_time):
		self.nodeid = nodeid
		self.ip = ip
		self.port = port
		self.last_activity_time = now_time  # Timestamp
		self.is_ping = False  # 是否之前对这个节点发送ping消息
		self.ping_time = now_time  # Timestamp 发送ping消息的时间


class BucKets:
	"""
	因为对每个节点的ping是异步实现的，所有需要我去额外的维护一个字典 self.new_node 就是待加入的列表，
	如果那个节点超时就将新的节点加入到最新的nodes中
	{<ping node id>：new node}
	"""

	def __init__(self, serial_number):
		self.serial_number = serial_number
		self.nodes = list()
		self.nodes_munber = 0
		self.node_id_set = set()
		self.last_update_time = None  # Timestamp
		self.new_node = dict()


class FunctionTable:
	"""
	回调函数表当中应该包含这些函数
	UDP 数据包
		q: 别人向我的查询数据包
		r: 我向别人查询的数据包的回复
		e: 我向别人的查询别人发生的错误
	UDP-HTTP 数据包
		待定
	HTTP 数据包
		待定
	"""

	def __init__(self):
		self.request = dict()

	def udp_message_query(self, message: dict):
		"""别人向我的查询数据包"""
		pass

	def udp_message_response(self, message: dict):
		"""我向别人查询的数据包的回复"""
		pass

	def udp_message_error(self, message: dict):
		"""我向别人的查询别人发生的错误"""
		pass


class MyError(Exception):
	def __init__(self, strmessage):
		print(strmessage)
