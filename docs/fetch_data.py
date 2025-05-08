import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

__doc__ = """
This script downloads the read-only public data from the MinIO bucket `flood-adapt` at `s3.deltares.nl` to the local docs/_data directory.

Uploading files to the bucket can be done at this url (https://s3-console.deltares.nl), when on the Deltares VPN.

To access other data in the bucket, you need to provide your own access and secret keys.
To get non-public access keys, please contact us at floodadapt@deltares.nl
"""

READ_ONLY_ACCESS_KEY = "AZBGNdxd45VEPFp1IiGe" # read-only access key for flood-adapt/public
READ_ONLY_SECRET_KEY = "nHnbTeZ4iAWlM2i5veikZq9UGvOZogUWzi4tLftZ" # read-only access key for flood-adapt/public


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

    access_key = os.getenv("MINIO_ACCESS_KEY") or READ_ONLY_ACCESS_KEY
    secret_key = os.getenv("MINIO_SECRET_KEY") or READ_ONLY_SECRET_KEY

    client = prepare_client(access_key=access_key, secret_key=secret_key)

    download_directory(
        client=client,
        path_in_bucket="public", # requires just the public access keys
        output_path=data_dir / "public",
        overwrite=True
    )

    if os.getenv("MINIO_ACCESS_KEY") and os.getenv("MINIO_SECRET_KEY"):
        download_directory(
            client=client,
            path_in_bucket="examples", # requires the non-public access keys
            output_path=data_dir / "examples",
            overwrite=True
        )
