# 使用 PyMySQL 替代 MySQLdb
import pymysql
pymysql.install_as_MySQLdb()
# 绕过版本检查
pymysql.version_info = (2, 2, 1, 'final', 0)