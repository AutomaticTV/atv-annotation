# Dependences
import hmac
from flask import Flask, Response, request, current_app, abort
from flask_cors import CORS
from datetime import datetime, timedelta
from flask_jwt import JWT, JWTError, jwt_required, current_identity, _jwt
from werkzeug.exceptions import HTTPException
from functools import wraps, partial
import os
import uuid
import traceback
from pyunpack import Archive
import pymongo
import glob2
import glob
import logging

# Core
from core.config import Config
from core.misc import json_util, Timer, is_annotation, get_annotation
from core.connection import CLIENT, DB
from core import cron
from core.ftp_daemon import FTP_AUTH

# Models
from models.jobs import *
from models.users import *
from models.preferences import Preferences

# Queue
from queue_list import Queue

# Pipeline
from pipeline.processes import Preprocess, Postprocess, GetFileProcess, SetFileProcess

"""
    DEFINE SYMLINK FOLDER OUTPUT
"""
try:
    os.unlink(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output'))
except:
    pass
os.symlink(Config.OUTPUT_BASE_UPLOADS, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output'))

def remove_if_empty(folder_path):
    if os.path.exists(folder_path) and len(os.listdir(folder_path)) == 0:
        shutil.rmtree(folder_path)

# Start APP
app = Flask(__name__)
CORS(app)
queue = Queue()
Job.queue = queue

def Response_OK(description="", data={}, status_code=200, status=""):
    return Response(json_util.dumps({'description': description, 'data': data, 'status_code': status_code, 'status': status}), status=status_code, mimetype='application/json')

def Response_ERROR(description="", error="", status_code=401):
    return Response(json_util.dumps({'description': description, 'error': error, 'status_code': status_code}), status=status_code, mimetype='application/json')

"""
==========================================0
    USERS
==========================================0
"""
#from werkzeug.security import safe_str_cmp
from functools import wraps
def authenticate(username, password):
    data = json_util.loads(request.data)
    user = User.get(username=username)
    logging.debug(f"Trying to authenticate user {username} with password {password}")
    logging.debug(f"Stored user and password are {user.username} and {user.password}")
    if not (user and hmac.compare_digest(user.password.encode('utf-8'), User.cypher(password).encode('utf-8'))):
        return

    if 'group' in data and data['group'] != user.group:
        raise JWTError('Bad Request', 'Invalid group')

    if not user.enable:
        raise JWTError('Bad Request', 'Removed user')

    user.ref_id = str(user.ref_id)
    return user

def identity(payload):
    try:
        user_id = payload['identity']
        user = User.get(ref_id=user_id)
        if user is None:
            return None
    except:
        return None

    user.ref_id = str(user.ref_id)
    return user

def group_decorator(group=None, groups=[]):
    if group is not None:
        groups = [group]
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if current_identity.group not in groups:
                raise JWTError('Bad Request', 'Invalid group')
            return fn(*args, **kwargs)
        return decorator
    return wrapper


# User create route
@app.route('/user/create', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def user_create():
    try:
        data = json_util.loads(request.data)
        response = User.create(data['username'], User.cypher(data['password']), data['group'])
        if response:
            return Response_OK(description="Successful user creation")
        else:
            return Response_ERROR(description="Error during user creation", error="error_user_creation")
    except Exception as e:
        return Response_ERROR(description="Error during user creation", error="error_user_creation_duplicated")

# User list
@app.route('/user/list', methods=["GET"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def user_list():
    try:
        response = User.list(group=request.args.get('group'))
        return Response_OK(description="Successful user list", data=response)
    except Exception as e:
        return Response_ERROR(description="Error during user list", error="error_user_list")


# User change password
@app.route('/user/change_password', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def user_change_password():
    try:
        data = json_util.loads(request.data)
        response = User.change_password(data['user_id'], User.cypher(data['password']))
        if response:
            return Response_OK(description="Successful user password changed", data=response)
        else:
            return Response_ERROR(description="Error during user password change", error="error_user_change_password")
    except:
        return Response_ERROR(description="Error during user password change", error="error_user_change_password")


# User change password
@app.route('/user/active', methods=["POST"])
@jwt_required()
@group_decorator(groups=[User.ADMIN, User.ANNOTATOR])
def set_active():
    try:
        data = json_util.loads(request.data)
        response = User.set_active(current_identity.ref_id, data['active'])
        return Response_OK(description="Error during set activation", data=response)
    except:
        return Response_ERROR(description="Error during set activation", error="error_user_active")

# User remove
@app.route('/user/toggle', methods=["POST"])
@jwt_required()
@group_decorator(groups=[User.ADMIN, User.ANNOTATOR])
def user_toggle():
    data = json_util.loads(request.data)
    response = User.toggle(data['user_id'], data['enable'])
    if response:
        return Response_OK(description="Successful user toggle")
    else:
        return Response_ERROR(description="Error during toggle user", error="error_user_toggle")

# User configuration JWT
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['JWT_AUTH_URL_RULE'] = '/user/login'
app.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=Config.USER_EXPIRATION)
jwt = JWT(authentication_handler=authenticate, identity_handler=identity)
def __handler():
    data = request.get_json()
    username = data.get(current_app.config.get('JWT_AUTH_USERNAME_KEY'), None)
    password = data.get(current_app.config.get('JWT_AUTH_PASSWORD_KEY'), None)
    group = data.get('group', None)

    if not (username and password and ((len(data) == 3 and group is not None) or len(data) == 2)):
        raise JWTError('Bad Request', 'Invalid credentials')

    identity = _jwt.authentication_callback(username, password)

    if identity:
        access_token = _jwt.jwt_encode_callback(identity)
        return _jwt.auth_response_callback(access_token, identity)
    else:
        raise JWTError('Bad Request', 'Invalid credentials')
jwt.auth_request_handler(__handler)
jwt.init_app(app)

"""
==========================================0
    JOBS
==========================================0
"""
from threading import Lock
from collections import defaultdict
def job_remove_temporal_data(parent, key):
    try:
        del parent[key]
    except:
        pass

def job_create_temporal_data(parent, key):
    """
        def __error_when_upload(parent, key):
        job_remove_temporal_data(parent, key)
        os.rmtree(parent[key]['folder'])
    """

    Timer().setTimeout(partial(job_remove_temporal_data, parent, key), Config.NOT_FINISH_UPLOAD_TIMEOUT) # 1 dia
    return {'lock': Lock(), 'used': False, 'uploaded_files': 0}

class TemporalDefaultdict(defaultdict):
    def __missing__(self, key):
        if self.default_factory:
            dict.__setitem__(self, key, self.default_factory(self, key))
            return self[key]
        else:
            defaultdict.__missing__(self, key)

TMP_DATA = TemporalDefaultdict(job_create_temporal_data)
def get_chunk_name(uploaded_filename, chunk_number):
    return uploaded_filename + "_part_%03d" % chunk_number

@app.route("/job/create", methods=['POST'])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_create_post():
    def job_normal_post(job_files_type):
        resumableTotalChunks = request.form.get('resumableTotalChunks', type=int)
        resumableChunkNumber = request.form.get('resumableChunkNumber', default=1, type=int)
        resumableFilename = request.form.get('resumableFilename', default='error', type=str)
        resumableIdentifier = request.form.get('resumableIdentifier', default='error', type=str)
        numberFiles = request.form.get('number_files', type=int)
        packIdentifier = request.form.get('pack_identifier', type=str)

        # get the chunk data
        chunk_data = request.files['file']

        # make our temp directory
        temp_dir = os.path.join(Config.TMP_BASE_UPLOADS, packIdentifier, resumableIdentifier)
        os.makedirs(temp_dir, 777, exist_ok=True)

        # save the chunk data
        chunk_name = get_chunk_name(resumableFilename, resumableChunkNumber)
        chunk_file = os.path.join(temp_dir, chunk_name)
        chunk_data.save(chunk_file)
        app.logger.debug('Saved chunk: %s', chunk_file)

        with TMP_DATA[packIdentifier]['lock']:
            # check if the upload is complete
            chunk_paths = [os.path.join(temp_dir, get_chunk_name(resumableFilename, x)) for x in range(1, resumableTotalChunks + 1)]
            upload_complete = all([os.path.exists(p) for p in chunk_paths])

            # combine all the chunks to create the final file
            if upload_complete:
                target_folder = os.path.join(Config.INPUT_BASE_UPLOADS, packIdentifier)
                target_file_name = os.path.join(target_folder, resumableFilename)
                TMP_DATA[packIdentifier]['folder'] = target_folder
                os.makedirs(target_folder, 777, exist_ok=True)
                with open(target_file_name, "ab") as target_file:
                    for p in chunk_paths:
                        stored_chunk_file_name = p
                        stored_chunk_file = open(stored_chunk_file_name, 'rb')
                        target_file.write(stored_chunk_file.read())
                        stored_chunk_file.close()
                        os.unlink(stored_chunk_file_name)
                target_file.close()
                os.rmdir(temp_dir)
                app.logger.debug('File saved to: %s', target_file_name)
                TMP_DATA[packIdentifier]['uploaded_files'] += 1
            
                # All is uploaded
                if TMP_DATA[packIdentifier]['uploaded_files'] == numberFiles:
                    if not TMP_DATA[packIdentifier]['used']:
                        os.rmdir(os.path.dirname(temp_dir))
                        """
                            CREATE JOB
                        """
                        job_name = request.form.get('name', type=str)
                        job_camera = request.form.get('camera', type=str)
                        job_priority = request.form.get('priority', type=int)
                        job_sport = request.form.get('sport', type=str)
                        job_tags = json_util.loads(request.form.get('tags', type=str, default="[]"))
                        job_frame_tags = json_util.loads(request.form.get('frame_tags', type=str, default="[]"))
                        job_order = request.form.get('order', type=str)
                        job_order_regex = request.form.get('order_regex', type=str)
                        job_comments = request.form.get('comments', type=str)
                        job_label_roi = request.form.get('label_roi') == 'true'
        
                        if job_files_type == 'files':
                            type_container = Job.Container.IMAGE_FOLDER
                        elif job_files_type == 'video':
                            type_container = Job.Container.VIDEO
                        elif job_files_type == 'zip':
                            type_container = Job.Container.ZIP

                        job_files_params = json_util.loads(request.form.get('files_params', type=str, default="{}"))
                        
                        target_files = []
                        for n in os.listdir(target_folder):
                            file_path = os.path.join(target_folder, n)
                            if os.path.isfile(file_path) and not is_annotation(file_path):
                                file_annotation_path = get_annotation(file_path)
                                if file_annotation_path is not None:
                                    target_files.append((file_path, file_annotation_path))
                                else:
                                    target_files.append(file_path)

                        # Cada fichero un solo job (zip se hara una vez descomprimido en processes).
                        if 'each_file_one_job' in job_files_params and job_files_params['each_file_one_job'] and type_container != Job.Container.ZIP:
                            parent_id = str(uuid.uuid4())
                            for i, target_file in enumerate(target_files):
                                random_identifier = str(uuid.uuid4())
                                new_target_folder = os.path.join(Config.INPUT_BASE_UPLOADS, random_identifier)
                                os.makedirs(new_target_folder, exist_ok=True)

                                if isinstance(target_file, (tuple, list)):
                                    new_target_file = []
                                    for x in target_file:
                                        new_target_file_v = os.path.join(new_target_folder, os.path.basename(x))
                                        new_target_file.append(new_target_file_v)
                                        shutil.move(x, new_target_file_v)
                                    new_target_file = tuple(new_target_file)

                                else:  
                                    new_target_file = os.path.join(new_target_folder, os.path.basename(target_file))
                                    shutil.move(target_file, new_target_file)

                                job_name_split = job_name + " (" + str(i) + ")"
                                j = Job(
                                    name=job_name_split,
                                    camera=job_camera,
                                    created_by=current_identity.ref_id,
                                    priority=job_priority,
                                    sport=job_sport,
                                    tags=job_tags,
                                    frame_tags=job_frame_tags,
                                    container=Job.Container(type_container=type_container, files=[new_target_file], params=job_files_params, order=job_order, order_regex=job_order_regex, folder=new_target_folder),
                                    visible=True,
                                    comments=job_comments,
                                    label_roi=job_label_roi,
                                    variables={'parent_id': parent_id})
                                try:
                                    queue.insert_job(j)
                                except pymongo.errors.DuplicateKeyError:
                                    shutil.rmtree(target_folder)
                                    return Response_ERROR(description="Error duplicated name.", error="error_job_duplicated_name")
                            remove_if_empty(target_folder)
                        else:
                            j = Job(
                                name=job_name,
                                camera=job_camera,
                                created_by=current_identity.ref_id,
                                priority=job_priority,
                                sport=job_sport,
                                tags=job_tags,
                                frame_tags=job_frame_tags,
                                container=Job.Container(type_container=type_container, files=target_files, params=job_files_params, order=job_order, order_regex=job_order_regex, folder=target_folder),
                                visible=True,
                                comments=job_comments,
                                label_roi=job_label_roi)
                            try:
                                queue.insert_job(j)
                            except pymongo.errors.DuplicateKeyError:
                                shutil.rmtree(target_folder)
                                return Response_ERROR(description="Error duplicated name.", error="error_job_duplicated_name")

                        Timer().setTimeout(partial(job_remove_temporal_data, TMP_DATA, packIdentifier), 10.0) # 10 segundos
                        TMP_DATA[packIdentifier]['used'] = True

    def job_ftp_post():
        """
            CREATE JOB
        """
        job_name = request.form.get('name', type=str)
        job_camera = request.form.get('camera', type=str)
        job_priority = request.form.get('priority', type=int)
        job_sport = request.form.get('sport', type=str)
        job_tags = json_util.loads(request.form.get('tags', type=str, default="[]"))
        job_frame_tags = json_util.loads(request.form.get('frame_tags', type=str, default="[]"))
        job_order = request.form.get('order', type=str)
        job_order_regex = request.form.get('order_regex', type=str)
        job_comments = request.form.get('comments', type=str)
        job_label_roi = request.form.get('label_roi') == 'true'

        type_container = Job.Container.FOLDER

        job_files_params = json_util.loads(request.form.get('files_params', type=str, default="{}"))        
        j = Job(
            name=job_name,
            camera=job_camera,
            created_by=current_identity.ref_id,
            priority=job_priority,
            sport=job_sport,
            tags=job_tags,
            frame_tags=job_frame_tags,
            status=Job.FTP_UPLOADING,
            container=Job.Container(type_container=type_container, files=[], params=job_files_params, order=job_order, order_regex=job_order_regex, folder=None),
            visible=True,
            comments=job_comments,
            label_roi=job_label_roi)

        try:
            queue.insert_job(j, add_files=False)
        except pymongo.errors.DuplicateKeyError:
            return Response_ERROR(description="Error duplicated name.", error="error_job_duplicated_name")
            #return Response(json_util.dumps({'status': 'Error', 'message': 'Duplicated name'}), status=500, mimetype='application/json')

    def job_corpus_post():
        """
            CREATE JOB
        """
        job_name = request.form.get('name', type=str)
        job_camera = request.form.get('camera', type=str)
        job_priority = request.form.get('priority', type=int)
        job_sport = request.form.get('sport', type=str)
        job_tags = json_util.loads(request.form.get('tags', type=str, default="[]"))
        job_frame_tags = json_util.loads(request.form.get('frame_tags', type=str, default="[]"))
        job_order = request.form.get('order', type=str)
        job_order_regex = request.form.get('order_regex', type=str)
        job_comments = request.form.get('comments', type=str)
        job_label_roi = request.form.get('label_roi') == 'true'

        type_container = Job.Container.FOLDER

        job_files_params = json_util.loads(request.form.get('files_params', type=str, default="{}"))

        new_files = []
        random_identifier = str(uuid.uuid4())
        new_folder = os.path.join(Config.INPUT_BASE_UPLOADS, random_identifier)
        os.makedirs(new_folder, exist_ok=True)

        glob_route = os.path.join(Config.CORPUS_PATH, glob.escape(job_files_params['glob_route']).replace("[*]", "*"))
        glob_route = glob2.glob(glob_route)

        print(f"Glob route: {glob_route}")
        for file_path in glob_route:
            new_file_path = os.path.join(new_folder, os.path.basename(file_path))
            print(f"File path {file_path}")
            os.symlink(file_path, new_file_path)
            file_annotation_path = get_annotation(file_path)
            if file_annotation_path is not None:
                new_annotation_file_path = os.path.join(new_folder, os.path.basename(file_annotation_path))
                os.symlink(file_annotation_path, new_annotation_file_path)

                new_files.append((new_file_path, new_annotation_file_path))
            else:
                new_files.append(new_file_path)

        # Cada fichero un job
        if 'each_file_one_job' in job_files_params and job_files_params['each_file_one_job']:
            parent_id = str(uuid.uuid4())
            for i, new_file in enumerate(new_files):
                random_identifier = str(uuid.uuid4())
                new_target_folder = os.path.join(Config.INPUT_BASE_UPLOADS, random_identifier)
                os.makedirs(new_target_folder, exist_ok=True)

                if isinstance(new_file, (tuple, list)):
                    new_target_file = []
                    for x in new_file:
                        new_target_file_v = os.path.join(new_target_folder, os.path.basename(x))
                        new_target_file.append(new_target_file_v)
                        shutil.move(x, new_target_file_v)
                    new_target_file = tuple(new_target_file)

                else:  
                    new_target_file = os.path.join(new_target_folder, os.path.basename(new_file))
                    shutil.move(new_file, new_target_file)

                job_name_split = job_name + " (" + str(i) + ")"
                j = Job(
                    name=job_name_split,
                    camera=job_camera,
                    created_by=current_identity.ref_id,
                    priority=job_priority,
                    sport=job_sport,
                    tags=job_tags,
                    frame_tags=job_frame_tags,
                    container=Job.Container(type_container=type_container, files=[new_target_file], params=job_files_params, order=job_order, order_regex=job_order_regex, folder=new_target_folder),
                    visible=True,
                    comments=job_comments,
                    label_roi=job_label_roi,
                    variables={'parent_id': parent_id})

                try:
                    queue.insert_job(j)
                except pymongo.errors.DuplicateKeyError:
                    return Response_ERROR(description="Error duplicated name.", error="error_job_duplicated_name")
            remove_if_empty(new_folder)
        else:
            j = Job(
                name=job_name,
                camera=job_camera,
                created_by=current_identity.ref_id,
                priority=job_priority,
                sport=job_sport,
                tags=job_tags,
                frame_tags=job_frame_tags,
                container=Job.Container(type_container=type_container, files=new_files, params=job_files_params, order=job_order, order_regex=job_order_regex, folder=new_folder),
                visible=True,
                comments=job_comments,
                label_roi=job_label_roi)

            try:
                queue.insert_job(j)
            except pymongo.errors.DuplicateKeyError:
                return Response_ERROR(description="Error duplicated name.", error="error_job_duplicated_name")
                #return Response(json_util.dumps({'status': 'Error', 'message': 'Duplicated name'}), status=500, mimetype='application/json')

    try:
        job_files_type = request.form.get('files_type', type=str)

        if job_files_type == 'ftp':
            response = job_ftp_post()

        elif job_files_type == 'corpus':
            response = job_corpus_post()

        else:
            response = job_normal_post(job_files_type)

        if response is not None:
            return response

        return Response_OK(description="Successful job creation")

    except HTTPException as e:
        traceback.print_exc()
        print(e)
        raise e

    except Exception as e:
        traceback.print_exc()
        print(e)
        abort(404, 'Not found')

    return 'OK'

@app.route("/job/create", methods=['GET'])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_create_get():
    resumableIdentifier = request.args.get('resumableIdentifier', type=str)
    resumableFilename = request.args.get('resumableFilename', type=str)
    resumableChunkNumber = request.args.get('resumableChunkNumber', type=int)
    packIdentifier = request.args.get('pack_identifier', type=str)

    if not resumableIdentifier or not resumableFilename or not resumableChunkNumber:
        # Parameters are missing or invalid
        abort(500, 'Parameter error')

    # chunk folder path based on the parameters
    temp_dir = os.path.join(Config.TMP_BASE_UPLOADS, packIdentifier, resumableIdentifier)

    # chunk path based on the parameters
    chunk_file = os.path.join(temp_dir, get_chunk_name(resumableFilename, resumableChunkNumber))
    app.logger.debug('Getting chunk: %s', chunk_file)

    if os.path.isfile(chunk_file):
        # Let resumable.js know this chunk already exists
        return 'OK'
    else:
        # Let resumable.js know this chunk does not exists and needs to be uploaded
        abort(404, 'Not found')

@app.route('/job/visibility', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_visibility():
    data = json_util.loads(request.data)
    response = Job.change_visibility(data['job_id'], data['value'])
    if response:
        return Response_OK(description="Successful job change visibility")
    else:
        return Response_ERROR(description="Error job change visibility", error="error_job_change_visibility")

@app.route('/job/tags', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_tags():
    data = json_util.loads(request.data)
    response = Job.change_tags(data['job_id'], data['tags'])
    if response:
        return Response_OK(description="Successful job change tags")
    else:
        return Response_ERROR(description="Error during change tags", error="error_job_change_tags")

@app.route('/job/tags/frame', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_frame_tags():
    data = json_util.loads(request.data)
    response = Job.change_frame_tags(data['job_id'], data['frame_tags'])
    if response:
        return Response_OK(description="Successful job change frametags")
    else:
        return Response_ERROR(description="Error during change frame tags", error="error_job_change_frame_tags")

@app.route('/job/list', methods=["GET"])
@jwt_required()
@group_decorator(User.ADMIN)
def job_list():
    try:
        status = request.args.get('status', None)
        response = Job.list(status=status)
        return Response_OK(description="Successful job list", data=response)
    except:
        traceback.print_exc()
        return Response_ERROR(description="Error during job list", error="error_job_list")

@app.route('/job/metrics', methods=["GET"])
@jwt_required()
@group_decorator(User.ADMIN)
def job_metrics():
    try:
        job_id = request.args.get('job_id', None)
        image_type = request.args.get('image_type', type=str, default='jpg')
        if job_id is None:
            return Response_ERROR(description="Error during job metrics", error="error_job_metrics")

        response = Job.metrics(job_id=job_id)
        response['heatmap']['sample'] = Images.pack_im(response['heatmap']['sample'], image_type)
        return Response_OK(description="Successful job metrics", data=response)
    except:
        traceback.print_exc()
        return Response_ERROR(description="Error during job metrics", error="error_job_metrics")

@app.route('/job/remove', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_remove():
    data = json_util.loads(request.data)
    response = Job.remove(data['job_id'], data['remove_output'])
    if response:
        return Response_OK(description="Successful job removed")
    else:
        return Response_ERROR(description="Error during remove job", error="error_job_remove")

@app.route('/job/remove/entire', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def job_remove_entire():
    data = json_util.loads(request.data)
    response = Job.remove_entire(data['parent_id'], data['remove_output'])
    if response:
        return Response_OK(description="Successful job removed")
    else:
        return Response_ERROR(description="Error during remove job", error="error_job_remove")

@app.route('/job/image/frame', methods=["GET"])
@jwt_required()
@group_decorator(User.ADMIN)
def job_image_frame():
    try:
        job_id = request.args.get('job_id', None)
        frame_id = request.args.get('frame_id', None, type=int)
        image_type = request.args.get('image_type', type=str, default='jpg')
        frame = Job.get_frame(job_id, frame_id)
        if frame is not None:
            response = {
                'image': Images.pack_im(frame, image_type)
            }
        else:
            response = None
        return Response_OK(description="Successful job frame", data=response)
    except:
        traceback.print_exc()
        return Response_ERROR(description="Error during job frame", error="error_job_image_frame")


"""
==========================================0
    ANNOTATION
==========================================0
"""
from library.images import Images

def __annotation_remove_assigned(file_id, user_id):
    queue.remove_annotation(file_id, user_id)

@app.route('/job/get/annotation', methods=["GET"])
@jwt_required()
@group_decorator(groups=[User.ADMIN, User.ANNOTATOR])
def get_annotation_job():
    image_type = request.args.get('image_type', type=str, default='numpy')
    timeout_data = Config.GET_ANNOTATION_TIMEOUT

    while True:
        file_annotation, job, has_to_label_roi, is_new = queue.get_annotation(current_identity)
        if file_annotation is None:
            return Response_OK(description="Not annotation available", data=None)
        
        annotation_path = os.path.splitext(file_annotation.path)[0] + Config.ANNOTATION_FILE
        if os.path.exists(annotation_path):
            with open(annotation_path, 'rb') as f:
                annotation_data = f.read().decode('utf-8')
        else:
            annotation_data = None
        try:
            def_frame_tags = []
            def_frame_tags_active = []
            for tag in Preferences.get_frame_tags(job.sport):
                def_frame_tags.append(tag)
                def_frame_tags_active.append(tag in job.frame_tags)

            response = {
                '_id': file_annotation.ref_id,
                'has_to_label_roi': has_to_label_roi,
                'file_path': file_annotation.path.replace(Config.INPUT_BASE_UPLOADS, ''),
                'image': Images.pack_im(Images.read(file_annotation.path), image_type),
                'xml': annotation_data,
                'timeout': file_annotation.assigned_at + datetime.timedelta(seconds=timeout_data),
                'sport': job.sport,
                'camera': job.camera,
                'default_frame_tags': {
                    'list': def_frame_tags,
                    'active': def_frame_tags_active
                },
                'job_id': job.ref_id
            }

            # if is_new:
            #     Timer().setTimeout(partial(__annotation_remove_assigned, file_annotation.ref_id, current_identity), timeout_data)

            return Response_OK(description="Successful get annotation", data=response)

        except Exception as e:
            traceback.print_exc()
            
            job = Job.get(file_annotation.job_id)
            on_error = {}
            on_error['files'] = [file_annotation.path]
            on_error['messages'] = ['Error during get annotation.']
            on_error['extras'] = [str(e)]
            on_error['removes'] = [True]
            job.create_error_on_file(**on_error, cancel=False)
            queue.set_annotation(current_identity, file_annotation)   

"""
@app.route('/job/check/annotation', methods=["GET"])
@jwt_required()
@group_decorator(groups=[User.ADMIN, User.ANNOTATOR])
def check_annotation_job():
    anno_id = request.args.get('anno_id', default=None)
    status = queue.check_is_annotated(anno_id)
    return Response(json_util.dumps({'status': status}), status=200, mimetype='application/json')
"""

@app.route('/job/set/annotation', methods=["POST"])
@jwt_required()
@group_decorator(groups=[User.ADMIN, User.ANNOTATOR])
def set_annotation_job():
    data = json_util.loads(request.data)
    file_annotation = Job.Container.File.get(data['ref_id'])
    if file_annotation is None:
        return Response_ERROR(description="Error during assign. File not exists", error='error_set_annotation_removed')

    last_changes = data.get('last_changes', None)
    frame_tags = data.get('frame_tags', None) #Preferences.get_frame_tags(Job.get(file_annotation.job_id).sport))
    roi = data.get('roi', None)

    annotation_path = os.path.splitext(file_annotation.path)[0] + Config.ANNOTATION_FILE
    with open(annotation_path, "wb") as f:
        f.write(data['xml'].encode('utf-8'))

    if last_changes is not None:
        file_annotation.variables['last_changes'] = last_changes

    if frame_tags is not None:
        file_annotation.variables['frame_tags'] = frame_tags

    if 'annotation_path' not in file_annotation.variables.keys():
        file_annotation.variables['annotation_path'] = annotation_path

    try:
        response, text, error_or_status = queue.set_annotation(current_identity, file_annotation, roi)

        if response:
            return Response_OK(description=text, data=response, status=error_or_status)
        else:
            return Response_ERROR(description=text, error=error_or_status)
    except Exception as e:
        return Response_ERROR(description="Error while saving annotation", error="error_set_annotation")

"""
==========================================0
    FTP
==========================================0
"""
import random
import string
import shutil

"""
    FTP TO OUTPUT
"""
#for user in User.list(list_password=True):
#    if user['group'] == User.ADMIN:
#        FTP_AUTH.add_user(user['username'], user['password'], homedir=Config.OUTPUT_BASE_UPLOADS, perm='elradfmwMT', is_cypher=True)

def random_string(string_length=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))

def __job_remove_user_ftp(user_ftp, token_dir):
    try:
        FTP_AUTH.remove_user(user_ftp)
        shutil.rmtree(token_dir)
    except:
        pass

@app.route('/job/ftp/credentials', methods=["GET"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def get_ftp_credentials():
    try:
        user_ftp = random_string(15)
        pass_ftp = random_string(15)
        token_ftp = str(uuid.uuid4())
        
        token_dir = os.path.join(Config.FTP_BASE_UPLOADS, token_ftp)
        os.makedirs(token_dir, 777, exist_ok=True)
        FTP_AUTH.add_user(user_ftp, pass_ftp, homedir=token_dir, perm='elradfmwMT')
        timeout_data = Config.FTP_CREDENTIALS_TIMEOUT
        Timer().setTimeout(partial(__job_remove_user_ftp, user_ftp, token_dir), timeout_data) # 7 dias

        response = {
            'host': '127.0.0.1',
            'port': '2121',
            'username': user_ftp,
            'password': pass_ftp,
            'token': token_ftp
        }
        
        return Response_OK(description="Successful ftp configuration", data={
            "credentials": response,
            "timeout": timeout_data
            })
    except:
        return Response_ERROR(description="Error during ftp configuration", error="error_job_ftp_config")

@app.route('/job/ftp/start', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def set_ftp_start():
    data = json_util.loads(request.data)
    job = Job.get(data['job_id'])

    if job.status != Job.FTP_UPLOADING:
        return Response_OK(description="Successful ftp start process") # TODO

    job.update_status(Job.PREPROCESS)
    
    try:
        user_ftp = job.container.params['username']
        token_ftp = job.container.params['token']
        
        # Pasamos los ficheros de la carpeta FTP a la input
        target_folder = os.path.join(Config.FTP_BASE_UPLOADS, token_ftp)
        dest_folder = os.path.join(Config.INPUT_BASE_UPLOADS, token_ftp)
        shutil.move(target_folder, dest_folder)

        target_files = []
        for n in os.listdir(dest_folder):
            file_path = os.path.join(dest_folder, n)
            if os.path.isfile(file_path) and not is_annotation(file_path):
                file_annotation_path = get_annotation(file_path)
                if file_annotation_path is not None:
                    target_files.append((file_path, file_annotation_path))
                else:
                    target_files.append(file_path)


        # Cada fichero un solo job.
        if 'each_file_one_job' in job.container.params and job.container.params['each_file_one_job']:
            parent_id = str(uuid.uuid4())
            for i, target_file in enumerate(target_files):
                random_identifier = str(uuid.uuid4())
                new_target_folder = os.path.join(Config.INPUT_BASE_UPLOADS, random_identifier)
                os.makedirs(new_target_folder, exist_ok=True)

                if isinstance(target_file, (tuple, list)):
                    new_target_file = []
                    for x in target_file:
                        new_target_file_v = os.path.join(new_target_folder, os.path.basename(x))
                        new_target_file.append(new_target_file_v)
                        shutil.move(x, new_target_file_v)
                    new_target_file = tuple(new_target_file)

                else:  
                    new_target_file = os.path.join(new_target_folder, os.path.basename(target_file))
                    shutil.move(target_file, new_target_file)

                job_name_split = job.name + " (" + str(i) + ")"
                j = Job(
                    name=job_name_split,
                    camera=job.camera,
                    created_by=job.created_by,
                    priority=job.priority,
                    sport=job.sport,
                    tags=job.tags,
                    frame_tags=job.frame_tags,
                    container=Job.Container(type_container=job.container.type_container, files=[new_target_file], params=job.container.params, order=job.container.order, order_regex=job.container.order_regex, folder=new_target_folder),
                    visible=True,
                    comments=job.comments,
                    variables={'parent_id': parent_id})
                try:
                    queue.insert_job(j)
                except pymongo.errors.DuplicateKeyError:
                    shutil.rmtree(target_folder)
                    return Response_ERROR(description="Error duplicated name.", error="error_job_duplicated_name")
            Job.remove(job.ref_id)
            remove_if_empty(dest_folder)
        else: 
            # Anadimos los ficheros
            container = Job.Container(type_container=Job.Container.FOLDER, files=target_files, params=job.container.params, folder=dest_folder)
            job.update_files(container)

        # Eliminamos los ficheros
        __job_remove_user_ftp(user_ftp, token_ftp)

    except Exception as e:
        traceback.print_exc()
        return Response_ERROR(description="Error in ftp start", error="error_job_ftp_start")
    
    if not ('each_file_one_job' in job.container.params and job.container.params['each_file_one_job']):
        # Empezamos el preprocesado
        job.start_preprocess(queue)

    return Response_OK(description="Successful ftp start process")
        
"""
==========================================0
    Preferences
==========================================0
"""
@app.route('/preferences', methods=["GET"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def preferences():
    return Response_OK(description="Successful get preferences", data=Preferences.get())

@app.route('/preferences/tags/add', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def add_tag():
    try:
        data = json_util.loads(request.data)
        response = Preferences.add_tag(data['sport'], data['name'])
        if response:
            return Response_OK(description="Successful add tag")
        else:
            return Response_ERROR(description="Error when add tag", error='error_add_tag')
    except:
        return Response_ERROR(description="Error when add tag", error='error_add_tag')


@app.route('/preferences/tags/remove', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def remove_tag():
    try:
        data = json_util.loads(request.data)
        response = Preferences.remove_tag(data['sport'], data['name'])
        if response:
            return Response_OK(description="Successful remove tag")
        else:
            return Response_ERROR(description="Error when remove tag", error='error_remove_tag')
    except:
        return Response_ERROR(description="Error when remove tag", error='error_remove_tag')

@app.route('/preferences/tags/frame/add', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def add_frame_tag():
    try:
        data = json_util.loads(request.data)
        response = Preferences.add_frame_tag(data['sport'], data['name'])
        if response:
            return Response_OK(description="Successful add frame tag")
        else:
            return Response_ERROR(description="Error when add frame tag", error='error_add_frame_tag')
    except:
        return Response_ERROR(description="Error when add frame tag", error='error_add_frame_tag')  

@app.route('/preferences/tags/frame/remove', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def remove_frame_tag():
    try:
        data = json_util.loads(request.data)
        response = Preferences.remove_frame_tag(data['sport'], data['name'])
        if response:
            return Response_OK(description="Successfully removed frame tag")
        else:
            return Response_ERROR(description="Error when removing frame tag", error='error_remove_frame_tag')
    except:
        return Response_ERROR(description="Error when removing frame tag", error='error_remove_frame_tag')

@app.route('/preferences/sports/add', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def add_sport():
    try:
        data = json_util.loads(request.data)
        response = Preferences.add_sport(data['name'])
        if response:
            return Response_OK(description="Successfully added sport")
        else:
            return Response_ERROR(description="Error when adding sport", error='error_add_sport')
    except:
        return Response_ERROR(description="Error when adding sport", error='error_add_sport')

@app.route('/preferences/sports/remove', methods=["POST"])
@jwt_required()
@group_decorator(group=User.ADMIN)
def remove_sport():
    try:
        data = json_util.loads(request.data)
        response = Preferences.remove_sport(data['name'])
        if response:
            return Response_OK(description="Successful remove sport")
        else:
            return Response_ERROR(description="Error when remove sport", error='error_remove_sport')
    except:
        return Response_ERROR(description="Error when remove sport", error='error_remove_sport')

import argparse
LOG_LEVEL_MAP = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR, "CRITICAL": logging.CRITICAL}

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--log_level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Log level')
    args = parser.parse_args()
    logging.basicConfig(format='%(levelname)s - %(funcName)s@%(lineno)d : %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',level=LOG_LEVEL_MAP[args.log_level])
    
    Preferences.create()

    logging.info("Starting Flask ...")
    app.run(host="0.0.0.0", port=Config.SERVER_PORT)
