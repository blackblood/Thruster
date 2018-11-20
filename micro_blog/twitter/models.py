# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.

class User(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

class Tweet(models.Model):
    body = models.CharField(max_length=140)
    user = models.ForeignKey(User, on_delete=models.CASCADE)