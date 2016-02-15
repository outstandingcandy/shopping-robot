from qiniu import Auth
from qiniu import put_file
from qiniu import BucketManager

access_key = 'Cs3-GFcxRXIR9dDM01tyzzQp7WwmeplsoMranWee'
secret_key = 'vB7ijZS5utWxnrqO7JwCYLPByQ2YXsFfkSwJQGKt'

q = Auth(access_key, secret_key)

bucket_name = 'babazdm'
key = '00001b4951e726416de10ae1e0284213a55d9f9d.jpg'
mime_type = "image/jpeg"
params = {'x:a': 'a'}

token = q.upload_token(bucket_name, key)
localfile = '/root/mmh/image/full/00001b4951e726416de10ae1e0284213a55d9f9d.jpg'
ret, info = put_file(token, key, localfile, mime_type=mime_type, check_crc=True)
print(info)

