import os
import sys
from threading import Thread
from queue import Queue
import json
import numpy as np
import logging
import time
import re
import pymongo
import uuid
from pyunpack import Archive
import cv2
import traceback
import glob2
import glob
import shutil
from collections import namedtuple, defaultdict, Counter

from .pipeline_definition import PipelineDefinition
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.config import Config
from models.jobs import Job
from core.misc import *
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'library'))
from library.yolo_io import YOLOShapeParser
from library.pascal_voc_io import PascalVocWriter, PascalVocReader
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'library/darknet'))
from library.darknet.darknet import free_network_ptr,load_net_custom, make_image, network_width, network_height, copy_image_from_bytes, detect_image, free_image
"""
[Victor] When using GPU, GPU_AUTOLABEL_USE_QUEUE prevents the GPU from autolabelling more than one job at a time.
    True:
        Will que new jobs for inference and load one network at a time on the Memory. Avoids out of memory errors.
        However, once the job is put on the queue, the job status will change automatically to NOT_STARTED instead of showing PREPROCESS.
        This hasn't shown any problems yet, but need to be aware.
    False:
        Will load networks on Memory for inference as soon as files are ready. This can lead to out of memory errors.
        The job status issue does not happen here.
        If using this option, be aware that uploading many files and selecting the option "Each file one individual job" will most likely lead to out of memory error.
        Best practice is to upload a job and and wait until Preprocess status is done. With GPU inference this is fast.
"""
GPU_AUTOLABEL_USE_QUEUE = True

"""
[Victor] Before accessing a file in Corpus, we may need to sync the cache. with the following macro CORPUS_SYNC we control wheather we sync or not with
the system command "cat"
    True: Will use cat to sync the cache before using openCV to read the video file.
    False: Will not use cat to sync the cache before using openCV to read the video file.
"""
CORPUS_SYNC = False
"""
====================================
    PREPROCESS
====================================
"""


"""
    STANDARIZE
"""

class Regex:
    class TupleValue:
        ASC, DESC = True, False
        def __init__(self, value, order):
            self.value = value
            self.order = order

        def __eq__(self, b):
            return self.value == b.value

        def __ne__(self, b):
            return self.value != b.value

        def __lt__(self, b):
            cmp_val = self.value < b.value
            if self.order == self.ASC:
                return cmp_val
            else:
                return not cmp_val

        def __gt__(self, b):
            cmp_val = self.value > b.value
            if self.order == self.ASC:
                return cmp_val
            else:
                return not cmp_val

        def __le__(self, b):
            cmp_val = self.value <= b.value
            if self.order == self.ASC:
                return cmp_val
            else:
                return not cmp_val

        def __ge__(self, b):
            cmp_val = self.value >= b.value
            if self.order == self.ASC:
                return cmp_val
            else:
                return not cmp_val

    OrderingTuple = namedtuple("OrderingTuple", "index key type order cast")
    String, Number, Float = range(3)
    Types = {
        'string': {
            'cast': str,
            'type': String
        },
        'number': {
            'cast': int,
            'type': Number
        },
        'float': {
            'cast': float,
            'type': Float
        }
    }

def sort_files(files, key, reverse=False):
    files_order = map(lambda x: (x, key(x)), files)
    files_order = filter(lambda x: x[1] is not None, files_order)
    files_order = sorted(files_order, key=lambda x: x[1])
    files = map(lambda x: x[0], files_order)
    return files 

