from django.conf import settings
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.template import Context
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from subscribers.models import Subscriber


def sign_up(request):
    if request.method == 'POST':
        new_subscriber = False

        # App gmail not configured yet
        if settings.EMAIL_HOST_USER == 'YOUR_GMAIL_ADDRESS':
            flash_type = messages.WARNING
            flash_message = 'It looks like the host is not configured to send emails quite yet'
        else:
            proceed = True
            valid_email = True
            email = request.POST.get('email', '')

            # Already subscribed
            if Subscriber.objects.filter(email=email):
                subscriber = Subscriber.objects.get(email=email)
                if subscriber.subscribed:
                    proceed = False
                    flash_type = messages.SUCCESS
                    flash_message = 'Good news, it looks like you are already subscribed!'
            else:
                try:
                    # Create database record
                    subscriber = Subscriber(email=email)
                    subscriber._set_hash()
                    subscriber.save()
                    new_subscriber = True
                except:
                    valid_email = False

            if valid_email and proceed:
                try:
                    # Success!
                    _send_confirmation_email(request, subscriber)
                    flash_type = messages.SUCCESS
                    flash_message = "Thanks for subscribing! We've sent a confirmation email to %s." % email
                except:
                    valid_email = False
                    if new_subscriber:
                        subscriber.delete()

            # Bad email provided
            if not valid_email:
                flash_type = messages.WARNING
                flash_message = 'It looks like you submitted an invalid email address'
        messages.add_message(request, flash_type, flash_message)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def subscribe(request, hash_key):
    subscriber = Subscriber.objects.get(hash_key=hash_key)
    if subscriber and not subscriber.subscribed:
        subscriber.subscribed = True
        subscriber.save()
        _notify_admin_of_new_subscriber(subscriber.email)
        messages.add_message(
            request,
            messages.SUCCESS,
            'Thanks for confirming your subscription!'
        )
    return HttpResponseRedirect('/')

def unsubscribe(request, hash_key):
    subsciber = Subscriber.objects.get(hash_key=hash_key)
    if subsciber and subsciber.subscribed:
        subsciber.subscribed = False
        subsciber.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            'You have successfully unsubscribed. Thanks for using our service!'
        )
    return HttpResponseRedirect('/')

@login_required()
def notify_subscribers(request):
    call_command('notifysubscribers')
    return HttpResponseRedirect('/citations/')

def _send_confirmation_email(request, subscriber):
    url_base = request.build_absolute_uri('/')
    html = get_template('confirm_subscription_email.html')
    context = Context({
        'subscriber': subscriber,
        'url_base': url_base.rstrip('/'),
        'contact_email': settings.EMAIL_HOST_USER if settings.EMAIL_HOST_USER else False
    })
    body = html.render(context)
    subject = '[scotuswebcites] Subscriber confirmation'
    sender = settings.EMAIL_HOST_USER
    recipient = subscriber.email
    msg = EmailMultiAlternatives(subject, body, sender, [recipient])
    msg.attach_alternative(body, "text/html")
    msg.send()

def _notify_admin_of_new_subscriber(email_address):
    if settings.EMAIL_HOST_USER != 'YOUR_GMAIL_ADDRESS':
        subject = '[scotuswebcites] New Subscriber Registered'
        message = 'Congratulations!  You have a new follower: %s' % email_address
        send_mail(subject, message, settings.EMAIL_HOST_USER, [settings.CONTACT_EMAIL])
