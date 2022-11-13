# -*- coding: utf-8 -*-
"""
Created on Saturday, 12th November 2022 3:14:04 pm
===============================================================================
@filename:  test_s3.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Unit tests for the s3 module.
===============================================================================
"""
# pylint: disable=missing-function-docstring,redefined-outer-name
# pylint: disable=protected-access

import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_s3

from cloudtile.s3 import S3Storage


@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-2"


@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client("s3")


@mock_s3
@pytest.fixture(scope="function")
def mock_storage(s3) -> Generator[S3Storage, None, None]:
    s3store = S3Storage()
    s3.s3_client = s3
    yield s3store


@mock_s3
class TestInstantiation:
    """
    Tests the S3Storage's instantiation.
    """

    @staticmethod
    def test_s3_storage():
        s3 = S3Storage()
        assert s3


class TestMethods:
    """
    Test S3Storage's methods.
    """

    @staticmethod
    @mock_s3
    def test_create_bucket(mock_storage: S3Storage):
        mock_storage.create_bucket()
        s3 = boto3.resource("s3")
        assert s3.Bucket("cloudtile-files") in s3.buckets.all()
        mock_storage.create_bucket()  # this checks for idempotency
        assert s3.Bucket("cloudtile-files") in s3.buckets.all()

    @staticmethod
    def test_create_bucket_exists(mock_storage: S3Storage):
        mock_storage.s3_client.create_bucket = MagicMock(
            side_effect=ClientError(
                error_response={"Error": {"Code": "SomethingElse"}},
                operation_name="test",
            )
        )
        with pytest.raises(ClientError):
            mock_storage.create_bucket()

    @staticmethod
    def test_upload_file(mock_storage: S3Storage):
        mock_storage.create_bucket()
        mock_storage.upload_file("LICENSE")
        s3 = mock_storage.s3_client
        obj = s3.get_object(Bucket="cloudtile-files", Key="raw/LICENSE")
        assert "GNU" in obj["Body"].read().decode("utf-8")

    @staticmethod
    @patch.object(
        S3Storage, "_check_file_equality", MagicMock(return_value=True)
    )
    def test_upload_file_exists(mock_storage: S3Storage):
        mock_storage.create_bucket()
        mock_storage.upload_file("LICENSE")

    @staticmethod
    @patch.object(
        S3Storage, "_check_file_equality", MagicMock(return_value=False)
    )
    def test_upload_file_other_error(mock_storage: S3Storage):
        mock_storage.s3_client.upload_file = MagicMock(
            side_effect=ClientError(
                error_response={"Error": {"Code": "SomethingElse"}},
                operation_name="test",
            )
        )
        with pytest.raises(ClientError):
            mock_storage.upload_file("LICENSE")

    @staticmethod
    def test_check_file_eq(mock_storage: S3Storage):
        mock_storage.create_bucket()
        mock_storage.upload_file("LICENSE")
        checksum = "1ebbd3e34237af26da5dc08a4e440464"
        assert mock_storage._check_file_equality(
            Path("LICENSE"), checksum=checksum
        )

    @staticmethod
    def test_check_file_not_eq(mock_storage: S3Storage):
        mock_storage.create_bucket()
        mock_storage.upload_file("LICENSE")
        checksum = "e62637ea8a114355b985fd86c9f3bd6e"
        assert not mock_storage._check_file_equality(
            Path("LICENSE"), checksum=checksum
        )

    @staticmethod
    def test_check_file_eq_404(mock_storage: S3Storage):
        mock_storage.create_bucket()
        assert not mock_storage._check_file_equality(
            Path("LICENSE"), checksum="123"
        )

    @staticmethod
    def test_check_file_eq_other_error(mock_storage: S3Storage):
        mock_storage.s3_client.head_object = MagicMock(
            side_effect=ClientError(
                error_response={"Error": {"Code": "SomethingElse"}},
                operation_name="test",
            )
        )
        with pytest.raises(ClientError):
            mock_storage._check_file_equality(Path("LICENSE"), "123")

    @staticmethod
    def test_make_rawpath(mock_storage: S3Storage):
        path = Path("LICENSE")
        expected = "raw/LICENSE"
        assert mock_storage._make_rawpath(path) == expected

    @staticmethod
    def test_md5_checksum(mock_storage: S3Storage):
        path = Path("LICENSE")
        checksum = mock_storage._md5_checksum(path)
        assert checksum == "1ebbd3e34237af26da5dc08a4e440464"

    @staticmethod
    def test_resolve_path(mock_storage: S3Storage):
        path = mock_storage._resolve_path("LICENSE")
        assert path.exists()

    @staticmethod
    def test_resolve_path_no_exist(mock_storage: S3Storage):
        with pytest.raises(FileNotFoundError):
            mock_storage._resolve_path("IdontExist")
