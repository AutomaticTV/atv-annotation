import cv2
import base64
import numpy as np
from PIL import Image as PILlib
import io
import re

class Images:
    @staticmethod
    def read(im_path):
        return cv2.imread(im_path)

    @staticmethod
    def unpack_im(pack, image_type):
        if image_type == 'numpy':
            b64, dtype, shape = pack
            return np.frombuffer(base64.decodebytes(b64.encode()), dtype=dtype).reshape(shape)
        
        elif image_type == 'jpeg' or image_type == 'jpg':
            m = re.search(r'base64,(.*)', pack)
            if m is None:
                raise IndexError

            imgstring = m.group(1)
            
            # aplicamos una correccion para evitar un error de padding
            imgbyte = imgstring.encode()
            pad = len(pack.partition(",")[2]) % 4
            imgbyte += b"="*pad
            image = cv2.imdecode(np.frombuffer(io.BytesIO(base64.b64decode(imgbyte)).getbuffer(), np.uint8), -1)
            
            return image[..., :3]

    @staticmethod
    def pack_im(im, image_type):
        if image_type == 'numpy':
            return base64.b64encode(np.ascontiguousarray(im)).decode(), im.dtype.name, im.shape

        elif image_type == 'jpeg' or image_type == 'jpg':
            return 'data:image/jpg; base64,' + base64.b64encode(cv2.imencode('.jpg', im)[1]).decode("utf-8")

if __name__ == '__main__':
    im = Images.read('/home/automatictv/Descargas/WhatsApp Image.jpeg')
    im2 = Images.unpack_im(Images.pack_im(im, 'numpy'), 'numpy')
    cv2.imshow('images', np.concatenate((im, im2), axis=1))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    im2 = Images.unpack_im(Images.pack_im(im, 'jpg'), 'jpg')
    cv2.imshow('images', np.concatenate((im, im2), axis=1))
    cv2.waitKey(0)
    cv2.destroyAllWindows()
