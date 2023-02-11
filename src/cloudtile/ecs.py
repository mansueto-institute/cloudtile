# -*- coding: utf-8 -*-
"""
Created on Wednesday, 31st December 1969 7:00:00 pm
===============================================================================
@filename:  ecs.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   Execute a CLI task on ECS.
===============================================================================
"""
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import boto3


@dataclass(eq=False)
class ECSTask:
    """
    This is a class that represents an ECS task, which maps to a CLI command.

    Raises:
        TypeError: If the cpu value is not an integer.
        TypeError: If the memory value is not an integer.
        LookupError: If the default VPC id cannot be found.
        LookupError: If the default subnets cannot be found.
        LookupError: If the default security group cannot be found.

    Args:
        cli_args (list[str]): The CLI arguments which are passed to the ECS
            container.
        memory (Optional[int], optional): The upper bound memory limit
            (in MiB) that will override the default of 16GB, which is set in
            via the CDK code. Defaults to None.
    """

    cli_args: list[str]
    memory: Optional[int] = None
    storage: Optional[int] = None
    _memory: Optional[int] = field(init=False, repr=False, default=None)
    _storage: Optional[int] = field(init=False, repr=False, default=None)

    def __post_init__(self):
        self.ecs = boto3.client("ecs", region_name="us-east-2")
        self.ec2 = boto3.client("ec2", region_name="us-east-2")

    @property  # type: ignore
    def memory(self) -> Optional[int]:
        """
        Gets the memory value.

        Returns:
            Optional[int]: The memory value.
        """
        return self._memory

    @memory.setter
    def memory(self, value: Optional[int]) -> None:
        """
        Sets the memory value.

        Args:
            value (Optional[int]): The memory value.
        """
        if isinstance(value, property):
            value = ECSTask._memory
        if not isinstance(value, int) and value is not None:
            raise TypeError(f"memory must be an integer, not {type(value)}")
        if isinstance(value, int):
            if value < 32768 or value > 122880:
                raise ValueError("memory must be between 32768 and 122880")
            if value % 8192 != 0:
                raise ValueError("memory must be a multiple of 8192")
        self._memory = value

    @property  # type: ignore
    def storage(self) -> Optional[int]:
        """Gets the ephemeral storage override value.

        Returns:
            int: The ephemeral storage override value.
        """
        return self._storage

    @storage.setter
    def storage(self, value: Optional[int]) -> None:
        """Sets the override ephemeral storage value in GB.

        Args:
            value (int, optional): The override ephemeral storage value
        """
        if isinstance(value, property):
            value = ECSTask._storage
        if not isinstance(value, int) and value is not None:
            raise TypeError(f"storage must be an integer, not {type(value)}")
        if isinstance(value, int):
            if not 20 <= value <= 200:
                raise ValueError(
                    "The storage value must be 20 <= value <= 200"
                )
        self._storage = value

    def run(self) -> dict:
        """
        Driver method to run the ECS task instance.

        Raises:
            TypeError: If the cpu value is not an integer.
            TypeError: If the memory value is not an integer.

        Returns:
            dict: The response from the ECS API.
        """
        overrides: dict = {
            "containerOverrides": [
                {
                    "name": "cloudtile",
                    "command": self.cli_args,
                    "memoryReservation": 65536,
                }
            ]
        }

        if self.memory is not None:
            overrides["containerOverrides"][0]["memory"] = self.memory
        if self.storage is not None:
            overrides["ephemeralStorage"] = {"sizeInGiB": self.storage}

        response = self.ecs.run_task(
            cluster="cloudtile",
            taskDefinition="cloudtile",
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": self._get_default_subnets(),
                    "securityGroups": [self._get_default_security_group()],
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides=overrides,
        )
        return response

    @lru_cache
    def _get_default_vpc_id(self) -> str:
        response: dict = self.ec2.describe_vpcs(
            Filters=[{"Name": "is-default", "Values": ["true"]}]
        )

        if len(response["Vpcs"]) == 0:
            raise LookupError("default vpc not found")

        return response["Vpcs"][0]["VpcId"]

    @lru_cache
    def _get_default_subnets(self) -> list[str]:
        response: dict = self.ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [self._get_default_vpc_id()]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )

        if len(response["Subnets"]) == 0:
            raise LookupError("default subnets not found")

        result = [subnet["SubnetId"] for subnet in response["Subnets"]]
        return result

    @lru_cache
    def _get_default_security_group(self) -> str:
        response: dict = self.ec2.describe_security_groups(
            Filters=[
                {"Name": "vpc-id", "Values": [self._get_default_vpc_id()]},
                {
                    "Name": "description",
                    "Values": ["default VPC security group"],
                },
            ]
        )

        if len(response["SecurityGroups"]) == 0:
            raise LookupError("default security group not found")

        return response["SecurityGroups"][0]["GroupId"]
