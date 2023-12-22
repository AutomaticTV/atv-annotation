from bson import ObjectId
import bson.json_util as json_util
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import requests
import os

ENDPOINTS = [
    os.environ.get('BACKEND_URL', 'http://localhost:5000'),
]

class Login(QDialog):
    def selectionchange(self, i):
        self.labelName.show()
        self.textName.show()

        self.labelPass.show()
        self.textPass.show()

    def __init__(self, parent=None, message=None):
        super(Login, self).__init__(parent)

        if message is not None:
            self.message = QLabel(message)

        self.labelName = QLabel("Username:")
        self.textName = QLineEdit(self)
        
        self.labelPass = QLabel("Password:")
        self.textPass = QLineEdit(self)
        self.textPass.setEchoMode(QLineEdit.Password)
        
        self.buttonLogin = QPushButton('Go', self)
        self.buttonLogin.clicked.connect(self.handleLogin)
        

        self.hor_name = QHBoxLayout()
        self.hor_name.addWidget(self.labelName)
        self.hor_name.addWidget(self.textName)

        self.hor_pass = QHBoxLayout()
        self.hor_pass.addWidget(self.labelPass)
        self.hor_pass.addWidget(self.textPass)

        layout = QVBoxLayout(self)
        if message != "" or message is not None:
            layout.addWidget(self.message)
        layout.addLayout(self.hor_name)
        layout.addLayout(self.hor_pass)
        layout.addWidget(self.buttonLogin)

    def checkLogin(self):
        response, description = Requests.Login.do(self.textName.text(), self.textPass.text())
        if not response:
            QMessageBox.warning(
                self, 'Error', description)

        return response

    def handleLogin(self):
        if self.checkLogin():
            self.accept()

    def closeEvent(self, evnt):
        evnt.ignore()

def LOGIN_CHECK(r):
    if r.status_code == 401:
        json_content = r.json()
        if json_content['error'] == 'Invalid token':
            Login(message="Login expired").exec_()

def CONNECTION_ERROR(func):
    def wrapper_connection(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            q = QMessageBox.warning(None, "Error", "Server not available")
            return wrapper_connection(*args, **kwargs)
    return wrapper_connection

class Requests:
    APP = None
    TOKEN = None
    USERNAME = None

    class Login:
        @staticmethod
        @CONNECTION_ERROR
        def do(username, password, endpoint):
            r = requests.post(
                url=endpoint + '/user/login',
                json={
                'username': username,
                'password': password
            })

            if r.status_code == 200:
                json_content = r.json()
                Requests.USERNAME = username
                Requests.TOKEN = json_content['access_token']
                return True, ""
            else:
                return False, 'Wrong user or password'

    class User:
        @staticmethod
        @CONNECTION_ERROR
        def set_active(active, endpoint):
            r = requests.post(
                url=endpoint + '/user/active', 
                data=json_util.dumps({
                    'active': active
                }),
                headers={
                    'Authorization': 'JWT ' + Requests.TOKEN
                })
            LOGIN_CHECK(r)

            if r.status_code == 200:
                return True, ""
            else:
                return False, 'Error on active user.'

    class Annotation:
        @staticmethod
        @CONNECTION_ERROR
        def get(endpoint):
            r = requests.get(
                url=endpoint + '/job/get/annotation', 
                data={'image_type': 'numpy'},
                headers={
                    'Authorization': 'JWT ' + Requests.TOKEN
                }
            )
            LOGIN_CHECK(r)
            
            if r.status_code == 200:
                #json_content = r.json_content()
                json_content = json_util.loads(r.text)
                json_content = json_content['data']
                if json_content is None:
                    return None, "No annotation available"

                # Parse name, remove first slash
                if json_content['file_path'][0] == '/' or json_content['file_path'][0] == '\\':
                    json_content['file_path'] = json_content['file_path'][1:]

                return json_content, ""
            else:
                return None, "No annotation available"


        @staticmethod
        @CONNECTION_ERROR
        def set(ref_id, data, last_changes, frame_tags, endpoint, roi=None):
            r = requests.post(
                url=endpoint + '/job/set/annotation', 
                json={
                    'ref_id': str(ref_id),
                    'xml': data,
                    'last_changes': last_changes,
                    'frame_tags': frame_tags,
                    'roi': roi
                },
                headers={
                    'Authorization': 'JWT ' + Requests.TOKEN
                }
            )
            LOGIN_CHECK(r)

            if r.status_code == 200:
                json_content = r.json()
                if 'description' in json_content and json_content['description'] is not None:
                    return True, json_content['description'], json_content['status']
                else:
                    return True, None, json_content['status'] if 'status' in json_content else None
                #json_content = r.json_content()
                # """if json_content['status']:
                #     return True, None
                # else:
                #     if 'description' in json_content:
                #         return False, json_content['description']
                #     return False, "Something wrong during annotation save."""
            else:
                json_content = r.json()
                if 'description' in json_content and json_content['description'] is not None:
                    return False, json_content['description'], json_content['error']
                else:
                    return False, "Something went wrong when saving the annotation.", json_content['error']

        """@staticmethod
        @CONNECTION_ERROR
        def check_is_annotated(anno_id):
            r = requests.get(
                url=ENDPOINT + '/job/check/annotation', 
                data={'anno_id': anno_id},
                headers={
                    'Authorization': 'JWT ' + Requests.TOKEN
                }
            )
            LOGIN_CHECK(r)"""
