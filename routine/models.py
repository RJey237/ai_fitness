from django.db import models
from parler.models import TranslatableModel,TranslatedFields


class Schedule(models.Model):
    user = models.ForeignKey("user.CustomUser",on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()



class Routine(TranslatableModel):
    user = models.ForeignKey("user.CustomUser",on_delete=models.CASCADE)
    translations = TranslatedFields(
        description = models.TextField()
    )
    start_date = models.DateField(auto_now_add=True)


class Week(models.Model):
    routine = models.ForeignKey(Routine,on_delete=models.CASCADE)
    week_number = models.IntegerField(default=1)


class Day(models.Model):
    week = models.ForeignKey(Week,on_delete=models.CASCADE)
    week_day = models.IntegerField(default=1)
    week_date = models.DateField()
    status = models.BooleanField()


class DailyFood(TranslatableModel):
    day = models.ForeignKey(Day,on_delete=models.CASCADE)
    callory = models.FloatField()
    translations = TranslatedFields(
        description = models.TextField()
    )

class DailyExercises(TranslatableModel):
    day = models.ForeignKey(Day,on_delete=models.CASCADE)
    translations = TranslatedFields(
        name = models.TextField(),
        description = models.TextField()
    )
    duration = models.IntegerField()
    sets = models.IntegerField()
    reps = models.IntegerField()
