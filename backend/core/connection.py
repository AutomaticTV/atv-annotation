from .config import Config
from pymongo import *
from collections import OrderedDict
import logging
try:
    CLIENT = MongoClient(Config.DB_URL, document_class=OrderedDict)
    DB = CLIENT[Config.DB_NAME]
    CLIENT.server_info()
except Exception as e:
    logging.error(e)
    exit()