import datetime
from random import randint
import traceback
from django.db.models import Q,Sum
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.utils.crypto import get_random_string
import json

from accounts.services.email_services import EmailService


from ..decorators import auth_user
from ..models import User
from ..utilitie_functions import mask_email, validate_password


def login(request):
    print(request.session)
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
        otp = request.POST.get('otp')

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
        
        if not validate_password(password):
            context['msg'] = "Password must have at least 8 characters, an uppercase letter, a number, and a special character."
            return render(request, "auth/signup.html", context=context)

        if password != rpassword:
            context['msg'] = "Passwords do not match."
            return render(request, "auth/signup.html", context=context)
        
        session_data = request.session.get("email")
        if not session_data or email != session_data["email_id"] :
            context['msg'] = "Please verify the email first!"
            return render(request, "auth/signup.html", context=context)
        
        print(session_data)

        first_attempt_time =  datetime.datetime.strptime(session_data['created_at'], "%d/%m/%Y %H:%M:%S")
        if (datetime.datetime.now() - first_attempt_time).total_seconds() > 600:
            context['msg'] = "OTP Expired try again"
            return render(request, "auth/signup.html", context=context)
        
        if session_data['OTP'] != int(otp):
            context['msg'] = "Invalid OTP"
            return render(request, "auth/signup.html", context=context) 
        
        del request.session['email']   

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
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('password', '')
        confirm_password = request.POST.get('c_password', '')

        if not check_password(old_password, user.password):
            messages.error(request, f"Old Password Incorrect")
            return redirect('profile')

        if not validate_password(new_password):
            messages.error(request, f"Password must have at least 8 characters, an uppercase letter, a number, and a special character.")
            return redirect('profile')

        if new_password != confirm_password:
            messages.error(request, f"Confirm Password Should Match")
            return redirect('profile')

        user.password = make_password(new_password)
        user.save()
        messages.info(request, f"Password Updated Succesfully !!!")
        return redirect('profile')
    except:
        traceback.print_exc()
        return redirect('error_505')
    

def send_otp(request):
    email_service = EmailService()
    if request.method == "POST":

        data = json.loads(request.body)
        otp = randint(100000, 999999)

        if User.objects.filter(email=data["email"]).exists():
            return JsonResponse({"status": "error", "message": "Email Already in Use"})
        
        session_data = request.session.get("email")
        current_time = datetime.datetime.now()
        attempt_count = 0
        if session_data and session_data['email_id'] == data['email']:
            attempt_count = session_data.get('attempt', 0)
            first_attempt_time = datetime.datetime.strptime(session_data['created_at'], "%d/%m/%Y %H:%M:%S")

            # If 30 minutes have passed, reset the attempt counter
            if (current_time - first_attempt_time).total_seconds() > 1800:
                attempt_count = 0  

            remain = round((1800 - (current_time - first_attempt_time).total_seconds())//60)

            # If user exceeds 3 attempts within 30 minutes, block them
            if attempt_count >= 3:
                return JsonResponse({"status": "error", "message": f"Resend Limit Exhausted. Try again after {remain} minutes."})

        request.session["email"] = {
            "email_id": data['email'],
            "OTP": otp,
            "created_at": current_time.strftime("%d/%m/%Y %H:%M:%S"),
            "attempt": attempt_count + 1
        } 

        email_sent = email_service.send_email(
            subject="OTP Verification code",
            recipient_list=[data["email"], settings.ADMIN_EMAIL],
            template_name="email_templates/otp_verification.html",
            context={"otp": otp},
            is_html=True,
            )

        if not email_sent:
            return JsonResponse({"status": "error", "message": "Invalid Email"})
        
        return JsonResponse({"status": "Success"}) 

    return JsonResponse({"status": "error", "message": "Invalid request"})