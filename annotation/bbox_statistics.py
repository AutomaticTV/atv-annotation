import json
import numpy as np

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

    Shapes must be generated with (or in the same format as) YOLOShapeParser.shapes -> check detections_to_shape() method
    """

    img_width, img_height = img_resolution[0], img_resolution[1]
    
    confidence_idx = np.ones(len(shapes),dtype=np.uint8)
    
    for curr_idx,shape in enumerate(shapes):
        label, points = shape[0],shape[1]
        bndbox = convert_points_to_bb(points)
        x,y,w,h = bndbox[0], bndbox[1], abs(bndbox[0]-bndbox[2]), abs(bndbox[1]-bndbox[3])

        # Check first if bounding box is outside of image range
        if (x < 0 or x >= img_width) or (x+w < 0 or x+w >= img_width) or (w < 0 or w >= img_width):
            confidence_idx[curr_idx] = 0
            continue
        if (y < 0 or y >= img_height) or (y+h < 0 or y+h >= img_height) or (h < 0 or h >= img_height):
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