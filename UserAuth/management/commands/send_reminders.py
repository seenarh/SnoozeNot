from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail

class Command(BaseCommand):
    help = "Send reminders for tasks"

    def handle(self, *args, **kwargs):
        # import inside handle to avoid import-time issues
        from UserAuth.models import Task  

        now = timezone.now()

        tasks = Task.objects.filter(
            reminder_time__lte=now,
            completed=False,
            reminder_time__isnull=False
        )

        for task in tasks:
            send_mail(
                subject=f"Reminder: {task.title}",
                message=f"Hey, don't forget:\n\n{task.details}",
                from_email="noreply@snoozenot.com",
                recipient_list=[task.user.email],
            )

            # Clear reminder so it doesn’t send again
            task.reminder_time = None
            task.save()

        self.stdout.write(self.style.SUCCESS("Reminders sent"))
