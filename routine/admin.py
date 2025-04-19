from django.contrib import admin
from .models import *

admin.site.register(Schedule)
admin.site.register(Routine)
admin.site.register(Week)
admin.site.register(Day)
admin.site.register(DailyFood)
admin.site.register(DailyExercises)
# Register your models here.
