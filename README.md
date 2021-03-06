# bt协议的实现
    目标bittorrent协议中 0003、0005、0009、0010规定的实现
## BT下载流程介绍：
    现在我们使用BT下载的时候一般使用得都是磁链下载，什么你不知道什么是磁链？？？
    来我来告诉你磁链它一般长这样
> magnet:?xt=urn:btih:546d02a715638f59846569d1e9606abafa637e0f
    
    也有长这样 
> 546d02a715638f59846569d1e9606abafa637e0f

    还有这样的
![cmd-markdown-logo](https://ww1.sinaimg.cn/bmiddle/b33c7fddly1g93gs9p4awj207f07ddh9.jpg)

    当然这些都是可以在BT下载器去下载你想要的东西 :smirk:
    磁力链的格式如下一般来讲，一个磁力链接只需要上面两个参数即可找到唯一对应的资源。
    也有其他的可选参数提供更加详细的信息。
    
* magnet：协议名。
* xt：exact topic 的缩写，表示资源定位点。BTIH（BitTorrent Info Hash）表示哈希方法名，这里还可以使用 SHA1 和 MD5。这个值是文件的标识符，是不可缺少的。
* dn：display name 的缩写，表示向用户显示的文件名。
* tr：tracker 的缩写，表示 tracker 服务器的地址。
* kt: 关键字，更笼统的搜索，指定搜索关键字而不是特定文件。
* mt：文件列表，链接到一个包含磁力链接的元文件 (MAGMA - MAGnet MAnifest）。
    
    
    当我们拿到一个磁力链的时候，就可以拿着这个磁链的btih值去DHT网络去询问谁有这个hash值
    的对应文件，当DHT网络中的莫个人说我存有这个btih值的对应文件。我们就可以去向他请求
    下载这个hash值对应的种子文件，当然我们在DHT网络中查询的时候不是直接拿着这个btih值去询问
    因为这个btih的值是Base16编码之后的结果，我们需要将它进行Base16解码成20位的info_hash值去查询的
    这个可以看我的代码中 utils.btih_to_sha1 这个函数是怎么抓换的。
    当然这一步骤也可以不再DHT网络中查找这个种子，而是在一些有存有info_hash与种子对应网站去直接查询下载，
    比如迅雷，比特彗星，itorrents.org这些网站去查询，不过就是不多罢了。
    其实还有个更好的的方法，找个老司机把他的种子库拖出来就好了 :satisfied:
    
    
    我们下载除了磁力链还有种子，这两个最大的区别就是，我们拿到种子解析完种子就可以直接去下载了，但是
    磁力链我们还是需要现在各种渠道通过这个种子的info_hash值去查到这个种子然后下载下来，
    才能解析这个种子中包含的文件列表信息，最直观的感受就是当你使用迅雷兴建下载任务的时候，如果是使用磁力链新建下载任务，
    他会先有正在下载种子的过程，只有下载种子成功了你才能看见这个磁链中包含的文件信息。当我们拿到种子当中的问文件信息的时候，
    就可以拿着这些文件的hash值去相别人询问有没有这个文件，找到一群志同道合的网友了之后，你们就可以愉快的交换一些不可描述的东西啦。
[种子与磁链的区别](#jump)
    
### DHT网络
#### DHT网络全名是 [Distributed Hash Table](https://zh.wikipedia.org/wiki/%E5%88%86%E6%95%A3%E5%BC%8F%E9%9B%9C%E6%B9%8A%E8%A1%A8) 
      是一个分布式hash表，我们现在每个下载者都是要先连接这个网络成为这个网络中的一分子就是我们说的node，这时候你就需要一个介绍人，
      将你介绍到这个网络当中，就好比你知道有一个神奇的地方，但是这个地方未注册的人是不允许进去，除非有人带你才能进去
      这个介绍人只要是这个地方的会员就可以了，无论是高级还是普通的会员都行。
      那么DHT网络当你需要加入的时候，你需要先知道一个存在这个网络当中的一个node，然后向他发送find_node请求，提取返回结果当中的
      node，重复上面的操作，当你完善了你的路由表之后就可以进行寻找资源的操作了。
#### KRPC 协议
    我们DHT网络中基本的消息发送遵循KRPC协议。KRPC协议包含四种基本消息ping,find_node,get_peers,announce_peer,
    消息的数据类型是字典。每个消息都包含两个必有的字段 t 和 y 这两个字段。
    t这个字段对应的数据是字符串数据类型，数据内容是有发送者生成的一个短字符串，用来标记发送者对外发送的每一条数据，
    方便在接收到消息时候可以查找自己发送的数据，因为协议要求我们在回应消息的时候需要将这个t字段原封不动的返回去。
    y 这个字段对应的数据有三种： 
     1.q标记这个数据是别人的请求数据、 
     2.r 标记这个数据是别人对我之前请求得响应、
     3.e 标记这个数据是别人对我的请求响应出现错误、
更多规范请查看这里 [bep_0005规范](http://www.bittorrent.org/beps/bep_0005.html)
    
    目前该脚本的KademliaCall类实现了以上四种主要的消息发送与回复的接口函数签名如下
* ping : 该消息主要是验证要查询的节点是否存活
         def ping(node_id: str, addres: tuple, t=None) -> str: node_id 
         需要ping的节点id addres节点的ip与port t如果是回复时使用将接收到别人的t值填入该参数
* find_node : 该消息是向别的节点查询是否有查询节点的信息
         def find_node(node_id: str, addres: tuple, t=None, nodes=None) -> str:
         前三个参数同上 第四个参数是在回复别人消息时使用 填入的是一个列表，列表中的对象是Node对象
* get_peers : 该消息是向别的节点查询想要下载的资源
         def get_peers(addres: tuple, info_hash: str, t=None, nodes=None) -> str:
         相同的参数名是与上方的参数是相同的作用，info_hash 该参数是向外查询的时候需要传入的资源的hash值20位长度的字符串
* announce_peer :该消息是当别人知道了我之前查询的资源信息时给我的回复
         announce_peer(self, addres: tuple, node_id: str, t=None, info_hash=None, token=None, implied_port=None,port=None) -> str
         info_hash资源的sha1值  get_peers这个请求中获得的token值 当implied_port存在时候port可以不存在
      
      
      以上的四个四个函数的返回值均是t值，需要自己去处理如何保存和查询
#### 路由表 RoutingTable
    每个节点都需要维护的一个路由表，这个路由表类似于前端二叉树。这个二叉树的构建使用node_id生成160位的（bit），
    在或得到一个新的node时将这个node的id与自己的id生成160位的（bit）进行异或（ XOR ）运算，使用运算的结果构建成一个有
    160层的前端二叉树，每一个node都是这个二叉树上的一个叶子。但是因为这个二叉树过于庞大因为这个一共有2^160次方个node可以存储
    可是我们不需要这么多，所以我们对这个二叉树分成160个K桶，有没有发现这个数字熟悉，对你没猜错，这个K桶的划分是当这个二叉树
    从顶层开始到自身节点这里每分叉一次就出现一个新的K桶，就比如当规定当在得到异或运算的结果后从第一位开始取数，当这位数字
    是1这个二叉树就向左分叉，0这个二叉树就向右分叉一直到最底层，这样我们得到一个二叉树，
    例：异或运算结果是'0111011000'这里我仅用十位来演示 这个结果按上面的规则来排列的话我们得到的就是一个十层的二叉树，
    因为0000000000结果是自身节点，所以从下标为0开始有1就是一个新的k桶生成，这样我们就得到十个k桶。160位的同理可得出160个K桶
    bep_0005规范中规定我们每个k桶最多存储8个节点，当有新的节点需要加入这个k桶的时候有三种情况：k桶没满，就直接添加。k桶满了
    就将未活跃时长最长的节点发送ping请求，如果未响应就该节点移除，将新节点添加进来，如果对ping响应了就丢弃新节点将刚
    ping的那个节点活跃时间标记
### 资源与peers对应表
    这个bittorrent协议中没有规定如何存储，所以这个你可以在数据库存储也可以自己实现存储，我这里是使用的和路由表一样的存储
    方法，使用一个hash表将所有的数据存储子叶子中 具体可以看class_models.BtHashTable,你也可以不使用自己去调用数据库去实现
    BtHashTable该类实现了五种方法 add get delete revise count 分别是 曾加 查询 删除 修改 获得存储的总数
### 种子和磁链有何不一样
    种子和磁链最大的区别就是种子一般当中内置有知道资源所在位置的TRACKER服务器的地址，这样当你去下载资源的时候可以直接去
    找有该资源的节点，省去在网络中查询的时间。
    磁链从网络中获取到的种子也只有种子info信息，就是种子当中的文件列表信息，其他的信息都是没有的
    而且与TRACKER服务器通信和DHT网络中通信是不同的
    TRACKER 服务器只支持thhp/https协议通信，所以你看见的TRACKER地址中协议名是http/https 
    但是你还会看见一个叫UTP的，
   [UTP](http://www.bittorrent.org/beps/bep_0029.html)详细介绍在这里
    
    
## 使用介绍
    我这个使用的时候需要你 先创建这个类KademliaCall对象它需要从参数有node_id、启动端口，一个队列对象
    然后在创建这个类RoutingTable的对象它需要的参数有node_id、KademliaCall的对象
    然后根据你需要可以创建BtHashTable去存储info_hash
    接下来继承FunctionTable这个类并改写当中的方法去分别处理接收的数据，注意这里都是在一个线程池中去处理的，
    所以你的主线程是无法直接获取接收到的数据内容。
    然后创建一个线程池和一个新的线程
    新线程执行utils.thread_pool这个函数 这个函数需要的参数有：之前创建KademliaCall类对象时候传入的队列对象、线程池对象、
    和你继承FunctionTable类的实例。
    至此所有的工具创建完毕~(￣▽￣)~*
    重点介绍一下FunctionTable这个类，这个类主要做的事情是处理所有的接收到的数据。当有新数据到来时候会判断是何种数据，
    然后调用该类原有的方法去执行。目前仅实现三种别的节点发来的数据，别的节点对自己之前请求的响应，和错误三种。
    TRACKER的通信尚未实现请等待后续更新，或者你帮我写一下(/▽＼) 。
    不明白的地方可以联系我 邮箱地址是qinglianjushi.libai@gmail.com

###修改备注
    这几天重新去bt官网看了bt协议，发现之前一些思路有问题，不适合去调用，所以现在把当中的路由表（RoutingTable），
    bt资源表（BtHashTable），定时器（TimingWhell），这三个类单个拿出来分别做为一个个单独的服务去执行，这样如果有多个下载
    者，或者种子爬虫可以不需要维护这些内容，只需要去调用这些服务就可以了，这些调用者只需要创建一个对外的通信接口就好了。
    而且这样单进程去执行这三个类也不需要去考虑多进程的资源安全问题了。至于调用这三个服务的方法是每个服务在初始化完成后会
    有一个对外管道，当需要调用服务的时候向这个管道发送消息，这个消息当中包含一个调用者自己创建的管道去接收服务的结果，
    如不需要结果就可以不传入自己的管道，这样每个进程只需要一个管道就可以了。这个我可以同时有多个下载者在同时下载，
    而不需要每个下载者都去维护这三个功能。
    先就这样先备注一下，先找工作，等有时间在把这个实现。