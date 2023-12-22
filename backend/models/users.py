from bson.objectid import ObjectId
import hashlib

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.connection import CLIENT, DB


"""
    CLASS
"""
class User(object):
    ADMIN, ANNOTATOR = range(2)

    def __init__(self, username, password, group=None, ref_id=None, active=None, enable=True):
        self.ref_id = ref_id
        self.username = username
        self.password = password
        self.active = active
        self.enable = enable

        if group is None:
            group = User.ADMIN
        self.group = group

    def __str__(self):
        return self.__repr__()

    def __repr__(self, ):
        return str(self.dict())

    def dict(self):
        return {
            '_id': self.ref_id,
            'username': self.username,
            'password': self.password,
            'group': self.group,
            'active': self.active,
            'enable': self.enable
        }

    @staticmethod
    def parse(user_dict):
        return User(
            ref_id=user_dict['_id'],
            username=user_dict['username'],
            password=user_dict['password'],
            group=user_dict['group'],
            active=user_dict['active'],
            enable=user_dict['enable']
        )

    @staticmethod
    def get(**kwargs):
        if 'ref_id' in kwargs:
            if isinstance(kwargs['ref_id'], str):
                kwargs['ref_id'] = ObjectId(kwargs['ref_id'])
            kwargs['_id'] = kwargs['ref_id']
            del kwargs['ref_id']

        user = DB.users.find_one(kwargs)
        if user is None:
            return None
        
        user['ref_id'] = user['_id']
        del user['_id']
        
        return User(**user)

    def put(self):
        try:
            with CLIENT.start_session() as session:
                    with session.start_transaction():
                        DB.users.create_index([("username", 1)], unique=True)
                        #if DB.users.find({'username': self.username}, {"_id": 1}).count() > 0:
                        #    raise IndexError('User already exists')
                        #else:
                        user_dict = self.dict()
                        if self.ref_id is None:
                            del user_dict['_id']
                        DB.users.insert_one(user_dict)
                        return True
        except:
            return False

    @property
    def id(self):
        return self.ref_id

    @staticmethod
    def cypher(x):
        return hashlib.sha224(x.encode('utf-8')).hexdigest()

    @staticmethod
    def create(username, password, group):
        return User(username, password, group=group).put()

    @staticmethod
    def change_password(ref_id, password):
        try:
            ref_id = ObjectId(ref_id)
            with CLIENT.start_session() as session:
                    with session.start_transaction():
                        DB.users.update_one({'_id': ref_id}, {'$set': {'password': password}})
                        return True
        except:
            return False
    
    @staticmethod
    def list(group=None, list_password=False):
        dict_info = {}
        if group is not None:
            dict_info['group'] = int(group)
        dict_info['$or'] = [{'enable': {'$exists': False}}, {'enable': True}]

        users = list(DB.users.find(dict_info))
        for u in users:
            if not list_password:
                del u['password']
        
        return users

    @staticmethod
    def set_active(ref_id, active):
        try:
            ref_id = ObjectId(ref_id)
            with CLIENT.start_session() as session:
                    with session.start_transaction():
                        DB.users.update_one({'_id': ref_id}, {'$set': {'active': active}}, upsert=True)
                        return True
        except:
            return False

    @staticmethod
    def toggle(user_id, enable):
        try:
            with CLIENT.start_session() as session:
                with session.start_transaction():
                    DB.users.update_one({'_id': user_id}, {'$set': {'enable': enable}})
            return True
        except:
            return False