from django.contrib.auth import authenticate, login


class AuthService:

    @staticmethod
    def login_user(request, username, password):

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user:

            login(request, user)

        return user