# -*- coding: utf-8 -*-
"""
Created on Saturday, 12th November 2022 1:06:43 pm
===============================================================================
@filename:  s3.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   functionality for interacting with S3.
===============================================================================
"""
import logging
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class S3Storage:
    """
    This class is a wrapper for the S3 boto3 client.
    """

    region: str = "us-east-2"
    bucket_name: str = "cloudtile-files"

    def __post_init__(self) -> None:
        self.s3_client = self._get_client()

    def create_bucket(self) -> None:
        """
        Attempts to create the bucket, if the bucket already exists it shows
        a warning.
        """
        try:
            s3_client = self.s3_client
            location = {"LocationConstraint": self.region}
            s3_client.create_bucket(
                Bucket=self.bucket_name, CreateBucketConfiguration=location
            )
        except ClientError as e:
            ecode = e.response["Error"]["Code"]
            if ecode == "BucketAlreadyOwnedByYou":
                logger.warning(e)
            else:
                logger.error(e)
                raise e from e

    def upload_file(self, file_path: str) -> None:
        """
        Upload a file in the local machine to the cloudtile-files/raw path in
        S3. If the bucket doesn't exist, you should create it first. We first
        check if the file has already been uploaded. This check happens by
        checking for a file of the same name and the same checksum. If both
        name and checksum match, the file upload is skipped. Otherwise the
        file is uploaded.

        Args:
            file_path (str): Either the absolute or relative path to the file.
        """
        fpath = self._resolve_path(file_path=file_path)
        checksum = self._md5_checksum(file_path=fpath)
        s3_client = self.s3_client

        if not self._check_file_equality(file_path=fpath, checksum=checksum):
            try:
                s3_client.upload_file(
                    str(fpath),
                    self.bucket_name,
                    self._make_rawpath(fpath),
                    ExtraArgs={"Metadata": {"md5": checksum}},
                )
            except ClientError as e:
                logger.error(e)

    def _check_file_equality(self, file_path: Path, checksum: str) -> bool:
        """
        Check if a local file matches the checksum of a file in the raw
        subpath of the remote bucket.

        Args:
            file_path (Path): The path to the local file.
            checksum (str): The checksum generated from the local file.

        Raises:
            e: Some ClientError instance.

        Returns:
            bool: Whether the file exists or not.
        """
        s3_client = self.s3_client
        try:
            response = s3_client.head_object(
                Bucket=self.bucket_name,
                Key=self._make_rawpath(file_path=file_path),
            )
            remote_md5 = response["ResponseMetadata"]["HTTPHeaders"][
                "x-amz-meta-md5"
            ]
            if remote_md5 == checksum:
                logger.warning("File %s found in S3 already", file_path.name)
                return True
            return False

        except ClientError as e:
            logger.error(e)
            raise e from e

    def _get_client(self) -> Any:
        """
        Instantiates a s3 client

        Returns:
            Any: A boto3.client('s3') instance.
        """
        return boto3.client("s3", region_name=self.region)

    @staticmethod
    def _make_rawpath(file_path: Path) -> str:
        """
        Helper method to create raw subpath keys for files.

        Args:
            file_path (Path): The file to generate the key for.

        Returns:
            str: The bucket key.
        """
        return "/".join(("raw", file_path.name))

    @staticmethod
    def _md5_checksum(file_path: Path) -> str:
        """
        Reads a local file as bytes using a stream and calculates its md5
        checksum.

        Args:
            file_path (Path): The file to read.

        Returns:
            str: The file's md5 checksum.
        """
        m = md5()
        with open(file=file_path, mode="rb") as f:
            for data in iter(lambda: f.read(1024 * 1024), b""):
                m.update(data)
        return m.hexdigest()

    @staticmethod
    def _resolve_path(file_path: str) -> Path:
        """
        Helper method to resolve file paths from a string.

        Args:
            file_path (str): The local file to fetch.

        Raises:
            FileNotFoundError: If the file does not exist or is not found.

        Returns:
            Path: Path representation of the file passed.
        """
        fpath: Path = Path(file_path).resolve().absolute()
        if not fpath.exists():
            error_msg = f"The file {fpath} does not exist"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        return fpath
