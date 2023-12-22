import schedule
import time
import threading

from .config import Config
from .connection import CLIENT, DB, DESCENDING, ASCENDING

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.processes import *
from models.jobs import Job

class Cron:
	@staticmethod
	def __check_not_finish_files():
		with CLIENT.start_session() as session:
			with session.start_transaction():
				job_files_ids = DB.files_jobs.aggregate([
					{'$match':
						{'status': Job.Container.File.IN_PROCESS}
					},
					{'$project': 
						{'_id': 1,
						'days':
							{'$divide': [{'$subtract': [datetime.datetime.utcnow(), '$assigned_at']}, 1000]} # 1 dia en ms
						}
					},

					{'$match':
						{'days': {'$gt': Config.GET_ANNOTATION_TIMEOUT}}
					},

					{'$project': {'_id': 1}}
				])
				job_files_ids = [f['_id'] for f in job_files_ids]
				DB.files_jobs.update_many({'_id': {'$in': job_files_ids}},
					{'$set': {'assigned_at': None, 'annotated_by': None, 'status': Job.Container.File.NOT_ANNOTATED}})

	@staticmethod
	def start():
		schedule.every(1).minutes.do(Cron.__check_not_finish_files)

		def __thread():
			while True:
				schedule.run_pending()
				time.sleep(1)
		threading.Thread(target=__thread).start()

Cron.start()