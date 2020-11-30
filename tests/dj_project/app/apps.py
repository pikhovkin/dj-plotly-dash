# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig

# Initialise views for registering in dash.dash.BaseDashView._dashes
from .views import *


class App(AppConfig):
    name = 'app'
