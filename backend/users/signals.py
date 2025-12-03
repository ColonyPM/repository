from allauth.socialaccount.signals import social_account_updated
from django.dispatch import receiver


@receiver(social_account_updated)
def sync_github_profile(sender, request, sociallogin, **kwargs):
    if sociallogin.account.provider != "github":
        return

    data = sociallogin.account.extra_data
    user = sociallogin.user

    changed = False

    bio = data.get("bio")
    if bio is not None and getattr(user, "bio", None) != bio:
        user.bio = bio
        changed = True

    location = data.get("location")
    if location is not None and getattr(user, "location", None) != location:
        user.location = location
        changed = True

    if changed:
        user.save()
