"""
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

import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

logger = logging.getLogger("fetch-data")


def download_directory(client: Minio, path_in_bucket: str, output_path: Path, overwrite: bool = False, bucket_name = "flood-adapt") -> None:
    """Download a directory from a MinIO bucket to a local directory."""
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Output path {output_path} already exists. Use `overwrite=True` to overwrite."
        )
    objs = list(
        client.list_objects(
            bucket_name=bucket_name,
            prefix=path_in_bucket,
            recursive=True,
        )
    )
    if len(objs) == 0:
        raise ValueError(f"No objects found in '{path_in_bucket}'. Please check the path and try again.")

    logger.info(f"Found {len(objs)} objects in '{path_in_bucket}'. Downloading to '{output_path}'...")
    for obj in objs:
        rel_path = Path(obj.object_name).relative_to(path_in_bucket)
        client.fget_object(
            bucket_name=bucket_name,
            object_name=obj.object_name,
            file_path=str(output_path / rel_path),
        )
        logger.debug(
            f"Downloaded '{rel_path}' to '{output_path / rel_path}'"
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

    parser = argparse.ArgumentParser(description="Download data from MinIO bucket.")
    parser.add_argument(
        "--path-in-bucket",
        type=str,
        required=True,
        nargs="+", # allow multiple paths to be specified
        help="Path(s) in the MinIO bucket to download. E.g. --path-in-bucket system public examples",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=data_dir,
        help="Directory to download the data to. Default is `docs/_data`.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in the output directory.",
    )
    parser.add_argument(
        "--secret-key",
        type=str,
        default=os.getenv("MINIO_SECRET_KEY"),
        help="MinIO secret key. Default is the value of the `MINIO_SECRET_KEY` environment variable.",
    )
    parser.add_argument(
        "--access-key",
        type=str,
        default=os.getenv("MINIO_ACCESS_KEY"),
        help="MinIO access key. Default is the value of the `MINIO_ACCESS_KEY` environment variable.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level. Default is INFO.",
        required=False
    )
    args = parser.parse_args()

    if not (args.access_key and args.secret_key):
        raise ValueError(
            "Please set the MINIO_ACCESS_KEY and MINIO_SECRET_KEY environment variables, "
            " or provide them as command line arguments. Refer to the __doc__ at the top "
            "of this file for more information."
        )

    logging.basicConfig(
        format="%(name)s - %(levelname)s - %(message)s",
        level=args.log_level
    )

    client = prepare_client(access_key=args.access_key, secret_key=args.secret_key)

    for path_in_bucket in args.path_in_bucket:
        download_directory(
            client=client,
            path_in_bucket=path_in_bucket.strip(),
            output_path=args.data_dir / path_in_bucket.strip(),
            overwrite=args.overwrite
        )
    logger.info(f"Download finished. Data downloaded to {args.data_dir}.")
