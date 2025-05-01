from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from utils.models import ModelWithTimeStamp


class CustomUser(AbstractUser, ModelWithTimeStamp):

    phone = models.CharField(verbose_name=_("phone"), max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to="profile_image/", blank=True, null=True) 
    user_permissions=models.ManyToManyField( "auth.Permission",verbose_name=_("user permissions"),blank=True, help_text=_("Specific permissions for this user."),related_name="customuser_permissions",related_query_name="customuser",)
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="customuser_groups",  
        related_query_name="customuser",
    )
    
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


