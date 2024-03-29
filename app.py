# -*- coding: utf-8 -*-
"""
Created on Wednesday, 31st December 1969 6:00:00 pm
===============================================================================
@filename:  app.py
@author:    Manuel Martinez (manmart@uchicago.edu)
@project:   cloudtile
@purpose:   The app for CDK
===============================================================================
"""
import os
import aws_cdk as cdk

from cloudtile.cdk.cloudtile_stack import CloudtileStack


app = cdk.App()
CloudtileStack(
    app,
    "CloudtileStack",
    env=cdk.Environment(
        account="921974715484",
        region="us-east-2"
    ),
)

app.synth()
