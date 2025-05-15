from django.db import models
from parler.models import TranslatableModel, TranslatedFields
from user.models import CustomUser  # Import CustomUser model


class Schedule(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.start_time}-{self.end_time}"



class Routine(TranslatableModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount_of_weeks = models.IntegerField(default=1)
    description = models.TextField(default="Descrpition is not provided")
    translations = TranslatedFields(
    )
    start_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.start_date}"


class Day(models.Model):
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name="days", null=True)
    week_number = models.IntegerField(default=1)
    week_day = models.IntegerField(default=1)
    week_date = models.DateField(default=1)
    status = models.BooleanField(default=False)

    class Meta:
        unique_together = ("routine", "week_number", "week_day")

    def __str__(self):
        return f"{self.week_date}"


class DailyFood(TranslatableModel):
    day = models.ForeignKey(Day, on_delete=models.CASCADE)
    description = models.TextField(default="Description is not provided")

    callory = models.FloatField()
    translations = TranslatedFields(
    )



class DailyExercises(TranslatableModel):
    day = models.ForeignKey(Day, on_delete=models.CASCADE)
    name = models.CharField(max_length=100,default="Exercise")    
    description = models.TextField(default="Descrpition is not provided")
    translations = TranslatedFields(
    )
    duration = models.IntegerField()
    sets = models.IntegerField()
    reps = models.IntegerField()
    status=models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.sets} sets - {self.reps}"