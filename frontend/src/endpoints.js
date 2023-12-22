let BACKEND_URL = process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:5000';

export const Endpoints = {
	USERS: {
		LOGIN: BACKEND_URL + '/user/login',
		CREATE: BACKEND_URL + '/user/create',
		LIST: BACKEND_URL + '/user/list',
		CHANGE_PASSWORD: BACKEND_URL + '/user/change_password',
		TOGGLE: BACKEND_URL + '/user/toggle',
	},

	JOBS: {
		CREATE: BACKEND_URL + '/job/create',
		LIST: BACKEND_URL + '/job/list',
		CHANGE_VISIBILITY: BACKEND_URL + '/job/visibility',
		CHANGE_TAGS: BACKEND_URL + '/job/tags',
		FRAME: {
			CHANGE_TAGS: BACKEND_URL + '/job/tags/frame',
		},
		REMOVE: BACKEND_URL + '/job/remove',
		REMOVE_ENTIRE: BACKEND_URL + '/job/remove/entire',
		
		FTP: {
			CREDENTIALS: BACKEND_URL + '/job/ftp/credentials',
			START: BACKEND_URL + '/job/ftp/start',
		},

		METRICS: BACKEND_URL + '/job/metrics',
		IMAGE_FRAME: BACKEND_URL + '/job/image/frame'
	},

	PREFERENCES: {
		GET: BACKEND_URL + '/preferences',
		TAGS: {
			FRAME: {
				ADD: BACKEND_URL + '/preferences/tags/frame/add',
				REMOVE: BACKEND_URL + '/preferences/tags/frame/remove',
			},

			ADD: BACKEND_URL + '/preferences/tags/add',
			REMOVE: BACKEND_URL + '/preferences/tags/remove',
		},
		SPORTS: {
			ADD: BACKEND_URL + '/preferences/sports/add',
			REMOVE: BACKEND_URL + '/preferences/sports/remove',
		}
	},

	METRICS: {
		GET: BACKEND_URL + '/job/metrics/annotation',
	}
};