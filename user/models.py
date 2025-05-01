from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from utils.models import ModelWithTimeStamp


class CustomUser(AbstractUser, ModelWithTimeStamp):

    phone = models.CharField(verbose_name=_("phone"), max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to="profile image")
    is_verified = models.BooleanField(default=False)
    
    @property
    def verify_email(self):
        self.email_verified = True
        self.save()

class Bmi(models.Model):
    class Gender(models.TextChoices):
        MAN = 'man', 'male'
        WOMAN = 'woman', 'female'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    age = models.IntegerField(default=0)
    height = models.FloatField(default=0)
    weight = models.FloatField(default=0)
    gender = models.CharField(max_length=6, choices=Gender.choices, default=Gender.MAN)  

    def __str__(self):
        return f"{self.user.username}'s Profile"
