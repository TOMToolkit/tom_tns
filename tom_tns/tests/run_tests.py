#!/usr/bin/env python
# django_shell.py
import sys

from django.core.management import call_command
from boot_django import boot_django, APP_NAME  # noqa


boot_django()
print(f'running test for {APP_NAME}')
call_command('test', *sys.argv[1:], '--exclude-tag=canary', verbosity=2)
