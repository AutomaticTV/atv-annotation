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