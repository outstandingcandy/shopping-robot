import os
import scrapy
from scrapy.contrib.pipeline.images import ImagesPipeline
from scrapy.exceptions import DropItem
from scrapy import log

from qiniu import Auth
from qiniu import put_file
from qiniu import BucketManager
import image_cropper

class MyImagesPipeline(ImagesPipeline):
    access_key = 'Cs3-GFcxRXIR9dDM01tyzzQp7WwmeplsoMranWee'
    secret_key = 'vB7ijZS5utWxnrqO7JwCYLPByQ2YXsFfkSwJQGKt'
    q = Auth(access_key, secret_key)
    bucket_name = 'babazdm'
    mime_type = "image/jpeg"
    image_dir = '/root/mmh/image/'

    def item_completed(self, results, item, info):
        image_paths = [x['path'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem("Item contains no images")
        for localfile in image_paths:
            key = localfile.split('/')[-1]
            full_image_key = 'full/' + key
            full_image_path = MyImagesPipeline.image_dir + full_image_key
            if not os.path.exists(full_image_path):
                continue
            token = MyImagesPipeline.q.upload_token(MyImagesPipeline.bucket_name, full_image_key)
            put_file(token, full_image_key, full_image_path, mime_type=MyImagesPipeline.mime_type, check_crc=True)
            square_image_key = 'square/' + key
            square_image_path = MyImagesPipeline.image_dir + square_image_key
            image_cropper.process(full_image_path, square_image_path)
            token = MyImagesPipeline.q.upload_token(MyImagesPipeline.bucket_name, square_image_key)
            put_file(token, square_image_key, square_image_path, mime_type=MyImagesPipeline.mime_type, check_crc=True)
            log.msg("put %s to qiniu cloud" % (square_image_path), level=log.INFO)
            os.remove(full_image_path)
            os.remove(square_image_path)
        return item
