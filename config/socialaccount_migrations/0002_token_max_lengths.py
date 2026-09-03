from importlib import import_module

Migration = import_module("allauth.socialaccount.migrations.0002_token_max_lengths").Migration
