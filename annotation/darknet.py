from ctypes import *
import cv2
from pathlib import Path, PureWindowsPath
import os
import random

# Variables
dl_resources = Path(__file__).parent / 'resources_dl'
if os.name == 'posix':
    lib_path = dl_resources / 'darknet' / './libdarknet.so'
elif os.name == 'nt':
    cwd = dl_resources / 'darknet' / 'win' / 'darknet' / 'lib'
    cwd = PureWindowsPath(cwd)
    os.environ['PATH'] = r'str(cwd)' + ';' + os.environ['PATH']
    lib_path = dl_resources / 'darknet' / 'dark.dll'
    lib_path = PureWindowsPath(lib_path)
    # Reset the dll search path loading a dll from the current directory works.
    # https://github.com/pyinstaller/pyinstaller/issues/1609
    #print(lib_path)
    #print(windll.kernel32.SetDllDirectoryW(str(lib_path)))
    windll.kernel32.SetDllDirectoryW(str(lib_path))

lib = CDLL(str(lib_path), RTLD_GLOBAL)


def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1


def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr


class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]


class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int),
                ("uc", POINTER(c_float)),
                ("points", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]


class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]


lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

copy_image_from_bytes = lib.copy_image_from_bytes
copy_image_from_bytes.argtypes = [IMAGE,c_char_p]

def network_width(net):
    return lib.network_width(net)

def network_height(net):
    return lib.network_height(net)

predict = lib.network_predict_ptr
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int), c_int]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict_ptr
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

load_net_custom = lib.load_network_custom
load_net_custom.argtypes = [c_char_p, c_char_p, c_int, c_int]
load_net_custom.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)

predict_image_letterbox = lib.network_predict_image_letterbox
predict_image_letterbox.argtypes = [c_void_p, IMAGE]
predict_image_letterbox.restype = POINTER(c_float)


def array_to_image(arr):
    import numpy as np
    # need to return old values to avoid python freeing memory
    arr = arr.transpose(2, 0, 1)
    c = arr.shape[0]
    h = arr.shape[1]
    w = arr.shape[2]
    arr = np.ascontiguousarray(arr.flat, dtype=np.float32) / 255.0
    data = arr.ctypes.data_as(POINTER(c_float))
    im = IMAGE(w, h, c, data)
    return im, arr


def classify(net, meta, im):
    out = predict_image(net, im)
    res = []
    for i in range(meta.classes):
        if alt_names is None:
            nameTag = meta.names[i]
        else:
            nameTag = alt_names[i]
        res.append((nameTag, out[i]))
    res = sorted(res, key=lambda x: -x[1])
    return res


def detect(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45, debug= False):
    """
    Performs the meat of the detection
    """
    #pylint: disable= C0321
    im = load_image(image, 0, 0)
    if debug:
        print("Loaded image")
    ret = detect_image(net, meta, im, thresh, hier_thresh, nms, debug)
    free_image(im)
    if debug:
        print("freed image")
    return ret


def detect_image(net, num_classes, im, thresh=.5, hier_thresh=.5, nms=.45, debug= False):
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    letter_box = 0

    dets = get_network_boxes(net, im.w, im.h, thresh, hier_thresh, None, 0, pnum, letter_box)

    num = pnum[0]
    if nms:
        do_nms_sort(dets, num, num_classes, nms)

    res = []
    for j in range(num):
        for i in range(num_classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                nameTag = alt_names[i]
                res.append((nameTag, dets[j].prob[i], (b.x, b.y, b.w, b.h)))

    res = sorted(res, key=lambda x: -x[1])
    free_detections(dets, num)

    return res


def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax


def cvDrawBoxes(detections, img):
    for detection in detections:
        x, y, w, h = detection[2][0],\
            detection[2][1],\
            detection[2][2],\
            detection[2][3]
        xmin, ymin, xmax, ymax = convertBack(
            float(x), float(y), float(w), float(h))
        pt1 = (xmin, ymin)
        pt2 = (xmax, ymax)
        cv2.rectangle(img, pt1, pt2, (0, 255, 0), 1)
        cv2.putText(img,
                    detection[0] +
                    " [" + str(round(detection[1] * 100, 2)) + "]",
                    (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    [0, 255, 0], 2)
    return img


net_main = None
meta_main = None
alt_names = None


def YOLO(img, config_path, weight_path, names_path, thresh=0.5, init_net=False):
    global net_main, meta_main, alt_names

    if not config_path.exists():
        raise ValueError("Invalid config path `" + str(config_path))
    if not weight_path.exists():
        raise ValueError("Invalid weight path `" + str(weight_path))
    if not names_path.exists():
        raise ValueError("Invalid names file path `" + str(names_path))

    if (net_main is None) or init_net:
        net_main = load_net_custom(str(config_path).encode("ascii"), str(weight_path).encode("ascii"), 0, 1)  # batch size = 1

    if (alt_names is None) or init_net:
        with open(names_path, 'r') as r_names:
            names = r_names.read()
            alt_names = names.split('\n')[:-1]

    # Create an image we reuse for each detect
    darknet_image = make_image(network_width(net_main), network_height(net_main), 3)
    frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    frame_resized = cv2.resize(frame_rgb,
                               (network_width(net_main),
                                network_height(net_main)),
                               interpolation=cv2.INTER_LINEAR)

    copy_image_from_bytes(darknet_image, frame_resized.tobytes())
    detections = detect_image(net_main, len(alt_names), darknet_image, thresh=thresh)
    return detections, frame_resized


class YOLOShapeParser:
    def __init__(self, img_orig_shape, img_yolo_shape):
        self.shapes = []
        self.im_orig_h = img_orig_shape[0]
        self.im_orig_w = img_orig_shape[1]
        self.im_yolo_h = img_yolo_shape[0]
        self.im_yolo_w = img_yolo_shape[1]

    def detections_to_shape(self, detections):
        for det in detections:
            label, xmin, ymin, xmax, ymax = self.yolo_to_shape(det)
            self.add_shape(label, xmin, ymin, xmax, ymax, False)

    def yolo_to_shape(self, detection):
        label, xcen, ycen, w, h = detection[0], detection[2][0], detection[2][1], detection[2][2], detection[2][3]

        xmin = float(xcen) - (float(w) / 2)
        xmax = float(xcen) + (float(w) / 2)
        ymin = float(ycen) - (float(h) / 2)
        ymax = float(ycen) + (float(h) / 2)

        scale_factor_h = self.im_orig_h / self.im_yolo_h
        scale_factor_w = self.im_orig_w / self.im_yolo_w

        xmin = int(scale_factor_w * xmin)
        xmax = int(scale_factor_w * xmax)
        ymin = int(scale_factor_h * ymin)
        ymax = int(scale_factor_h * ymax)

        return label, xmin, ymin, xmax, ymax

    def add_shape(self, label, xmin, ymin, xmax, ymax, difficult):
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        self.shapes.append((label, points, None, None, difficult))


def main():
    import time

    sport = 'basketball'
    cfg = dl_resources / sport / 'model.cfg'
    weights = dl_resources / sport / 'model.weights'
    names = dl_resources / sport / 'model.names'

    img_path = dl_resources / sport / 'sample.jpg'
    img = cv2.imread(str(img_path))

    while 1:
        init = time.time()
        detections, frame_resized = YOLO(img, cfg, weights, names)
        print('Lasted: ', time.time() - init)
        image = cvDrawBoxes(detections, frame_resized)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        cv2.imshow('h', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    main()
