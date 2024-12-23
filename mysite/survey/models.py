import random
import string
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.core.mail import send_mail


# Utility function for generating unique slugs
def generate_unique_slug(klass, field, id, identifier='slug'):
    """
    Generate a unique slug for the given model class.
    """
    origin_slug = slugify(field)
    unique_slug = origin_slug
    numb = 1
    mapping = {identifier: unique_slug}
    obj = klass.objects.filter(**mapping).first()
    while obj:
        if obj.id == id:
            break
        rnd_string = ''.join(random.choices(string.ascii_lowercase, k=5))
        unique_slug = f'{origin_slug}-{rnd_string}-{numb}'
        mapping[identifier] = unique_slug
        numb += 1
        obj = klass.objects.filter(**mapping).first()
    return unique_slug


# Base model with created_at and updated_at timestamps
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Survey(BaseModel):
    name = models.CharField(
        max_length=200,
        help_text="The title of the survey.")

    description = models.TextField(
        blank=True, 
        help_text="A brief description of the survey.")

    slug = models.SlugField(max_length=225, 
        unique=True,
        blank=True, 
        help_text="Unique identifier for the survey.")

    is_editable = models.BooleanField(
        default=True, 
        help_text="Can the survey be edited after creation?")

    allow_multiple_submissions = models.BooleanField(
        default=False, 
        help_text="Allow users to submit the survey multiple times.")

    published = models.BooleanField(
        default=False, 
        help_text="Is the survey published?")

    created_by = models.ForeignKey(
        get_user_model(), 
        on_delete=models.CASCADE, 
        related_name="surveys", 
        help_text="The user who created the survey.",
        default=1)
    
    recipient_emails = models.TextField(
        blank=True, 
        help_text="Comma-separated list of email addresses that are allowed to access this survey.")
    
    password = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional: Password to access the survey.")

    class Meta:
        verbose_name = "Survey"
        verbose_name_plural = "Surveys"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Survey, self.name, self.id)
        super().save(*args, **kwargs)

    

    def send_survey_emails(self):
        if not self.recipient_emails:
            return
        email_list = [email.strip() for email in self.recipient_emails.split(',')]
        survey_link = f"http://127.0.0.1:8000/survey/{self.slug}/"
        subject = f"Invitation to participate in the survey: {self.name}"
        message = f"You are invited to participate in the survey '{self.name}'.\n\nClick the link below to access the survey:\n{survey_link}"
        send_mail(subject, message, 'noreply@example.com', email_list)



class Question(BaseModel):
    FIELD_TYPES = [
        (1, "Radio"),
        (2, "Select"),
        (3, "Multi-Select"),
        (4, "Textarea"),
    ]

    survey = models.ForeignKey(
        Survey, 
        related_name="questions", 
        on_delete=models.CASCADE)
    
    label = models.CharField(max_length=500, 
        help_text="The question text.")
    
    field_type = models.PositiveSmallIntegerField(
        choices=FIELD_TYPES,
        help_text="The input type for the question.")
    
    options = models.TextField(
        blank=True,
        help_text="Options for 'Radio', 'Select', or 'Multi-Select', separated by commas.",)
    
    is_required = models.BooleanField(
        default=True, 
        help_text="Is this question mandatory?")
    
    order = models.PositiveIntegerField(
        default=0, 
        help_text="The order of the question in the survey.")
    
    dimension = models.CharField(
        max_length=200, 
        help_text="The dimension for analysis.", 
        blank=True)
    
    area = models.CharField(
        max_length=200, 
        help_text="The area/category for analysis.", 
        blank=True)

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ["order"]

    def __str__(self):
        return f"{self.label} (Survey: {self.survey.name})"
    
    @property
    def split_choices(self):
        if self.options:
            return [choice.strip() for choice in self.options.split(",")]
        return []


class UserAnswer(BaseModel):
    survey = models.ForeignKey(Survey, 
        on_delete=models.CASCADE)

    user = models.ForeignKey(get_user_model(),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text="The user who submitted this answer.")

    class Meta:
        verbose_name = "User Answer"
        verbose_name_plural = "User Answers"

    def __str__(self):
        return f"Answers for {self.survey.name}"


class Answer(BaseModel):
    question = models.ForeignKey(
        Question, 
        related_name="answers",
        on_delete=models.CASCADE)
    
    value = models.TextField(
        help_text="The value provided by the user for this question.")
    
    user_answer = models.ForeignKey(
        UserAnswer,
        on_delete=models.CASCADE,
        related_name="answers")

    class Meta:
        verbose_name = "Answer"
        verbose_name_plural = "Answers"

    def __str__(self):
        return f"Answer to {self.question.label}: {self.value}"
