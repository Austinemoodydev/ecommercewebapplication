from importlib import import_module

Migration = import_module("allauth.socialaccount.migrations.0001_initial").Migration
