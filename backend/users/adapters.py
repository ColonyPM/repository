from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter, user_field


class DisableSignupAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False


class GitHubSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        try:
            picture = sociallogin.account.extra_data["avatar_url"]
            location = sociallogin.account.extra_data["location"]
            bio = sociallogin.account.extra_data["bio"]
            user_field(user, "avatar", picture)
            user_field(user, "location", location)
            user_field(user, "bio", bio)
        except (KeyError, AttributeError):
            pass
        return user

    def is_open_for_signup(self, request, sociallogin):
        return True
