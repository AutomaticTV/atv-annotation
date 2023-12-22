import os
import logging
class Config:
    SERVER_PORT = os.environ.get('SERVER_PORT', 5000)
    SECRET_KEY = 'zZV8RFNUoMf27wFzs3K57J3XngsShYAFm04lJjxw'
    # DB_URL = os.environ.get('MONGO_URL', 'mongodb://127.0.0.1:27017')
    DB_URL = os.environ.get('MONGO_URL', 'mongodb://mongo')
    DB_NAME = 'annotation'
    
    BASE_UPLOADS = os.environ.get('UPLOADS_FOLDER','uploads')
    TMP_BASE_UPLOADS = os.path.join(BASE_UPLOADS, 'tmp')
    INPUT_BASE_UPLOADS = os.path.join(BASE_UPLOADS, 'input')
    FTP_BASE_UPLOADS = os.path.join(BASE_UPLOADS, 'ftp')
    OUTPUT_BASE_UPLOADS = os.path.join(BASE_UPLOADS, 'output')

    # Alternative mounted path
    CORPUS_PATH = os.environ.get('CORPUS_FOLDER')

    GET_ANNOTATION_TIMEOUT = 60 * 5 # 5min # 10 #
    FTP_CREDENTIALS_TIMEOUT = 60 * 60 * 24 * 7 # 7 days
    NOT_FINISH_UPLOAD_TIMEOUT = 60 * 60 * 24
    USER_EXPIRATION = 5 * 24 * 3600 # 5 days
    ANNOTATION_FILE = '.xml'


if not os.path.exists(Config.BASE_UPLOADS):
    # Create bases
    os.makedirs(Config.BASE_UPLOADS, exist_ok=True)
    os.makedirs(Config.TMP_BASE_UPLOADS, exist_ok=True)
    os.makedirs(Config.INPUT_BASE_UPLOADS, exist_ok=True)
    os.makedirs(Config.FTP_BASE_UPLOADS, exist_ok=True)
    os.makedirs(Config.OUTPUT_BASE_UPLOADS, exist_ok=True)

    logging.error("Uploads folder do not exist")
    exit()