def __order_file(job):
    if job.container.order == 'CUSTOM (regex by name)':
        regex_types = []
        regex_pattern = job.container.order_regex
        for type_name in Regex.Types.keys():
            regex_types.append(("{%s:([0-9])+}" % (type_name, ), r"(?P<%s_asc_\1>\\w+)" % (type_name, )))
            regex_types.append(("{%s:asc:([0-9])+}" % (type_name, ), r"(?P<%s_asc_\1>\\w+)" % (type_name, )))
            regex_types.append(("{%s:desc:([0-9])+}" % (type_name, ), r"(?P<%s_desc_\1>\\w+)" % (type_name, )))

            regex_types.append(("{%s:ASC:([0-9])+}" % (type_name, ), r"(?P<%s_asc_\1>\\w+)" % (type_name, )))
            regex_types.append(("{%s:DESC:([0-9])+}" % (type_name, ), r"(?P<%s_desc_\1>\\w+)" % (type_name, )))

            regex_types.append(("{%s:ASCENDING:([0-9])+}" % (type_name, ), r"(?P<%s_asc_\1>\\w+)" % (type_name, )))
            regex_types.append(("{%s:DESCENDING:([0-9])+}" % (type_name, ), r"(?P<%s_desc_\1>\\w+)" % (type_name, )))

            regex_types.append(("{%s:ascending:([0-9])+}" % (type_name, ), r"(?P<%s_asc_\1>\\w+)" % (type_name, )))
            regex_types.append(("{%s:descending:([0-9])+}" % (type_name, ), r"(?P<%s_desc_\1>\\w+)" % (type_name, )))

        for search, replace in regex_types:
            regex_pattern = re.sub(search, replace, regex_pattern)

        regex_pattern = re.compile(regex_pattern)
        regex_keys = regex_pattern.groupindex.keys()
        map_to_order = []
        for k in regex_keys:
            data_type, asc_or_desc, index = k.split('_')
            regex_type = Regex.Types[data_type]
            map_to_order.append(Regex.OrderingTuple(int(index), 
                k, 
                regex_type['type'], 
                Regex.TupleValue.ASC if asc_or_desc == 'asc' else Regex.TupleValue.DESC,
                regex_type['cast']))
        map_to_order.sort(key=lambda x: x.index)

    def __order_func(file):
        nonlocal regex_pattern, map_to_order
        if isinstance(file, str):
            filepath = file
        elif isinstance(file, Job.Container.File):
            filepath = file.path

        if job.container.order == 'ASCEND BY NAME' or job.container.order == 'DESCEND BY NAME':
            return os.path.basename(filepath)

        elif job.container.order == 'ASCEND BY MOD. DATE' or job.container.order == 'DESCEND BY MOD. DATE':
            return int(os.path.getmtime(filepath))

        elif job.container.order == 'CUSTOM (regex by name)':
            try:
                filename = os.path.basename(filepath)
                match = regex_pattern.search(filename)
                if match is None:
                    return None

                fields = match.groupdict()

                output_order = []
                for i, map_order in enumerate(map_to_order):
                    data = fields[map_order.key]
                    data = map_order.cast(data)
                    output_order.append(Regex.TupleValue(data, map_order.order))
                output_order = tuple(output_order)
                return output_order
            except:
                return None

    return __order_func

def __process_video(job, on_error, video_file):
    video_folder = os.path.dirname(video_file)
    #  Since moving from metasan to dropbox, we use dropboxcache. We need to sync the cache before reading the video.
    if CORPUS_SYNC:
        logging.debug(f"Syncing corpus for file {video_file}")
        sync_time_start = time.time()
        os.system(f"cat {video_file} > /dev/null")
        sync_time_end = time.time()
        sync_elapsed_hhmmss = str(datetime.timedelta(seconds=sync_time_end - sync_time_start))
        logging.debug(f"Synced corpus for {video_file} in {sync_elapsed_hhmmss}")

    vid = cv2.VideoCapture(video_file)
    
    #Get info from video
    vid_fps = float(vid.get(cv2.CAP_PROP_FPS))
    vid_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vid_frame_count = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))

    try:
        logging.debug(f"job.container.params['start_time'] = {job.container.params['start_time']}")
        start_time = int(job.container.params['start_time'])
    except Exception as e:
        logging.error(e)
        start_time = 0
    logging.debug(f"start_time: {start_time}")
    try:
        logging.debug(f"job.container.params['end_time'] = {job.container.params['every']}")
        every_time = int(job.container.params['every'])
    except Exception as e:
        logging.error(e)
        every_time = 1
    logging.debug(f"every_time: {every_time}")
    try:
        logging.debug(f"job.container.params['duration'] = {job.container.params['duration']}")
        duration_time = int(job.container.params['duration'])
    except Exception as e:
        logging.error(e)
        duration_time = 0
    logging.debug(f"duration_time: {duration_time}")

    # Fast forward to first frame
    init_frame = int(start_time * vid_fps)
    if init_frame < 0 or init_frame >= vid_frame_count:
        logging.debug("Video init frame is out of bounds. defaulting to 0.")
        init_frame = 0

    final_frame = init_frame + round(duration_time * vid_fps) - 1
    if final_frame <= 0 or final_frame >= vid_frame_count:
        logging.debug("Video final frame is out of bounds. defaulting to last frame.")
        final_frame = vid_frame_count - 1

    every_frame = round(every_time * vid_fps)
    if every_frame <= 0:
        logging.debug("Video sampling period is out of bounds. defaulting to 1.")
        every_frame = 1

    image_name = 'img_' + job.name
    
    if init_frame > 0:
        logging.debug(f"Fast forwarding video to frame {init_frame}")
        for i in range(init_frame):
            _,_ = vid.read()
            if i%100 == 0:
                logging.debug(f"Fast forwarded {i} frames {video_file}")
    current_frame = init_frame

    list_frame_names = []
    cam_name = job.camera
    while True:
        if current_frame % every_frame == 0:
            # Extract images
            ret, frame = vid.read()

            # end of frames
            if not ret:
                logging.debug(f"Video capture returned false. {video_file}")
                break

            # Saves image
            image_name_frame = os.path.join(video_folder, image_name + '_' + str(current_frame) + '_' + cam_name + '.jpg')
            list_frame_names.append(image_name_frame)
            cv2.imwrite(image_name_frame, frame)

        # next frame
        current_frame += 1
        if current_frame > final_frame:
            logging.debug(f"Video capture reached final frame. {video_file}")
            break


    # [Victor]: Why did we delete the video after procesing?!?!
    #os.unlink(video_file)
    return list_frame_names

