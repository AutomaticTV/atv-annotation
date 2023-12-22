import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.connection import CLIENT, DB, DESCENDING, ASCENDING
from pipeline.processes import Preprocess, Postprocess

from models.jobs import Job
from models.users import User

class Preferences:
    """
        Class that represents the preferences of the backend system, includes: sport, tags and frame tags.
    """
    @staticmethod
    def create():
        """
            Create new preferences into the DB.
        """
        DB.preferences.drop()
        DB.preferences.insert_one({
            'tags': {'generic': ['cloudy', 'sun', 'bad day', 'jitter']},
            'frame_tags': {'generic': ['bad_frame']},
            'sports': ['football_11', 'basketball', 'ice_hockey', 'volleyball', 'handball', 'futsal', 'generic']  
        })

    @staticmethod
    def get():
        """
            Return preferences from the DB and additional information:
                - sports_with_autolabeling.
                - total_preprocess_steps.
                - total_postprocess_steps.
                - jobs. 
                - users
        """
        response = {}
        with CLIENT.start_session() as session:
                with session.start_transaction():
                    pref = DB.preferences.find_one({})                    
                    response['tags'] = pref['tags']                
                    response['frame_tags'] = pref['frame_tags']
                    response['sports'] = pref['sports']
                    response['sports_with_autolabeling'] = [os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl', sport.lower())) for sport in pref['sports']]
                    response['total_preprocess_steps'] = len(Preprocess.pipe)
                    response['total_postprocess_steps'] = len(Postprocess.pipe)
                    response['jobs'] = Job.list()
                    response['users'] = User.list()

        return response

    @staticmethod
    def add_tag(sport, tag):
        """
            Add a new tag for an specific sport.
        """
        try:
            if sport is not None:
                DB.preferences.update({}, {
                    '$push': {'tags.' + sport: tag}
                }, upsert=True)
            else:
                DB.preferences.update({}, {
                    '$push': {'tags.generic': tag}
                }, upsert=True)
            return True
        except:
            return False

    @staticmethod
    def remove_tag(sport, tag):
        """
            Remove tag for an specific sport.
        """
        try:
            if sport is not None:
                DB.preferences.update({}, {
                    '$pull': {'tags.' + sport: tag}
                }, upsert=True)
            else:
                DB.preferences.update({}, {
                    '$pull': {'tags.generic': tag}
                }, upsert=True)
            return True
        except:
            return False

    @staticmethod
    def get_tags(sport):
        """
            Return the tags for a specific sport
        """
        with CLIENT.start_session() as session:
                with session.start_transaction():
                    tags = DB.preferences.find_one()
                    if sport in tags['tags']:
                        return tags['tags'][sport] + tags['tags']['generic']
                    else:
                        return tags['tags']['generic']

    @staticmethod
    def add_frame_tag(sport, frame_tag):
        """
            Add a new frame tag for an specific sport.
        """
        try:
            if sport is not None:
                DB.preferences.update({}, {
                    '$push': {'frame_tags.' + sport: frame_tag}
                }, upsert=True)
            else:
                DB.preferences.update({}, {
                    '$push': {'frame_tags.generic': frame_tag}
                }, upsert=True)
            return True
        except:
            return False

    @staticmethod
    def remove_frame_tag(sport, frame_tag):
        """
            Remove frame tag for an specific sport.
        """
        try:
            if sport is not None:
                DB.preferences.update({}, {
                    '$pull': {'frame_tags.' + sport: frame_tag}
                }, upsert=True)
            else:
                DB.preferences.update({}, {
                    '$pull': {'frame_tags.generic': frame_tag}
                }, upsert=True)
            return True
        except:
            return False

    @staticmethod
    def get_frame_tags(sport):
        """
            Return the frame tags for a specific sport
        """
        with CLIENT.start_session() as session:
                with session.start_transaction():
                    frame_tags = DB.preferences.find_one()
                    if sport in frame_tags['frame_tags']:
                        return frame_tags['frame_tags'][sport] + frame_tags['frame_tags']['generic']
                    else:
                        return frame_tags['frame_tags']['generic']

    
    @staticmethod
    def add_sport(sport):
        """
            Add a new sport
        """
        try:
            DB.preferences.update({}, {
                '$push': {'sports': sport}
            })
            # sport_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl', sport.lower())
            # if not os.path.exists(sport_path):
            #     os.mkdir(sport_path)
            return True
        except:
            return False

    @staticmethod
    def remove_sport(sport):
        """
            Remove an specific sport
        """
        try:
            DB.preferences.update({}, {
                '$pull': {'sports': sport}
            })
            return True
        except:
            return False

# Preferences.create()