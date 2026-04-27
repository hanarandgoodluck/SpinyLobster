import multiprocessing

# 绑定地址 - Gunicorn 监听本地 8000 端口，Nginx 反向代理
bind = "127.0.0.1:8000"

# Worker 数量 - 根据 CPU 核心数计算
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 类型 - 同步 worker
worker_class = "sync"

# 线程数
threads = 2

# 超时时间（秒）- AI 处理可能需要较长时间
timeout = 300
keepalive = 5

# 最大请求数 - 防止内存泄漏
max_requests = 1000
max_requests_jitter = 50

# 日志配置 - 使用项目目录避免权限问题
accesslog = "/opt/stardragon/logs/gunicorn_access.log"
errorlog = "/opt/stardragon/logs/gunicorn_error.log"
loglevel = "info"

# 进程命名
proc_name = "stardragon"

# 工作目录
chdir = "/opt/stardragon"

# PID 文件 - 使用项目目录
pidfile = "/opt/stardragon/gunicorn.pid"

# 预加载应用
preload_app = True

# Worker 临时文件目录
worker_tmp_dir = "/dev/shm"

# 优雅重启超时
graceful_timeout = 30
