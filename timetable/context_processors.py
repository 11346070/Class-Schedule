from .models import StudentProfile


def avatar(request):
    if not request.user.is_authenticated:
        return {"avatar_url": ""}
    profile = StudentProfile.objects.filter(pk=str(request.user.pk)).only("avatar").first()
    if profile is None or not profile.avatar:
        return {"avatar_url": ""}
    return {"avatar_url": profile.avatar.url}
