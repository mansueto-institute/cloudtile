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
from dataclasses import dataclass
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
        cpu (Optional[int], optional): The number of vCPU to be overriden. The
            number is limited by the CDK's definition of the Fargate task. The
            passed number is multiplied by 1024. Meaning, if you pass cpu=4,
            then this means cpu=4096, which is how AWS counts vCPU units.
            Defaults to None.
        memory (Optional[int], optional): The upper bound memory limit
            (in MiB) that will override the default of 16GB, which is set in
            via the CDK code. Defaults to None.
    """

    cli_args: list[str]
    cpu: Optional[int] = None
    memory: Optional[int] = None

    def __post_init__(self):
        self.ecs = boto3.client("ecs", region_name="us-east-2")
        self.ec2 = boto3.client("ec2", region_name="us-east-2")

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
                    "memoryReservation": 4096,
                }
            ]
        }

        if self.cpu is not None:
            if isinstance(self.cpu, int):
                overrides["containerOverrides"][0]["cpu"] = self.cpu * 1024
            else:
                raise TypeError("cpu must be an integer")
        else:
            overrides["containerOverrides"][0]["cpu"] = 2048
        if self.memory is not None:
            if isinstance(self.memory, int):
                overrides["containerOverrides"][0]["memory"] = self.memory
            else:
                raise TypeError("memory must be an integer")

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
