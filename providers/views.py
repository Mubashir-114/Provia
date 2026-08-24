from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import User

from .forms import ProviderProfileForm
from .models import ProviderProfile


@login_required
@role_required(User.Role.PROVIDER)
def profile_view(request):
    profile = ProviderProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = ProviderProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():
            provider_profile = form.save(commit=False)
            provider_profile.user = request.user
            provider_profile.save()

            messages.success(
                request,
                "Your provider profile has been saved successfully.",
            )

            return redirect("providers:profile")

    else:
        form = ProviderProfileForm(
            instance=profile,
        )

    return render(
        request,
        "providers/profile.html",
        {
            "form": form,
            "profile": profile,
        },
    )