def __process_zip(job, on_error, zip_file):
    unzip_folder = os.path.dirname(zip_file)
    Archive(zip_file).extractall(unzip_folder)
    os.unlink(zip_file)

    files = []
    scan_files = glob2.glob(os.path.join(glob.escape(unzip_folder), '**', '*'))
    scan_files = sort_files(scan_files, key=__order_file(job), reverse='DESCEND' in job.container.order)

    for file_path in scan_files:
        if os.path.isfile(file_path):
            flatten_name = file_path.replace(unzip_folder, '').replace('/', '_').replace('\\', '_')
            if flatten_name[0] == '_':
                flatten_name = flatten_name[1:]

            if is_file(file_path):
                new_file_path = os.path.join(unzip_folder, flatten_name)
                shutil.move(file_path, new_file_path)

                file_annotation_path = get_annotation(file_path)
                if file_annotation_path is not None:
                    flatten_annotation_name = file_annotation_path.replace(unzip_folder, '').replace('/', '_').replace('\\', '_')
                    if flatten_annotation_name[0] == '_':
                        flatten_annotation_name = flatten_annotation_name[1:]
                    
                    new_file_annotation_path = os.path.join(unzip_folder, flatten_annotation_name)
                    shutil.move(file_annotation_path, new_file_annotation_path)
                    files.append((new_file_path, new_file_annotation_path))
                else:
                    files.append(new_file_path)

            elif is_video(file_path):
                new_file_path = os.path.join(unzip_folder, flatten_name)
                shutil.move(file_path, new_file_path)
                files += __process_video(job, on_error, new_file_path)

            elif is_annotation(file_path):
                pass

            else:
                os.unlink(file_path)
    
    # Remove useless folders
    for dir_path in os.listdir(unzip_folder):
        dir_path = os.path.join(unzip_folder, dir_path)
        if os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
            except:
                pass

    return files    

