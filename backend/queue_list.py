import datetime

from core.config import Config
from core.connection import CLIENT, DB, DESCENDING, ASCENDING

from pipeline.processes import *

from models.jobs import Job
from models.users import User
from models.preferences import Preferences
import traceback
from bson import ObjectId

class Queue(object):
	def __init__(self):
		pass

	def insert_job(self, job: Job, add_files = True):
		with CLIENT.start_session() as session:
				with session.start_transaction():
					DB.jobs.create_index([("name", 1), ("camera", 1)], unique=True)
					DB.files_jobs.create_index([("job_id", 1)])


					job_dict = job.dict()
					del job_dict['_id']
					aux_files = job_dict['container']['files']
					del job_dict['container']['files']
					#job_dict['done_files'] = 0
					#job_dict['total_files'] = len(aux_files)
					job.ref_id = DB.jobs.insert_one(job_dict).inserted_id

					if add_files: #job.container.type_container != Job.Container.FOLDER:
						# Añadimos los files
						for i, f in enumerate(aux_files):
							del f['_id']
							f['job_id'] = job.ref_id
							job.container.files[i].job_id = job.ref_id
						print(f"Queue files {aux_files}")
						r = DB.files_jobs.insert_many(aux_files)
						for f, id_ in zip(job.container.files, r.inserted_ids):
							f.ref_id = id_

						# Empezamos el preprocesado
						job.start_preprocess(self)

	def get_jobs(self, status=None):
		dict_info = {}
		if status is not None:
			dict_info['status'] = status

		jobs = DB.jobs.find(dict_info)
		if jobs.count() == 0:
			return None
		return [Job.parse(j) for j in jobs]

	def remove_annotation(self, file_id, user_id):
		with CLIENT.start_session() as session:
				with session.start_transaction():
					DB.files_jobs.update_one({'_id': file_id}, 
						{'$set': {'status': Job.Container.File.NOT_ANNOTATED, 'annotated_by': None, 'assigned_at': None}})
						
	def get_annotation(self, user):
		try:
			with CLIENT.start_session() as session:
				with session.start_transaction():
					#annotator_dict = user.dict()
					file_anno = DB.files_jobs.aggregate([
						{'$lookup': {
							'from': 'jobs',
							'localField': 'job_id',
							'foreignField': '_id',
							'as': 'join'
						}},
						{'$match': {'$and': [
							{'$or': [{'join.status': Job.NOT_STARTED}, {'join.status': Job.IN_PROCESS}]},
							{'$or': [{'status': Job.Container.File.NOT_ANNOTATED}, {'$and': [{'status': Job.Container.File.IN_PROCESS, 'annotated_by': ObjectId(user.ref_id)}]}]},
							{'join.visible': True},
							{'join.cancel': {'$in': [None, False]}}
						]}},
						{'$sort': {'join.priority': DESCENDING, 'join.created_at': ASCENDING}},
						{'$limit': 1},
					])

					file_anno = list(file_anno)
					if len(file_anno) == 0:
						return None, None, False, False
					else:
						file_anno = file_anno[0]
						is_new = file_anno['status'] = Job.Container.File.NOT_ANNOTATED
						assigned_at = datetime.datetime.utcnow()
						DB.files_jobs.update_one({'_id': file_anno['_id']}, {'$set': {'status': Job.Container.File.IN_PROCESS, 'annotated_by': ObjectId(user.ref_id), 'assigned_at': assigned_at}})
						
						DB.jobs.update_one({'_id': file_anno['job_id']}, {'$set': {'status': Job.IN_PROCESS}})
						job = Job.parse(file_anno['join'][0])
						
						if job.label_roi:
							is_first = DB.files_jobs.find_one({'job_id': ObjectId(file_anno['join'][0]['_id'])})
							has_to_label_roi = is_first['status'] in [Job.Container.File.NOT_ANNOTATED, Job.Container.File.IN_PROCESS] and is_first['_id'] == file_anno['_id']
						else:
							has_to_label_roi = False

						file_anno['join'][0]['container']['files'] = []
						file = Job.Container.File.parse(file_anno)
						file.status = Job.Container.File.IN_PROCESS
						file.annotated_by = ObjectId(user.ref_id)
						file.assigned_at = assigned_at
						file.start_getprocess(job)
						return file, job, has_to_label_roi, is_new
		
		except Exception as e:
			traceback.print_exc()
			return None, None, False, False

	def set_annotation(self, user, file, roi=None):
		if file is None:
			print('Error, no hay fichero')
			return False, None, None

		elif file.job_id is None:
			print('Error, el file no proviene de la BBDD.')
			return False, None, None

		try:
			with CLIENT.start_session() as session:
				with session.start_transaction():
					if roi is not None:
						DB.jobs.update_one({'_id': file.job_id}, {'$set': {'roi': roi}})

					aux_job = DB.jobs.find_one({'_id': file.job_id})
					if aux_job is not None:
						if aux_job['status'] != Job.IN_PROCESS:
							return False, 'Job not in process.', 'error_set_annotation_job_not_process'

					#annotator_dict = user.dict()
					prev_status = DB.files_jobs.find_one({'_id': file.ref_id})
					if prev_status is not None:
						prev_status = prev_status['status']
					else:
						return False, 'File not exists', 'error_set_annotation_file_not_exists'
					DB.files_jobs.update_one({'_id': file.ref_id}, {'$set': {'status': Job.Container.File.ANNOTATED, 'annotated_by': ObjectId(user.ref_id)}})
					
					# Ejecutamos la tarea especifica de la annotacion
					job = Job.parse(aux_job)
					file.start_setprocess(job) # No es en negundo plano, unicamente info del job sin files
					DB.files_jobs.update_one({'_id': file.ref_id}, {'$set': {'variables': file.variables}})
					
					# Solo sino ha sido anotado previamente lo contabilizamos
					if prev_status != Job.Container.File.ANNOTATED:
						# Miramos si hay mas datos a etiquetar
						#DB.jobs.update_one({'_id': file.job_id}, {'$inc': {'done_files': 1}})

						# Contabilizamos la marca de tiempo
						# TODO
						DB.files_jobs.update_one({'_id': file.ref_id}, 
							{'$set': {
								'finished_at': datetime.datetime.utcnow()
							}
						})

						# Job
						done_files, total_files = Job.get_count_files(file.job_id)
						job.update_trace('labeling', 'labeling', 100.0 * done_files / total_files)

						if done_files == total_files:
							DB.jobs.update_one({'_id': job.ref_id}, {'$set': {'status': Job.POSTPROCESS, 'labeling_at': datetime.datetime.utcnow()}})

							files = DB.files_jobs.find({'job_id': job.ref_id})
							job.container.files = [Job.Container.File.parse(f) for f in files]
							job.start_postprocess(self)
							return True, 'Job finished.', 'set_annotation_job_finished'
					return True, None, None
				
		except Exception as e:
			traceback.print_exc()
			return False, None
	
	def check_is_annotated(self, anno_id):
		with CLIENT.start_session() as session:
				with session.start_transaction():
					anno = DB.files_jobs.find_one({'_id': anno_id, 'status': Job.Container.File.ANNOTATED})
					return anno is not None

	def process_job_done(self, job: Job, key: str):
		DB.jobs.update_one(
			{'_id': job.ref_id}, 
			{"$set": {'status': job.status, key: datetime.datetime.utcnow(), 'variables': job.variables}}
		)

	def on_step_end(self, job: Job, attr, name):
		curr_step = getattr(job, attr).curr_step
		attr_step = attr + '_step'
		attr_name = attr + '_name'
		DB.jobs.update_one(
			{'_id': job.ref_id}, 
			{"$set": {attr_step: curr_step, attr_name: name}}
		)

