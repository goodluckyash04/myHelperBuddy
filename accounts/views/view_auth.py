import traceback
from django.db.models import Q,Sum
from django.shortcuts import render,redirect
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.utils.crypto import get_random_string

from ..decorators import auth_user
from ..models import User
from ..utilitie_functions import mask_email

def login(request):
    if 'username' in request.session:
        return redirect("dashboard")

    if request.method == "GET":
        msg = request.session.pop('forgot_password_msg', '')
        return render(request, "auth/login.html", {"msg": msg})

    if not User.objects.filter(username=request.POST['username'].lower()).exists():
        return render(request,"auth/login.html",{"msg":"user Does not exist"})


    user = User.objects.get(username=request.POST['username'].lower())

    if not check_password(request.POST['password'],user.password):
        return render(request,"auth/login.html",{"msg":"Invalid Credential"})

    request.session["username"] = user.username
    return redirect("dashboard")

def signup(request):
    if request.method == "GET":
        return render(request, "auth/signup.html")

    if request.method == "POST":
        username = request.POST.get('username', '').lower()
        password = request.POST.get('password', '')
        rpassword = request.POST.get('rpassword', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')

        context = {
            'username' :username,
            'name' :name,
            'email' :email
        }

        if not username or not password or not rpassword:
            context['msg'] = "All fields are required."
            return render(request, "auth/signup.html", context=context)

        if User.objects.filter(username=username).exists():
            context['msg'] = "Username already exists."
            return render(request, "auth/signup.html", context=context)
        
        if User.objects.filter(email=email).exists():
            context['msg'] = "Email already exists."
            return render(request, "auth/signup.html", context=context)

        if password != rpassword:
            context['msg'] = "Passwords do not match."
            return render(request, "auth/signup.html", context=context)

        try:
            User.objects.create(
                username=username,
                password=make_password(password),
                name=name,
                email=email,
            )
            return render(request, "auth/login.html", {"msg": "User Created. Login to Continue"})
        except Exception as e:
            traceback.print_exc()
            messages.error(request, str(e))
            # Log the error for debugging purposes
            return render(request, "auth/signup.html",{"msg":str(e)})

def logout(request):
    try:
        del request.session['username']
    except KeyError:
        pass  # 'username' key may not be present in the session

    return redirect('index')

def forgotPassword(request):
    if request.method == "GET":
        return render(request, "auth/forgotPassword.html")

    if request.method == "POST":
        try:
            username = request.POST.get("username", "").lower()
            user = User.objects.get(Q(username=username) | Q(email=username))

            new_password = get_random_string(8)
            sub = "Change in Account"
            message = f"Use This Password to Login to your account:\n{new_password}\n\n Do Not Share With anyone"
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]
            print(sub, message, from_email, recipient_list)
            send_mail(sub, message, from_email, recipient_list)

            user.password = make_password(new_password)
            user.save()

            masked_email = mask_email(user.email)
            msg = f"Password sent to {masked_email}"
            request.session['forgot_password_msg'] = msg

            return redirect('login')
        except User.DoesNotExist:
            return render(request, "auth/forgotPassword.html", {"msg": "User does not exist"})
        except:
            print(traceback.print_exc())
            # Handle other exceptions if necessary
            return render(request, "auth/forgotPassword.html", {"msg": "An error occurred. Please try again."})

    return render(request, "auth/forgotPassword.html")

@auth_user
def changePassword(request, user):
    try:
        if request.method == "GET":
            return render(request, "auth/changePassword.html", {"user": user})

        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('password', '')
        confirm_password = request.POST.get('c_password', '')

        if not check_password(old_password, user.password):
            return render(request, "auth/changePassword.html", {"user": user, "msg": "Old Password Incorrect"})

        if new_password != confirm_password:
            return render(request, "auth/changePassword.html", {"user": user, "msg": "Confirm Password Should Match"})

        user.password = make_password(new_password)
        user.save()
    except:
        traceback.print_exc()
        return redirect('error_505')
    