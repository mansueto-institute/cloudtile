# -*- coding: utf-8 -*-
"""
Created on 2022-12-13 10:18:47-05:00
===============================================================================
@filename:  test_ecs.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Test the ECS module.
===============================================================================
"""
# pylint: disable=missing-function-docstring,redefined-outer-name
# pylint: disable=protected-access

from unittest.mock import MagicMock, patch

import pytest

from cloudtile.ecs import ECSTask


@pytest.fixture(scope="function")
@patch("cloudtile.ecs.boto3")
def ecstask(mock_boto: MagicMock) -> ECSTask:
    ecstask = ECSTask(cli_args=[""])
    ecstask.ecs = mock_boto.client("ecs")
    ecstask.ec2 = mock_boto.client("ec2")
    return ecstask


def test_instantiation() -> None:
    assert ECSTask(cli_args=[""])


class TestAttributes:
    """
    Tests the attributes of the ECSTask class.
    """

    @staticmethod
    def test_memory_default(ecstask: ECSTask) -> None:
        assert ecstask.memory is None

    @staticmethod
    def test_memory_set(ecstask: ECSTask) -> None:
        ecstask.memory = 40960
        assert ecstask.memory == 40960

    @staticmethod
    def test_memory_bad_type(ecstask: ECSTask) -> None:
        with pytest.raises(TypeError):
            ecstask.memory = "1"

    @staticmethod
    def test_memory_bad_value(ecstask: ECSTask) -> None:
        with pytest.raises(ValueError):
            ecstask.memory = 0

    @staticmethod
    def test_memory_bad_value_range(ecstask: ECSTask) -> None:
        with pytest.raises(ValueError):
            ecstask.memory = 1000000

    @staticmethod
    def test_memory_bad_value_multiple(ecstask: ECSTask) -> None:
        with pytest.raises(ValueError):
            ecstask.memory = 55000

    @staticmethod
    def test_storage_set(ecstask: ECSTask) -> None:
        ecstask.storage = 100
        assert ecstask.storage == 100

    @staticmethod
    def test_storage_bad_type(ecstask: ECSTask) -> None:
        with pytest.raises(TypeError):
            ecstask.storage = "100"

    @staticmethod
    def test_storage_bad_value_range(ecstask: ECSTask) -> None:
        with pytest.raises(ValueError):
            ecstask.storage = 250


@patch.object(ECSTask, "_get_default_subnets", return_value=["subnet-1234"])
@patch.object(ECSTask, "_get_default_security_group", return_value=["sg-1234"])
def test_run(
    mock_sec_group: MagicMock,
    mock_subnets: MagicMock,
    ecstask: ECSTask,
) -> None:
    ecstask.run()
    mock_subnets.assert_called_once()
    mock_sec_group.assert_called_once()
    ecstask.ecs.run_task.assert_called_once_with(
        cluster="cloudtile",
        taskDefinition="cloudtile",
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": ["subnet-1234"],
                "securityGroups": [["sg-1234"]],
                "assignPublicIp": "ENABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": "cloudtile",
                    "command": [""],
                    "memoryReservation": 65536,
                }
            ]
        },
    )


@patch.object(ECSTask, "_get_default_subnets", return_value=["subnet-1234"])
@patch.object(ECSTask, "_get_default_security_group", return_value=["sg-1234"])
def test_run_w_memory(
    mock_sec_group: MagicMock,
    mock_subnets: MagicMock,
    ecstask: ECSTask,
) -> None:
    ecstask.memory = 49152
    ecstask.run()
    mock_subnets.assert_called_once()
    mock_sec_group.assert_called_once()
    call_args = ecstask.ecs.run_task.call_args[1]
    assert 49152 == call_args["overrides"]["containerOverrides"][0]["memory"]


@patch.object(ECSTask, "_get_default_subnets", return_value=["subnet-1234"])
@patch.object(ECSTask, "_get_default_security_group", return_value=["sg-1234"])
def test_run_w_storage(
    mock_sec_group: MagicMock,
    mock_subnets: MagicMock,
    ecstask: ECSTask,
) -> None:
    ecstask.storage = 50
    ecstask.run()
    mock_subnets.assert_called_once()
    mock_sec_group.assert_called_once()
    call_args = ecstask.ecs.run_task.call_args[1]
    assert 50 == call_args["overrides"]["ephemeralStorage"]["sizeInGiB"]


def test_get_fault_vpc_id(ecstask: ECSTask) -> None:
    ecstask.ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-1234"}]}
    assert ecstask._get_default_vpc_id() == "vpc-1234"
    ecstask.ec2.describe_vpcs.assert_called_once_with(
        Filters=[{"Name": "is-default", "Values": ["true"]}]
    )


def test_get_fault_vpc_id_bad_lookup(ecstask: ECSTask) -> None:
    ecstask.ec2.describe_vpcs.return_value = {"Vpcs": []}
    with pytest.raises(LookupError):
        ecstask._get_default_vpc_id()


@patch.object(ECSTask, "_get_default_vpc_id", return_value="vpc-1234")
def test_get_default_subnets(
    mock_default_vpc_id: MagicMock, ecstask: ECSTask
) -> None:
    ecstask.ec2.describe_subnets.return_value = {
        "Subnets": [{"SubnetId": "subnet-1234"}]
    }
    assert ecstask._get_default_subnets() == ["subnet-1234"]
    mock_default_vpc_id.assert_called_once()


@patch.object(ECSTask, "_get_default_vpc_id", return_value="vpc-1234")
def test_get_default_subnets_bad_lookup(_, ecstask: ECSTask) -> None:
    ecstask.ec2.describe_subnets.return_value = {"Subnets": []}
    with pytest.raises(LookupError):
        ecstask._get_default_subnets()


@patch.object(ECSTask, "_get_default_vpc_id", return_value="vpc-1234")
def test_get_default_security_group(
    mock_default_vpc_id: MagicMock, ecstask: ECSTask
) -> None:
    ecstask.ec2.describe_security_groups.return_value = {
        "SecurityGroups": [{"GroupId": "sg-1234"}]
    }
    assert ecstask._get_default_security_group() == "sg-1234"
    mock_default_vpc_id.assert_called_once()


@patch.object(ECSTask, "_get_default_vpc_id", return_value="vpc-1234")
def test_get_default_security_group_bad_lookup(
    mock_default_vpc_id: MagicMock, ecstask: ECSTask
) -> None:
    ecstask.ec2.describe_security_groups.return_value = {"SecurityGroups": []}
    with pytest.raises(LookupError):
        ecstask._get_default_security_group()
        mock_default_vpc_id.assert_called_once()


def test_parse_cli_args(ecstask: ECSTask) -> None:
    assert ecstask._parse_cli_args(
        ["test", "test", "--tc-kwargs one=one =two=two three"]
    ) == [
        "test",
        "test",
        "--tc-kwargs",
        "one=one",
        "=two=two",
        "three",
    ]
