from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pymysql
import config

# 因 MySQLDB 不支持 Python3，使用 pymysql 扩展库代替 MySQLDB 库
pymysql.install_as_MySQLdb()

# 初始化 web 应用
app = Flask(__name__, instance_relative_config=True)
app.config['DEBUG'] = config.DEBUG

# 设定数据库链接
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://{}:{}@{}/flask_demo'.format(config.username, config.password,
                                                                             config.db_address)

# 初始化 DB 操作对象
db = SQLAlchemy(app)

# 添加飞书 Webhook 配置（如果需要从配置文件读取）
app.config['FEISHU_WEBHOOK_URL'] = os.environ.get('FEISHU_WEBHOOK_URL')

# 加载控制器
from wxcloudrun import views

# 加载配置
app.config.from_object('config')