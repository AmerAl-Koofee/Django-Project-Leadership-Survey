from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.models import User


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        email = request.POST.get("email")
        
        # Check for existing email if needed
        if email and User.objects.filter(email=email).exists():
            form.add_error(None, "Email is already in use.")
        elif form.is_valid():
            user = form.save(commit=False)
            user.email = email
            user.save()
            login(request, user)
            return redirect("survey:survey")
    else:
        form = UserCreationForm()

    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect("survey:survey")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("users:login")
