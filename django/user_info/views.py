from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


def signin(request):
    if request.user.is_authenticated:
        return redirect("search")  # Redirect to search page if already logged in
    if request.method == "POST":
        username = request.POST.get("user_name")
        password = request.POST.get("password")

        print(f"Attempting to authenticate user: {username} with password: {password}")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            print("User authenticated successfully!")
            return redirect("search")  # Redirect to search page after login
        else:
            print("Authentication failed: Invalid credentials")
            return render(
                request, "signin.html", {"error": "Invalid username or password."}
            )

    return render(request, "signin.html")


def home(request):
    if request.user.is_authenticated:
        return redirect("search")  # Redirect to search page if already logged in
    return render(request, "signin.html")  # Render the signin page


def logout_view(request):
    logout(request)
    return redirect("home")  # Redirect to home page after logout


def register(request):
    if request.user.is_authenticated:
        return redirect("search")  # Redirect to search page if already logged in

    if request.method == "POST":
        username = request.POST.get("user_name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Username already exists."})

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return render(request, "signup.html", {"error": "Email already exists."})

        # Create new user
        user = User.objects.create_user(
            username=username, email=email, password=password
        )

        # Redirect to signin page with success message
        return render(
            request,
            "signin.html",
            {"success": "Account created successfully! Please sign in."},
        )

    return render(request, "signup.html")  # Render the signup page


@login_required
def search(request):
    show_results = False

    if request.method == "POST":
        # Get the search query
        query = request.POST.get("search")

        # If any query is submitted, show the gold price content
        if query:
            show_results = True

    return render(
        request, "search.html", {"show_results": show_results}
    )  # Render the search page with context


def forgot_password_view(request):
    return render(request, "forgot.html")  # Render the forgot password page
