from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from utils.models import ModelWithTimeStamp


class CustomUser(AbstractUser, ModelWithTimeStamp):

    phone = models.CharField(verbose_name=_("phone"), max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to="profile image", blank=True, null=True)

    @property
    def verify_email(self):
        self.email_verified = True
        self.save()

class Bmi(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    age = models.IntegerField(default=0)
    height = models.FloatField(default=0)
    weight = models.FloatField(default=0)

