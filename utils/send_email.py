from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_fitness_plan_email(user_first_name, user_email, plan_type, login_url):
    subject = f"🎯 Your {plan_type.capitalize()} Fitness Plan is Ready!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [user_email]

    html_content = render_to_string("emails/fitness_plan.html", {
        "user_first_name": user_first_name,
        "plan_type": plan_type,
        "login_url": login_url,
    })

    msg = EmailMultiAlternatives(subject, "", from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()