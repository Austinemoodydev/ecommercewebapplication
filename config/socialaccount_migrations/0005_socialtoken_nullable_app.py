from importlib import import_module

Migration = import_module("allauth.socialaccount.migrations.0005_socialtoken_nullable_app").Migration
