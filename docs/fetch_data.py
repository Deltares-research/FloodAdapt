from pathlib import Path
import boto3
from botocore.client import Config

# The access key is created here https://s3-console.deltares.nl/access-keys
s3 = boto3.resource(
    's3',
    endpoint_url='https://s3.deltares.nl',
    aws_access_key_id='*****',
    aws_secret_access_key='*****',
    config=Config(signature_version='s3v4'),
    region_name='eu-west-1'
)

bucket_name = 'flood-adapt'
file_path_in_bucket = 'databases/charleston_test'

local_save_file = Path(__file__).parent / "data" / 'charleston_test'
local_save_file.parent.mkdir(parents=True, exist_ok=True)
s3.Bucket(bucket_name).download_file(file_path_in_bucket , local_save_file)