def __standarize(parent_name, step_name, output, job):
    on_error = {
        'files': [],
        'messages': [],
        'extras': [],
        'removes': [],
    }

    if job.container.type_container == Job.Container.IMAGE_FOLDER:
        new_files = []
        try:
            job.container.files = list(sort_files(job.container.files, key=__order_file(job), reverse='DESCEND' in job.container.order))
        except Exception as e:
            traceback.print_exc()
            on_error['files'].append("ALL")
            on_error['messages'].append('Error during image standarization.')
            on_error['extras'].append(str(e))
            on_error['removes'].append(True)
            if len(on_error['files']) > 0:
                job.create_error_on_file(**on_error, cancel=True)

        for i, f in enumerate(job.container.files):
            try:
                if is_file(f.path): # is file
                    file_annotation_path = get_annotation(f.path)
                    if file_annotation_path is not None:
                        new_files.append((f.path, file_annotation_path))
                    else:
                        new_files.append(f.path)
                else:
                    os.unlink(f.path)
            except Exception as e:
                traceback.print_exc()
                on_error['files'].append(f)
                on_error['messages'].append('Error during image standarization.')
                on_error['extras'].append(str(e))
                on_error['removes'].append(True)

            finally:
                job.update_trace(parent_name, step_name, 100.0 * (i + 1) / len(job.container.files))

        container = Job.Container(type_container=Job.Container.IMAGE_FOLDER, files=new_files, params=job.container.params, folder=job.container.folder)
        job.update_files(container)

        if len(on_error['files']) > 0:
            job.create_error_on_file(**on_error, cancel=False)

    elif job.container.type_container == Job.Container.VIDEO:
        try:
            video_file = job.container.files[0].path
            new_files = __process_video(job, on_error, video_file)
        
            container = Job.Container(type_container=Job.Container.IMAGE_FOLDER, files=new_files, params=job.container.params, folder=job.container.folder)
            job.update_files(container)

        except Exception as e:
            traceback.print_exc()
            on_error['files'].append(video_file)
            on_error['messages'].append('Error during video standarization.')
            on_error['extras'].append(str(e))
            on_error['removes'].append(True)

        finally:
            job.update_trace(parent_name, step_name, 100.0)
        
        if len(on_error['files']) > 0:
            job.create_error_on_file(**on_error, cancel=True)
            return None, True # Not continue steps

    elif job.container.type_container == Job.Container.ZIP:
        try:
            zip_file = job.container.files[0].path
            new_files = __process_zip(job, on_error, zip_file)

            if 'each_file_one_job' in job.container.params and job.container.params['each_file_one_job']:
                for i, target_file in enumerate(new_files):
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
                        container=Job.Container(type_container=job.container.FOLDER, files=[new_target_file], params=job.container.params, order=job.container.order, order_regex=job.container.order_regex, folder=new_target_folder),
                        visible=True,
                        comments=job.comments)
                    try:
                        Job.queue.insert_job(j)
                    except pymongo.errors.DuplicateKeyError:
                        shutil.rmtree(target_folder)

                Job.remove(job.ref_id)
                return None, True # Cancel current job
            else:
                container = Job.Container(type_container=Job.Container.IMAGE_FOLDER, files=new_files, params=job.container.params, folder=job.container.folder)
                job.update_files(container)
                job.update_trace(parent_name, step_name, 100.0)

        except Exception as e:
            traceback.print_exc()
            on_error['files'].append(zip_file)
            on_error['messages'].append('Error during unzip.')
            on_error['extras'].append(str(e))
            on_error['removes'].append(True)
            job.update_trace(parent_name, step_name, 100.0)

        if len(on_error['files']) > 0:
            job.create_error_on_file(**on_error, cancel=True)
            return None, True # Not continue steps

    elif job.container.type_container == Job.Container.FOLDER:
        new_files = []
        for i, f in enumerate(job.container.files):
            input_type = ''
            try:
                if is_video(f.path):
                    input_type = 'video'
                    new_files += __process_video(job, on_error, f.path)
                elif is_zip(f.path):
                    input_type = 'zip'
                    new_files += __process_zip(job, on_error, f.path)
                elif is_file(f.path): # is file
                    file_annotation_path = get_annotation(f.path)
                    if file_annotation_path is not None:
                        new_files.append((f.path, file_annotation_path))
                    else:
                        new_files.append(f.path)
                    input_type = 'file'
                else: # TOCHECK
                    os.unlink(f.path)

            except Exception as e:
                traceback.print_exc()
                on_error['files'].append(f)
                on_error['messages'].append('Error during folder standarization (%s).' % (input_type, ))
                on_error['extras'].append(str(e))
                on_error['removes'].append(True)

            finally:
                job.update_trace(parent_name, step_name, 100.0 * (i + 1) / len(job.container.files))

        container = Job.Container(type_container=Job.Container.IMAGE_FOLDER, files=new_files, params=job.container.params, folder=job.container.folder)
        job.update_files(container)

        if len(on_error['files']) > 0:
            job.create_error_on_file(**on_error, cancel=False)

"""
    AUTOLABELING
"""


def convert_points_to_bb(points):
        xmin = float('inf')
        ymin = float('inf')
        xmax = float('-inf')
        ymax = float('-inf')
        for p in points:
            x = p[0]
            y = p[1]
            xmin = min(x, xmin)
            ymin = min(y, ymin)
            xmax = max(x, xmax)
            ymax = max(y, ymax)

        # Martin Kersner, 2015/11/12
        # 0-valued coordinates of BB caused an error while
        # training faster-rcnn object detector.
        if xmin < 1:
            xmin = 1

        if ymin < 1:
            ymin = 1

        return (int(xmin), int(ymin), int(xmax), int(ymax))

def load_labels(image_path, image_shape, shapes):
    image_folder_path = os.path.dirname(image_path)
    image_folder_name = os.path.split(image_folder_path)[-1]
    image_file_name = os.path.basename(image_path)
    writer = PascalVocWriter(image_folder_name, image_file_name, image_shape, localImgPath=image_path)

    for label, points, _, _, difficult in shapes:
        bndbox = convert_points_to_bb(points)
        width = abs(bndbox[0]-bndbox[2])
        height = abs(bndbox[1]-bndbox[3])
        writer.addBndBox(bndbox[0], bndbox[1], width, height, label, difficult)
    writer.save(targetFile=os.path.splitext(image_path)[0] + Config.ANNOTATION_FILE)

