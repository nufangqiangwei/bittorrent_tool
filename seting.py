# UDP 报文 buffsize
UDP_RECV_BUFFSIZE = 65535
# 服务 host
SERVER_HOST = "0.0.0.0"
# 服务端口
SERVER_PORT = 9090
# while 循环休眠时间
SLEEP_TIME = 1e-5
# 每个节点长度
PER_NODE_LEN = 26
# 节点 id 长度
PER_NID_LEN = 20
# 节点 id 和 ip 长度
PER_NID_NIP_LEN = 24
# 构造邻居随机结点
NEIGHBOR_END = 14
# ping的超时时长 /second
ping_time_out = 15
# K 桶超时时间 /second
K_time_out = 300
# 内置的tracker服务器
TRACKER_SERVER = [("tracker.leechers-paradise.org", 6969),
                  ("tracker.leechers-paradise.org", 6969),
                  ("tracker.coppersurfer.tk", 6969)]
"""
"udp://tracker.open-internet.nl:6969/announce",
"udp://tracker.coppersurfer.tk:6969/announce",
"udp://exodus.desync.com:6969/announce",
"udp://tracker.opentrackr.org:1337/announce",
"udp://tracker.internetwarriors.net:1337/announce",
"udp://9.rarbg.to:2710/announce",
"udp://public.popcorn-tracker.org:6969/announce",
"udp://tracker.vanitycore.co:6969/announce",
"https://1.track.ga:443/announce",
"udp://tracker.tiny-vps.com:6969/announce",
"udp://tracker.cypherpunks.ru:6969/announce",
"udp://thetracker.org:80/announce",
"udp://tracker.torrent.eu.org:451/announce",
"udp://retracker.lanta-net.ru:2710/announce",
"udp://bt.xxx-tracker.com:2710/announce",
"http://retracker.telecom.by:80/announce",
"http://retracker.mgts.by:80/announce",
"http://0d.kebhana.mx:443/announce",
"udp://torr.ws:2710/announce",
"udp://open.stealth.si:80/announce",
"""
