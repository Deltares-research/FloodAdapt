from pathlib import Path
from minio import Minio
import os

def download_database(output_path: Path, overwrite: bool = False) -> None:
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    if MINIO_ACCESS_KEY is None or MINIO_SECRET_KEY is None:
        raise ValueError(
            "Set the environment variables `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` before running this script."
        )

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output path {output_path} already exists. Use `overwrite=True` to overwrite."
        )

    bucket_name="flood-adapt"

    client = Minio(
        endpoint="s3.deltares.nl",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        region="eu-west-1",
    )

    if not client.bucket_exists(bucket_name):
        raise ValueError(
            f"Bucket {bucket_name} does not exist. Please create it first."
        )

    prefix_in_bucket = "examples/charleston_test"

    objs = client.list_objects(
        bucket_name=bucket_name,
        prefix=prefix_in_bucket,
        recursive=True,
    )
    for obj in objs:
        rel_path = Path(obj.object_name).relative_to(prefix_in_bucket)
        client.fget_object(
            bucket_name=bucket_name,
            object_name=obj.object_name,
            file_path=str(output_path / rel_path),
        )
        print(
            f"Downloaded {rel_path} to {output_path / rel_path}"
        )


if __name__ == "__main__":
    db_path = Path(__file__).parent / "_database" / "charleston_test"
    download_database(db_path)
