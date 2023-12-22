from threading import Thread
import datetime
from functools import partial
from bson import ObjectId
from collections import defaultdict, Counter
import cv2 
import os, sys
import shutil

import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.connection import CLIENT, DB, DESCENDING, ASCENDING
from core.config import Config

"""
    CLASS
"""

class Job(object):
    """
        
    """
    class Container(object):
        class File(object):
            NOT_ANNOTATED, IN_PROCESS, ANNOTATED = range(3)
            def __init__(self, 
                path: str,
                #ftp_path = None,
                status = None,
                annotated_by = None,
                assigned_at = None,
                ref_id = None,
                job_id = None,
                variables = None):

                if status is None:
                    status = Job.Container.File.NOT_ANNOTATED

                if variables is None:
                    variables = {}

                self.parent = None
                self.ref_id = ref_id
                self.job_id = ObjectId(job_id)

                if isinstance(path, (tuple, list)):
                    self.path = path[0]
                    annotation_file_path = path[1]
                else:
                    annotation_file_path = None
                    self.path = path

                #self.ftp_path = ftp_path
                self.status = status
                self.annotated_by = annotated_by
                self.assigned_at = assigned_at
                self.variables = variables

                if annotation_file_path is not None:
                    self.variables.update({'annotation_path': annotation_file_path})


            def __str__(self):
                return self.__repr__()

            def __repr__(self, ):
                return str(self.dict())

            def dict(self):
                return {
                    '_id': self.ref_id,
                    'job_id': ObjectId(self.job_id),
                    'path': self.path,
                    #'ftp_path': self.ftp_path,
                    'status': self.status,
                    'annotated_by': ObjectId(self.annotated_by),
                    'assigned_at': self.assigned_at,
                    'variables': self.variables
                }

            @staticmethod
            def parse(file_dict):
                return Job.Container.File(
                    ref_id=file_dict['_id'],
                    job_id=ObjectId(file_dict['job_id']),
                    path=file_dict['path'],
                    #ftp_path= file_dict['ftp_path'],
                    status=file_dict['status'],
                    annotated_by=ObjectId(file_dict['annotated_by']),
                    assigned_at=file_dict['assigned_at'] if 'assigned_at' in file_dict else None,
                    variables=file_dict['variables'] if 'variables' in file_dict else None
                )

            def start_setprocess(self, job):
                Job.SetFileProcess.parse(0).exec(None, self, job)

            def start_getprocess(self, job):
                return Job.GetFileProcess.parse(0).exec(None, self, job)

            @staticmethod
            def get(ref_id):
                with CLIENT.start_session() as session:
                    with session.start_transaction():
                        file = DB.files_jobs.find_one({'_id': ObjectId(ref_id)})
                        if file is not None:
                            return Job.Container.File.parse(file)
                        else:
                            return None

            def update_variables(self, variables):
                with CLIENT.start_session() as session:
                    with session.start_transaction():
                        self.variables.update(variables)
                        # Apaño temporal
                        updated_var = DB.files_jobs.find_one({'_id': self.ref_id})['variables']
                        updated_var.update(variables)
                        DB.files_jobs.update_one({'_id': self.ref_id}, {'$set': {'variables': updated_var}}, upsert=True)

            def update_path(self, path):
                with CLIENT.start_session() as session:
                    with session.start_transaction():
                        DB.files_jobs.update_one({'_id': self.ref_id}, {'$set': {'path': path}})



        VIDEO, IMAGE_FOLDER, ZIP, FOLDER = range(4)      
        def __init__(self, 
            type_container: int, 
            files: list,
            params: dict = None,
            order = 'ASCEND',
            order_regex = None,
            folder = None,
            **kwargs):
            assert type_container in [Job.Container.VIDEO, Job.Container.IMAGE_FOLDER, Job.Container.ZIP, Job.Container.FOLDER]
            self.type_container = type_container

            if files is not None:
                if not isinstance(files, (tuple, list)):
                    files = [files]

                if len(files) > 0 and not isinstance(files[0], Job.Container.File):
                    files = [Job.Container.File(f) for f in files]
            
            self.parent = None
            self.folder = folder
            self.__files = files

            if self.__files is not None:
                for f in self.__files:
                    f.parent = self

            if params is None:
                params = {}
            params.update(kwargs)
            self.params = params
            
            self.order = order
            self.order_regex = order_regex

        def __str__(self):
            return self.__repr__()

        def __repr__(self, ):
            return str(self.dict())

        def dict(self):
            return {
                'type_container': self.type_container,
                'files': [f.dict() for f in self.__files] if isinstance(self.__files, list) else [],
                'params': self.params,
                'order': self.order,
                'order_regex': self.order_regex,
                'folder': self.folder
            }

        @staticmethod
        def parse(file_container_dict):
            return Job.Container(
                params=file_container_dict['params'],
                type_container= file_container_dict['type_container'],
                files=[Job.Container.File.parse(f) for f in file_container_dict['files']] if 'files' in file_container_dict else None,
                order=file_container_dict['order'],
                order_regex=file_container_dict['order_regex'],
                folder=file_container_dict['folder'],
            )

        @property
        def files(self):
            if self.__files is None:
                with CLIENT.start_session() as session:
                    with session.start_transaction(): 
                        files = DB.files_jobs.find({'job_id': self.parent.ref_id})
                        files = [Job.Container.File.parse(f) for f in files]
                        if len(files) > 0:
                            self.__files = files
            return self.__files

        @files.setter
        def files(self, x):
            self.__files = x

    FTP_UPLOADING, PREPROCESS, NOT_STARTED, IN_PROCESS, POSTPROCESS, FINISHED = range(6)
    def __init__(self,
        name,
        camera,
        created_by,
        priority,
        sport,
        tags,
        frame_tags,
        container,
        preprocess_step = 0,
        postprocess_step = 0,
        status = None,
        ref_id = None,
        created_at = None,
        variables = None,
        visible = True,
        roi = None,
        comments = '',
        alerts = [],
        label_roi=True
        ):

        if status is None:
            status = Job.PREPROCESS

        if variables is None:
                    variables = {}

        if created_at is None:
            created_at = datetime.datetime.utcnow()

        self.ref_id = ref_id
        self.name = name
        self.camera = camera
        self.created_by = ObjectId(created_by)
        self.status = status
        self.preprocess = Job.Preprocess.parse(preprocess_step)
        self.postprocess = Job.Postprocess.parse(postprocess_step)
        assert 0 <= priority <= 10
        self.priority = priority
        self.container = container
        self.container.parent = self
        self.sport = sport
        self.tags = tags
        self.frame_tags = frame_tags

        self.created_at = created_at

        self.variables = variables

        self.visible = visible
        self.roi = roi
        self.comments = comments
        self.alerts = alerts
        self.label_roi = label_roi

    def __str__(self):
        return self.__repr__()

    def __repr__(self, ):
        return str(self.dict())

    def dict(self):
        return {
            '_id': self.ref_id,
            'created_at': self.created_at,
            'name': self.name,
            'camera': self.camera,
            'created_by': self.created_by,
            'status': self.status,
            'preprocess_step': self.preprocess.curr_step,
            'preprocess_name': self.preprocess.curr_step_name(),
            'postprocess_step': self.postprocess.curr_step,
            'postprocess_name': self.postprocess.curr_step_name(),
            'priority': self.priority,
            'container': self.container.dict(),
            'sport': self.sport,
            'tags': self.tags,
            'frame_tags': self.frame_tags,
            'variables': self.variables,
            'visible': self.visible,
            'roi': self.roi,
            'comments': self.comments,
            'alerts': self.alerts,
            'label_roi': self.label_roi

        }

    @staticmethod
    def parse(job_dict):
        return Job(
            ref_id=ObjectId(job_dict['_id']),
            created_at=job_dict['created_at'],
            name=job_dict['name'],
            camera=job_dict['camera'],
            created_by=ObjectId(job_dict['created_by']),
            status=job_dict['status'],
            preprocess_step=job_dict['preprocess_step'],
            postprocess_step=job_dict['postprocess_step'],
            priority=job_dict['priority'],
            container=Job.Container.parse(job_dict['container']),
            sport=job_dict['sport'],
            tags=job_dict['tags'],
            frame_tags=job_dict['frame_tags'],
            variables=job_dict['variables'] if 'variables' in job_dict else None,
            visible=job_dict['visible'],
            roi=job_dict['roi'] if 'roi' in job_dict else None,
            comments=job_dict['comments'],
            alerts=job_dict['alerts'],
            label_roi=job_dict['label_roi']
        )

    def start_preprocess(self, queue):
        def __thread():
            if not self.preprocess.exec(partial(queue.on_step_end, self, 'preprocess'), self)[1]:
                self.status = Job.NOT_STARTED
                queue.process_job_done(self, 'preprocess_at')
        Thread(target=__thread).start()

    def start_postprocess(self, queue):
        def __thread():
            if not self.postprocess.exec(partial(queue.on_step_end, self, 'postprocess'), self)[1]:
                self.status = Job.FINISHED
                queue.process_job_done(self, 'finished_at')
        Thread(target=__thread).start()

    def update_status(self, status):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                DB.jobs.update_one({'_id': self.ref_id}, {'$set': {'status': status}})
 
    def update_trace(self, process, step, percent):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                DB.jobs.update_one({'_id': self.ref_id}, {'$set': {'trace.%s.%s' % (process, step): percent}}, upsert=True)

    def update_files(self, container_files, remove_previous=True, is_preprocess=True):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                # Añadimos los files
                if remove_previous:
                    DB.files_jobs.delete_many({'job_id': self.ref_id})
                    #total_files = 0
                    self.container = container_files
                else:
                    #total_files = DB.jobs.find_one({'_id': self.ref_id})['total_files']
                    self.container.files += container_files.files
                
                aux_files = container_files.dict()['files']

                #if is_preprocess:
                #    DB.jobs.update_one({'_id': self.ref_id}, {'$set': {'done_files': 0, 'total_files': total_files + len(aux_files)}})

                for i, f in enumerate(aux_files):
                    del f['_id']
                    f['job_id'] = self.ref_id
                    container_files.files[i].job_id = self.ref_id

                if len(aux_files) > 0:
                    r = DB.files_jobs.insert_many(aux_files)
                    for f, id_ in zip(container_files.files, r.inserted_ids):
                        f.ref_id = id_

    def add_alert(self, message, cancel=False):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                curr_query = {'$push': {'alerts': message}}
                if cancel:
                    curr_query['$set'] = {'cancel': cancel, 'cancelled_at': datetime.datetime.utcnow()}
                DB.jobs.update_one({'_id': self.ref_id}, curr_query)

    def create_error_on_file(self, files=None, messages=None, extras=None, removes=None, file=None, message=None, extra=None, remove=[], cancel=False):
        def __parse_get_ref_id(file):
            if isinstance(file, Job.Container.File):
                return file.ref_id
            else:
                return None

        def __parse_file(file):
            if isinstance(file, Job.Container.File):
                return file.dict()
            else:
                return {'path': str(file)}

        if files is None:
            files = []

        if file is not None:
            files.append(file)

        if messages is None:
            messages = []

        if message is not None:
            messages.append(message)

        if extras is None:
            extras = []

        if extra is not None:
            extras.append(extra)  

        if removes is None:
            removes = []

        if remove is not None:
            removes.append(remove)      

        # Miramos cuales hay que borrar
        file_to_remove = []
        files_with_errors = []
        for file, remove, message, extra in zip(files, removes, messages, extras):
            file_dict = __parse_file(file)
            file_dict.update({'message': message, 'extras': extra})  
            files_with_errors.append(file_dict)      

            idx = __parse_get_ref_id(file)
            if remove and idx is not None:
                file_to_remove.append(idx)

        with CLIENT.start_session() as session:
            with session.start_transaction():
                if not cancel:
                    cancel = DB.files_jobs.find({'job_id': self.ref_id}).count() <= len(files_with_errors)

                if len(file_to_remove) > 0:
                    DB.files_jobs.delete_many({'_id': {'$in': file_to_remove}})
                curr_query = {'$push': {'files_error': {'$each': files_with_errors}}}

                if not cancel:
                    cancel = DB.files_jobs.find({'job_id': self.ref_id}).count() == 0

                if cancel:
                    curr_query['$set'] = {'cancel': cancel, 'cancelled_at': datetime.datetime.utcnow()}
                DB.jobs.update_one({'_id': self.ref_id}, curr_query)

                aux = self.container.files
                self.container.files = []
                for f in aux:
                    if f.path not in files:
                        self.container.files.append(f)
    
    def update_container_folder(self, folder):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                DB.jobs.update_one({'_id': self.ref_id}, {'$set': {'container.folder': folder}})

    def get_output_name(self):
        return os.path.join(self.sport, self.name, self.camera)

    @staticmethod
    def change_visibility(job_id, value):
        try:
            DB.jobs.update_one({'_id': job_id}, {'$set': {'visible':  value}})
            return True
        except:
            return False

    @staticmethod
    def change_tags(job_id, tags):
        try:
            DB.jobs.update_one({'_id': job_id}, {'$set': {'tags':  tags}})       
            return True
        except:
            return False

    @staticmethod
    def change_frame_tags(job_id, frame_tags):
        DB.jobs.update_one({'_id': job_id}, {'$set': {'frame_tags':  frame_tags}})

    @staticmethod
    def list(status=None):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                if status is not None:
                    jobs = DB.jobs.aggregate([
                        {'$lookup': {
                            'from': 'users',
                            'localField': 'created_by',
                            'foreignField': '_id',
                            'as': 'join'
                        }},
                        {'$match': {'status': int(status)}},  
                        {'$sort': {'priority': DESCENDING, 'created_at': ASCENDING}},
                        {'$addFields': {'created_by_name': {'$arrayElemAt': ['$join.username', 0]}}}
                    ])
                else:
                    jobs = DB.jobs.aggregate([
                        {'$lookup': {
                            'from': 'users',
                            'localField': 'created_by',
                            'foreignField': '_id',
                            'as': 'join'
                        }},
                        {'$sort': {'priority': DESCENDING, 'created_at': ASCENDING}},
                        {'$addFields': {'created_by_name': {'$arrayElemAt': ['$join.username', 0]}}}
                    ])

                jobs = list(jobs)
                for j in jobs:
                    done_files, total_files = Job.get_count_files(j['_id'])
                    j['done_files'] = done_files
                    j['total_files'] = total_files
                return jobs

    @staticmethod
    def get(job_id):
        job = DB.jobs.find_one({'_id': job_id})
        return Job.parse(job)

    @staticmethod
    def get_frame(job_id, frame_id):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                frame = DB.files_jobs.aggregate([
                    {'$match': {'job_id': ObjectId(job_id)}},
                    {'$skip': frame_id},
                    {'$limit': 1}
                ])
                frame = list(frame)
                if len(frame) > 0:
                    im_sample = cv2.imread(frame[0]['path'])
                    return im_sample
        return None

    @staticmethod
    def get_count_files(job_id):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                aux_done_count = DB.files_jobs.aggregate([
                    {'$match': {'$and': [{'job_id': ObjectId(job_id)}, {'status': Job.Container.File.ANNOTATED}]}},
                    {'$count': "number_annotations"}
                ])

                aux_done_count = list(aux_done_count)
                if len(aux_done_count) > 0:
                    aux_done_count = aux_done_count[0]['number_annotations']
                else:
                    aux_done_count = 0

                aux_total_count = DB.files_jobs.aggregate([
                    {'$match': {'job_id': ObjectId(job_id)}},
                    {'$count': "number_annotations"}
                ])

                aux_total_count = list(aux_total_count)
                if len(aux_total_count) > 0:
                    aux_total_count = aux_total_count[0]['number_annotations']
                else:
                    aux_total_count = 0

                return aux_done_count, aux_total_count

    @staticmethod
    def get_frame_tags(sport):
        with CLIENT.start_session() as session:
                with session.start_transaction():
                    frame_tags = DB.preferences.find_one()
                    if sport in frame_tags['frame_tags']:
                        return frame_tags['frame_tags'][sport] + frame_tags['frame_tags']['generic']
                    else:
                        return frame_tags['frame_tags']['generic']

    @staticmethod
    def metrics(job_id):
        with CLIENT.start_session() as session:
            with session.start_transaction():
                frame_tags = Job.get_frame_tags(DB.jobs.find_one({'_id': ObjectId(job_id)})['sport'])

                job = DB.jobs.find_one({'_id': ObjectId(job_id)})
                files = DB.files_jobs.aggregate([
                    {'$match':  {'job_id': ObjectId(job_id), 'status': Job.Container.File.ANNOTATED}},
                    {'$project': {'path': 1, 'annotated_by': 1, 'metrics': '$variables.metrics', 'frame_tags': '$variables.frame_tags', 'time': {'$subtract': ['$finished_at', '$assigned_at']}}},
                    {'$lookup': {
                        'from': 'users',
                        'localField': 'annotated_by',
                        'foreignField': '_id',
                        'as': 'join'
                    }},
                    {'$addFields': {'annotated_by_name': {'$arrayElemAt': ['$join.username', 0]}}}
                ])

                total_timming_per_annotator = defaultdict(lambda: 0)
                count_per_annotator = defaultdict(lambda: 0)
                count_per_annotator_valid = defaultdict(lambda: 0)

                heatmap = defaultdict(lambda: Counter())
                heatmap_per_annotator = defaultdict(lambda: defaultdict(lambda: Counter()))
                class_counter = Counter()
                class_counter_per_annotator = defaultdict(lambda: Counter())

                timeline_frame_tags = defaultdict(list)
                tmp_frame_tags = defaultdict(lambda: None)
                for fg in frame_tags:
                    timeline_frame_tags[fg] = []

                files = list(files)
                global_path = None
                for i, f in enumerate(files):
                    if i == 0:
                        global_path = f['path']
                    annotated_by = str(f['annotated_by_name'])

                    # Timmings
                    if f['time'] is not None:
                        total_timming_per_annotator[annotated_by] += f['time'] / 1e3 # Time ms to s
                        count_per_annotator_valid[annotated_by] += 1
                    count_per_annotator[annotated_by] += 1

                    # Heatmap and Counter
                    for label, positions in f['metrics']['position'].items():
                        for pos, value in positions.items():
                            # pos = [int(x) for x in pos.split('_')]
                            heatmap_per_annotator[annotated_by][label][pos] += value
                            heatmap[label][pos] += value

                            class_counter[label] += value
                            class_counter_per_annotator[annotated_by][label] += value

                    # Timeline tags
                    for tag in f['frame_tags']:
                        if tag not in tmp_frame_tags or tmp_frame_tags[tag] is None:
                            # Open tag: esta en frame tags pero no en tmp
                            tmp_frame_tags[tag] = i

                    for tag in tmp_frame_tags.keys():
                        if tag not in f['frame_tags'] and tmp_frame_tags[tag] is not None:
                            # Close tag: esta en tmp ero no en frame tags
                            timeline_frame_tags[tag].append([tmp_frame_tags[tag], i])
                            tmp_frame_tags[tag] = None

                
                # Timmings
                total_timming = 0
                total_count = 0
                total_avg_timming_per_annotator = {}
                for k in total_timming_per_annotator.keys():
                    total_avg_timming_per_annotator.update(
                        {
                            k: total_timming_per_annotator[k] / count_per_annotator_valid[k] if count_per_annotator_valid[k] > 0 else 0
                        }
                    )
                    # We need to provide data consistent with the observations. Somehow some assignet_at are None.
                    # We need to make up for theese missing values
                    if count_per_annotator[k] > count_per_annotator_valid[k]:
                        total_timming_per_annotator[k] = total_avg_timming_per_annotator[k] * count_per_annotator[k]
                    total_timming += total_timming_per_annotator[k]
                    total_count += count_per_annotator[k]
                total_avg_timming = total_timming / total_count if total_count > 0 else 0
    

                im_sample = cv2.imread(global_path)
                shape = im_sample.shape

                # Close posible open timeline tags
                for tag in tmp_frame_tags.keys():
                    # Close tag: esta en tmp ero no en frame tags
                    if tmp_frame_tags[tag] is not None:
                        timeline_frame_tags[tag].append([tmp_frame_tags[tag], len(files)])
                        tmp_frame_tags[tag] = None

                return {
                    'timmings': {
                        'count': {
                            'total': len(files),
                            'annotators': count_per_annotator
                        },
                        'sum': {
                            'total': total_timming,
                            'annotators': total_timming_per_annotator
                        },

                        'avg': {
                            'total': total_avg_timming,
                            'annotators': total_avg_timming_per_annotator
                        },
                    },

                    'distribution': {
                        'total': class_counter,
                        'annotators': class_counter_per_annotator
                    },

                    'heatmap': {
                        'sample': im_sample,
                        'size': (shape[1], shape[0]),
                        'total': heatmap,
                        'annotators': heatmap_per_annotator
                    },

                    'timeline': timeline_frame_tags,

                    'roi': job['roi'] if job['label_roi'] else None
                }

    @staticmethod
    def remove_entire(parent_id, remove_output=False):
        jobs = DB.jobs.find({'variables.parent_id': parent_id})
        true_all = True
        for j in jobs:
            true_all &= Job.remove(j['_id'], remove_output=remove_output)
        return true_all

    @staticmethod
    def remove(job_id, remove_output=False):
        try:
            with CLIENT.start_session() as session:
                with session.start_transaction():
                    job = DB.jobs.find_one({'_id': ObjectId(job_id)})
                    try:
                        # Sino no ha acabado el job se borra todo.
                        # Si el job ha terminado para borrarlo todo debe estar activada la flag remove_output
                        if job['container']['folder'] is not None and (remove_output or job['status'] != Job.FINISHED):
                            folder_job_path = job['container']['folder']

                            # Primero borramos los datos
                            shutil.rmtree(folder_job_path)

                            # Si es output vamos quitando borrando padres si estan vacios, con eso evitamos folders anidados vacios.
                            # Ej: Football_NY/other, Football_NY/

                            if folder_job_path.startswith(os.path.abspath(Config.OUTPUT_BASE_UPLOADS) + os.sep):
                                # Definimos la ruta relativa del directorio padre
                                rel_folder_ptr = folder_job_path.replace(os.path.abspath(Config.OUTPUT_BASE_UPLOADS) + os.sep, '')
                                rel_folder_ptr = os.path.dirname(rel_folder_ptr)

                                # Empezamos a borrar padres vacios hasta Config.OUTPUT_BASE_UPLOADS (SIN BORRARLO)
                                while True:
                                    # Si la ruta relativa esta vacia, finalizamos
                                    if rel_folder_ptr == os.sep or rel_folder_ptr == '':
                                        break

                                    # Si hay ficheros, no borramos.
                                    abs_folder_ptr = os.path.join(Config.OUTPUT_BASE_UPLOADS, rel_folder_ptr)
                                    if len(os.listdir(abs_folder_ptr)) > 0:
                                        break

                                    # De no ser asi borramos la carpeta
                                    shutil.rmtree(abs_folder_ptr)

                                    # Actualizamos el puntero al padre.
                                    rel_folder_ptr = os.path.dirname(rel_folder_ptr)
                            
                    except Exception:
                        traceback.print_exc()
                        pass
                    DB.files_jobs.remove({'job_id': ObjectId(job_id)})
                    DB.jobs.remove({'_id': ObjectId(job_id)})
            return True
        except:
            return False