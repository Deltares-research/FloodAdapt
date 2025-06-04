import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

__doc__ = """
This script downloads the read-only public data from the MinIO bucket `flood-adapt` at `s3.deltares.nl` to the local docs/_data directory.

Uploading files to the bucket can be done at this url (https://s3-console.deltares.nl), when on the Deltares VPN.

To access other data in the bucket, you need to provide your own access and secret keys.
To get access keys, please contact us at floodadapt@deltares.nl or create an issue on GitHub.

To use this script, you can do one of the following:
    1. set the environment variables manually
    2. create a `.env` file in the root of this project with the following content:
        ```
        MINIO_ACCESS_KEY=your_access_key
        MINIO_SECRET_KEY=your_secret_key
        ```
"""

def download_directory(client: Minio, path_in_bucket: str, output_path: Path, overwrite: bool = False, bucket_name = "flood-adapt") -> None:
    """Download a directory from a MinIO bucket to a local directory."""
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output path {output_path} already exists. Use `overwrite=True` to overwrite."
        )

    if not client.bucket_exists(bucket_name):
        raise ValueError(
            f"Bucket {bucket_name} does not exist. Please create it first."
        )

    objs = client.list_objects(
        bucket_name=bucket_name,
        prefix=path_in_bucket,
        recursive=True,
    )
    for obj in objs:
        rel_path = Path(obj.object_name).relative_to(path_in_bucket)
        client.fget_object(
            bucket_name=bucket_name,
            object_name=obj.object_name,
            file_path=str(output_path / rel_path),
        )
        print(
            f"Downloaded {rel_path} to {output_path / rel_path}"
        )

def prepare_client(access_key: str, secret_key: str) -> Minio:
    """Prepare the MinIO client."""
    return Minio(
        endpoint="s3.deltares.nl",
        access_key=access_key,
        secret_key=secret_key,
        region="eu-west-1",
    )

if __name__ == "__main__":
    data_dir = Path(__file__).parent / "_data"

    load_dotenv()

    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    if not (access_key and secret_key):
        raise ValueError(
            "Please set the MINIO_ACCESS_KEY and MINIO_SECRET_KEY environment variables. " \
            "Refer to the __doc__ at the top of this file for more information."
        )

    client = prepare_client(access_key=access_key, secret_key=secret_key)

    download_directory(
        client=client,
        path_in_bucket="public", # requires just the public access keys
        output_path=data_dir / "public",
        overwrite=True
    )

    download_directory(
        client=client,
        path_in_bucket="examples", # requires the non-public access keys
        output_path=data_dir / "examples",
        overwrite=True
    )

    download_directory(
        client=client,
        path_in_bucket="system", # requires the non-public access keys
        output_path=data_dir / "system",
        overwrite=True
    )
