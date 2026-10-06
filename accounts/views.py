from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, resolve_url
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, RegistrationForm


class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("tracker:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            f"Welcome, {self.object.username}! Start by creating your first category.",
        )
        return response


class LoginView(auth_views.LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """Log out on POST only.

    A GET (for example a typed or bookmarked /accounts/logout/ URL) shows a
    confirmation page instead of logging out, so a link on another site can't
    sign the user out.
    """

    http_method_names = ["get", "post", "options"]
    template_name = "accounts/logout_confirm.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(resolve_url(settings.LOGIN_URL))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have been logged out.")
        return response