def keys_exists(element, *keys):
    '''
    Check if *keys (nested) exists in `element` (dict).
    '''
    if not isinstance(element, dict):
        raise AttributeError('keys_exists() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True

def confidence_ellipse(m, cov, n_std=1):
    """
    Return the parametres of the confidence ellipse of a gaussian distribution with mean m and covariance matric cov
    """

    lambda_, v = np.linalg.eig(cov)
    lambda_ = np.sqrt(lambda_)

    Cx = m[0]
    Cy = m[1]
    Rx = lambda_[0]*2*n_std
    Ry = lambda_[1]*2*n_std
    theta = np.arccos(v[0, 0])#np.rad2deg(np.arccos(v[0, 0]))

    return Cx ,Cy ,Rx ,Ry ,theta

def sample_confidence(sample, m, cov, n_std=1):

    """
    Return weather a 2D sample is within the confidence ellipse of a gaussian distribution of mean m and covariance matrix cov
    """

    confidence = False

    Cx, Cy, Rx, Ry, theta = confidence_ellipse(m, cov, n_std)

    assert m.shape == sample.shape, "mean array shape {} differs from sample shape {}".format(m.shape, sample.shape)

    result = ((np.cos(theta)*(sample[0]-Cx) + np.sin(theta)*(sample[1]-Cy))**2)/((Rx/2.0)**2)
    result += ((np.sin(theta)*(sample[0]-Cx) - np.cos(theta)*(sample[1]-Cy))**2)/((Ry/2.0)**2)

    if result <= 1.0:
        confidence = True

    return confidence

def get_bbox_confidence(shapes,img_resolution=(1920,1080), bbox_stats=None):
    """
    This function iterates a list of shapes and returns a binary list with a 0 for all the bounding boxes that are outside of the image range
    or outside the confidence elipse given by the mean and covariance matrix in bbox stats (if available).
    """

    img_width, img_height = img_resolution[0], img_resolution[1]
    
    confidence_idx = np.ones(len(shapes),dtype=np.uint8)
    
    for curr_idx,shape in enumerate(shapes):
        label, points = shape[0],shape[1]
        bndbox = convert_points_to_bb(points)
        x,y,w,h = bndbox[0], bndbox[1], abs(bndbox[0]-bndbox[2]), abs(bndbox[1]-bndbox[3])

        # Check first if bounding box is outside of image range
        if (x < 0 or x >= img_width) or (x+w < 0 or x+w >= img_width) or (w < 1 or w > img_width):
            confidence_idx[curr_idx] = 0
            continue
        if (y < 0 or y >= img_height) or (y+h < 0 or y+h >= img_height) or (h < 1 or h > img_height):
            confidence_idx[curr_idx] = 0
            continue

        # If bbox is valid up to now, check if bbox_stats are available for current (label,resolution) and get confidence
        res = "{}x{}".format(int(img_width),int(img_height))
        if bbox_stats is not None and keys_exists(bbox_stats,label,res,'mean') and keys_exists(bbox_stats,label,res,'cov') and keys_exists(bbox_stats,label,res,'n_std'):
            m_stats = np.array(bbox_stats[label][res]['mean'])
            cov_stats = np.array(bbox_stats[label][res]['cov'])
            n_std_stats = bbox_stats[label][res]['n_std']

            if not sample_confidence(np.array([w,h]), m_stats, cov_stats, n_std=n_std_stats):
                confidence_idx[curr_idx] = 0
                continue

    return np.where(confidence_idx == 1)[0].tolist()

def predict_img(file, sport, network, names, thresh=0.5):

    img = cv2.imread(file.path)
    
    logging.debug("Allocating memory for darknet_image")
    darknet_image = make_image(network_width(network), network_height(network), 3)
    frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    frame_resized = cv2.resize(frame_rgb,
                               (network_width(network),
                                network_height(network)),
                               interpolation=cv2.INTER_LINEAR)
    
    logging.debug("Copying image to darknet_image")
    copy_image_from_bytes(darknet_image, frame_resized.tobytes())
    logging.debug("Image copied to darknet_image")

    start = time.time()
    logging.debug("Starting prediction")
    detections = detect_image(network, names, darknet_image, thresh=thresh)
    end = time.time()
    logging.debug("Prediction finished in {:.2f} seconds".format(end-start))

    logging.debug("Freeing darknet_image")
    free_image(darknet_image)
    logging.debug("darknet_image freed")
    
    if len(detections) > 0:
        yolo_shape_parser = YOLOShapeParser(img.shape, frame_resized.shape)
        yolo_shape_parser.detections_to_shape(detections)
        #[Victor] Check for possible detection errors here.
        predict_mode_bbox_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl/%s/bboxes.json' % (sport, )) #JSON contains mean and cov
        if os.path.exists(predict_mode_bbox_dist):
            try:
                with open(predict_mode_bbox_dist) as json_file:
                    bbox_statistics = json.load(json_file)
                    json_file.close()
                
                #with open cv imread height is in the first dimention, width in the second (third is channels)
                valid_bbox_idx = get_bbox_confidence(yolo_shape_parser.shapes,
                                                        img_resolution=(img.shape[1],img.shape[0]),
                                                        bbox_stats=bbox_statistics)
                logging.debug("Discarded {} YOLO labels from {}.".format(len(yolo_shape_parser.shapes)-len(valid_bbox_idx), file.path))
                yolo_shape_parser.shapes = [ yolo_shape_parser.shapes[valid_idx] for valid_idx in valid_bbox_idx]
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("\n",exc_type, fname, exc_tb.tb_lineno,e)
                pass
        load_labels(file.path, img.shape, yolo_shape_parser.shapes)

def autolabel_thread(autolabel_queue):
    while True:
        autolabel_task  = autolabel_queue.get()
        parent_name     = autolabel_task['parent_name']
        step_name       = autolabel_task['step_name']
        job             = autolabel_task['job']
        cfg             = autolabel_task['cfg']
        weights         = autolabel_task['weights']
        names           = autolabel_task['names']
        sport           = autolabel_task['sport']
        
        if not os.path.exists(cfg):
            logging.error("Network config file not found: %s" % (cfg, ))
            return
        if not os.path.exists(weights):
            logging.error("Network weights file not found: %s" % (weights, ))
            return
        if not os.path.exists(names):
            logging.error("Network names file not found: %s" % (names, ))
            return

        logging.debug("Loading network...")
        yolo_network = load_net_custom(cfg.encode('ascii'), weights.encode('ascii'), 0, 1) # cfg, weights, clear, batch
        logging.debug("Loaded YOLO network")

        with open(names) as f:
            yolo_names = f.read().strip().split("\n")
            f.close()
        
        on_error = {
            'files': [],
            'messages': [],
            'extras': [],
            'removes': [],
        }

        logging.debug("AUTOLABELLING for {}-{}".format(job.name,job.sport.lower()))
        init_time = time.time()

        for i,f in enumerate(job.container.files):
            try:
                # Check if there is an annotation associated to a file (to refine annotations)
                if 'annotation_path' in f.variables.keys() and f.variables['annotation_path'] is not None:
                    continue

                if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl', job.sport.lower())):
                    on_error['files'].append(f.path)
                    on_error['messages'].append('Error during autolabeling.')
                    on_error['extras'].append("Sport %s not exist in the deep learning models folder" % (job.sport.lower(), ))
                    on_error['removes'].append(False)

                predict_img(f, sport, yolo_network, yolo_names)
                f.update_variables({'annotation_path': os.path.splitext(f.path)[0] + Config.ANNOTATION_FILE, 'last_changes': 'autolabeling'})

            except Exception as e:
                traceback.print_exc()
                on_error['files'].append(f)
                on_error['messages'].append('Error during autolabeling.')
                on_error['extras'].append(str(e))
                on_error['removes'].append(False)

            finally:
                job.update_trace(parent_name, step_name, 100.0 * (i + 1) / len(job.container.files))
                end_time = time.time()
                #get elapsed time in hh:mm:ss format with no decimals
                elapsed_time = time.strftime("%H:%M:%S", time.gmtime(end_time - init_time))
                logging.info("JOB {}: {}/{} Elapsed time {}".format(job.name, i + 1, len(job.container.files), elapsed_time))

        try:
            if yolo_network is not None:
                logging.debug("Freeing network pointer for {}-{}".format(job.name,job.sport.lower()))
                free_network_ptr(yolo_network)
                del yolo_network
                logging.debug(f"Darknet Network memory freed")
                #time.sleep(10)
            if yolo_names is not None:
                del yolo_names
            logging.debug("AUTOLABELLING for {}-{} finished".format(parent_name,job.sport.lower()))
        except Exception as e:
            print("Error during network memory free: ", e)

        if len(on_error['files']) > 0:
            job.create_error_on_file(**on_error, cancel=False)

if GPU_AUTOLABEL_USE_QUEUE:
    autolabel_queue = Queue(maxsize=1)
    Thread(target=autolabel_thread, args=(autolabel_queue,)).start()

def __auto_labeling(parent_name, step_name, output, job):

    if GPU_AUTOLABEL_USE_QUEUE:
        global autolabel_queue
    if 'enable_autolabeling' in job.container.params.keys() and not job.container.params['enable_autolabeling']:
        return

    # Load network and names
    sport           = job.sport.lower()
    net_cfg         = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl/%s/model.cfg' % (sport, ))
    net_weights     = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl/%s/model.weights' % (sport, ))
    net_names       = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl/%s/model.names' % (sport, ))

    autolabel_task = {
        'parent_name': parent_name,
        'step_name': step_name,
        'job': job,
        'cfg': net_cfg,
        'weights': net_weights,
        'names': net_names,
        'sport': sport,
    }
    if GPU_AUTOLABEL_USE_QUEUE:
        autolabel_queue.put(autolabel_task)
        return

    if not os.path.exists(net_cfg):
        logging.error("Network config file not found: %s" % (net_cfg, ))
        return
    if not os.path.exists(net_weights):
        logging.error("Network weights file not found: %s" % (net_weights, ))
        return
    if not os.path.exists(net_names):
        logging.error("Network names file not found: %s" % (net_names, ))
        return
    

    logging.debug("Loading network...")
    yolo_network = load_net_custom(net_cfg.encode('ascii'), net_weights.encode('ascii'), 0, 1) # cfg, weights, clear, batch
    logging.debug("Loaded YOLO network")
    #time.sleep(5)
    #logging.debug("Freeing network pointer for {}-{}".format(job.name,job.sport.lower()))
    #free_network_ptr(yolo_network)
    #del yolo_network
    #logging.debug(f"Darknet Network memory freed")
    #time.sleep(5)

    #gc.collect()

    with open(net_names) as f:
        yolo_names = f.read().strip().split("\n")
        f.close()
    
    on_error = {
        'files': [],
        'messages': [],
        'extras': [],
        'removes': [],
    }

    logging.debug("AUTOLABELLING for {}-{}".format(job.name,job.sport.lower()))
    init_time = time.time()
    for i, f in enumerate(job.container.files):
        try:
            # Check if there is an annotation associated to a file (to refine annotations)
            if 'annotation_path' in f.variables.keys() and f.variables['annotation_path'] is not None:
                continue

            if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl', job.sport.lower())):
                on_error['files'].append(f.path)
                on_error['messages'].append('Error during autolabeling.')
                on_error['extras'].append("Sport %s not exist in the deep learning models folder" % (job.sport.lower(), ))
                on_error['removes'].append(False)

            predict_img(f, sport, yolo_network, yolo_names)
            f.update_variables({'annotation_path': os.path.splitext(f.path)[0] + Config.ANNOTATION_FILE, 'last_changes': 'autolabeling'})

        except Exception as e:
            traceback.print_exc()
            on_error['files'].append(f)
            on_error['messages'].append('Error during autolabeling.')
            on_error['extras'].append(str(e))
            on_error['removes'].append(False)

        finally:
            job.update_trace(parent_name, step_name, 100.0 * (i + 1) / len(job.container.files))
            end_time = time.time()
            #get elapsed time in hh:mm:ss format with no decimals
            elapsed_time = time.strftime("%H:%M:%S", time.gmtime(end_time - init_time))
            logging.info("JOB {}: {}/{} Elapsed time {}".format(job.name, i + 1, len(job.container.files), elapsed_time))
    
    try:
        if yolo_network is not None:
            logging.debug("Freeing network pointer for {}-{}".format(job.name,job.sport.lower()))
            free_network_ptr(yolo_network)
            del yolo_network
            logging.debug(f"Darknet Network memory freed")
            #time.sleep(10)
        if yolo_names is not None:
           del yolo_names
        logging.debug("AUTOLABELLING for {}-{} finished".format(parent_name,job.sport.lower()))
    except Exception as e:
        print("Error during network memory free: ", e)

    if len(on_error['files']) > 0:
        job.create_error_on_file(**on_error, cancel=False)

Preprocess = PipelineDefinition(name='preprocess', pipe=[PipelineDefinition.Step('Standarize', __standarize), PipelineDefinition.Step('AutoLabeling', __auto_labeling)])

"""
====================================
    FILEPROCESS
====================================
"""
"""
def __b(parent_name, step_name, output, file, job):
    return file
"""

def __push_metrics(parent_name, step_name, output, file, job):
    annotation = PascalVocReader(file.variables['annotation_path'])
    class_counter = Counter()
    class_pos = defaultdict(lambda: Counter())
    for c, pos, _, _, _ in annotation.shapes:
        class_counter[c] += 1

        norm_pos = (pos[2][0] + pos[0][0]) // 2, (pos[2][1] + pos[0][1]) // 2
        norm_pos = round(norm_pos[0] / 32) * 32, round(norm_pos[1] / 32) * 32
        norm_pos = str(norm_pos[0]) + '_' + str(norm_pos[1])
        class_pos[c][norm_pos] += 1

    file.variables['metrics'] = {
        'class': class_counter,
        'position': class_pos
    }

#File = PipelineDefinition.Step('file', __b)
GetFileProcess = PipelineDefinition(name='getfileprocess', pipe=[]) #File])

File = PipelineDefinition.Step('Push Metrics', __push_metrics)
SetFileProcess = PipelineDefinition(name='setfileprocess', pipe=[File])

"""
====================================
    POSTPROCESS
====================================
"""
def __save_on_output(parent_name, step_name, output, job):
    print('OUTPUT')
    on_error = {
        'files': [],
        'messages': [],
        'extras': [],
        'removes': [],
    }

    new_folder = os.path.join(Config.OUTPUT_BASE_UPLOADS, job.get_output_name())
    os.makedirs(new_folder, exist_ok=True)

    if job.label_roi:
        with open(os.path.join(new_folder, 'roi.json'), 'w') as f:
            json.dump(job.roi, f, indent=4)
    for i, f in enumerate(job.container.files):
        try:
            new_file_path = os.path.join(new_folder, os.path.basename(f.path))
            #os.symlink(f.path, new_file_path)     
            shutil.move(f.path, new_file_path)

            f.update_path(new_file_path)

            if 'annotation_path' in f.variables:
                new_file_path_annotation = os.path.join(new_folder, os.path.basename(f.variables['annotation_path']))
                #os.symlink(f.variables['annotation_path'], new_file_path_annotation)  
                shutil.move(f.variables['annotation_path'], new_file_path_annotation)      
                f.update_variables({'annotation_path': new_file_path_annotation})

        except Exception as e:
            traceback.print_exc()
            on_error['files'].append(f)
            on_error['messages'].append('Error while saving output.')
            on_error['extras'].append(str(e))
            on_error['removes'].append(True)

        finally:
            job.update_trace(parent_name, step_name, 100.0 * (i + 1) / len(job.container.files))

        job.update_container_folder(new_folder)

    if len(on_error['files']) > 0:
        job.create_error_on_file(**on_error, cancel=False)

def __generate_txt(parent_name, step_name, output, job):
    print('TXT GEN')
    on_error = {
        'files': [],
        'messages': [],
        'extras': [],
        'removes': [],
    }

    mapping_classes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'library', 'resources_dl/%s/mapping_classes.json' % (job.sport, ))
    if not os.path.exists(mapping_classes_path):
        job.add_alert('Model without mapping_classes.json.')
        return

    with open(mapping_classes_path, 'r') as f:
        mapping_classes = json.load(f)

    for i, f in enumerate(job.container.files):
        try:
            file_path = f.path
            if 'annotation_path' in f.variables:
                annotation_path = f.variables['annotation_path']

                annotation = PascalVocReader(annotation_path)
                str_data = ""
                for c, pos, _, _, _ in annotation.shapes:
                    x1, y1, x2, y2 = pos[0][0], pos[0][1], pos[2][0], pos[2][1]

                    cx = (x2 + x1) // 2
                    cy = (y2 + y1) // 2
                    w = (x2 - x1)
                    h = (y2 - y1)

                    cx /= annotation.img_width
                    cy /= annotation.img_height
                    w /= annotation.img_width
                    h /= annotation.img_height

                    bb = " ".join([str(cx), str(cy), str(w), str(h)])

                    if c in mapping_classes.keys() and mapping_classes[c] is not None:
                        str_data += str(mapping_classes[c]) + " " + bb + "\n"

                print(os.path.splitext(annotation_path)[0] + ".txt")
                with open(os.path.splitext(annotation_path)[0] + ".txt", 'w') as f:
                    f.write(str_data)


        except Exception as e:
            traceback.print_exc()
            on_error['files'].append(f)
            on_error['messages'].append('Error during generate txt.')
            on_error['extras'].append(str(e))
            on_error['removes'].append(True)

        finally:
            job.update_trace(parent_name, step_name, 100.0 * (i + 1) / len(job.container.files))

    if len(on_error['files']) > 0:
        job.create_error_on_file(**on_error, cancel=False)

GeneratingTxt = PipelineDefinition.Step('GeneratingTxt', __generate_txt)
SavingOutput = PipelineDefinition.Step('SavingOutput', __save_on_output)
Postprocess = PipelineDefinition(name='postprocess', pipe=[SavingOutput, GeneratingTxt])

"""
    ASSIGNATION
"""
Job.Preprocess = Preprocess
Job.Postprocess = Postprocess
Job.SetFileProcess = SetFileProcess
Job.GetFileProcess = GetFileProcess