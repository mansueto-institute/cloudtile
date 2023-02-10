# -*- coding: utf-8 -*-
"""
Created on Wednesday, 31st December 1969 6:00:00 pm
===============================================================================
@filename:  cloudtile_stack.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   This module defines the cloudtile AWS infrastructure.
===============================================================================
"""
from pathlib import Path

import aws_cdk as cdk
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_ec2 as ec2
from aws_cdk import Stack
from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct


class CloudtileStack(Stack):
    """
    This class describes the AWS infra stack.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(
            self,
            id="cloudtile-bucket",
            bucket_name="cloudtile-files",
            versioned=False,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        image = DockerImageAsset(
            self,
            id="cloudtile",
            directory=str(Path(__file__).parents[3]),
        )

        vpc = ec2.Vpc.from_lookup(self, "VPC", is_default=True)

        cluster = ecs.Cluster(
            self, id="cloudtile-cluster", cluster_name="cloudtile", vpc=vpc
        )
        cluster.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        task = ecs.FargateTaskDefinition(
            self,
            id="cloudtile-ecs-task",
            cpu=16384,
            memory_limit_mib=122880,
            ephemeral_storage_gib=100,
            family="cloudtile",
        )
        bucket.grant_read_write(task.task_role)
        task.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

        task.add_container(
            id="cloudtile",
            container_name="cloudtile",
            image=ecs.ContainerImage.from_docker_image_asset(image),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="cloudtile"),
        )
