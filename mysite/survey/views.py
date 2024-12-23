from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse
from django.db.models import Q
from django.urls import reverse

from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import urllib, base64

from .models import Survey, Question, UserAnswer, Answer


######################################################################################

def is_admin_or_authorized(user):
    return user.is_superuser

######################################################################################

@login_required
def survey(request):
    if request.user.is_superuser:
        # Admin sees all surveys
        surveys = Survey.objects.select_related('created_by').all()
    else:
        # Regular users see surveys based on specific rules
        surveys = Survey.objects.select_related('created_by').filter(
            Q(published=True) |
            Q(created_by=request.user) |
            Q(Q(recipient_emails__icontains=request.user.email) & ~Q(recipient_emails=''))).distinct()

    # Filter out restricted surveys where the user is not invited
    filtered_surveys = []
    for survey in surveys:
        if survey.recipient_emails:
            invited_emails = [email.strip().lower() for email in survey.recipient_emails.split(',')]
            if request.user.email in invited_emails or request.user.is_superuser:
                filtered_surveys.append(survey)
        else:
            filtered_surveys.append(survey)

    return render(request, 'survey/survey.html', {'surveys': filtered_surveys})

######################################################################################

@login_required
@user_passes_test(is_admin_or_authorized)
def create_survey(request):
    if request.method == "POST":
        # Collect form data
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        slug = request.POST.get("slug", None)
        is_editable = request.POST.get("is_editable", "off") == "on"
        allow_multiple_submissions = request.POST.get("allow_multiple_submissions", "off") == "on"
        published = request.POST.get("published", "off") == "on"
        password = request.POST.get("survey_password", "").strip()
        email_fields = request.POST.getlist("emails")
        recipient_emails = ",".join([email.strip() for email in email_fields if email.strip()])

        if name and description:
            survey = Survey.objects.create(
                name=name,
                description=description,
                slug=slug or None,
                is_editable=is_editable,
                allow_multiple_submissions=allow_multiple_submissions,
                published=published,
                created_by=request.user,
                password=password,
                recipient_emails=recipient_emails)

            return redirect("survey:add-question", slug=survey.slug)

    return render(request, "survey/create_survey.html")

######################################################################################

@login_required
def survey_detail(request, slug):
    survey = get_object_or_404(Survey, slug=slug)
    questions = survey.questions.all()

    # Validate invited users
    if survey.recipient_emails:
        invited_emails = [email.strip() for email in survey.recipient_emails.split(',')]
        if request.user.email not in invited_emails:
            messages.error(request, "You are not invited to access this survey.")
            return redirect("survey:survey")

    # Validate survey password
    if survey.password:
        entered_password = request.session.get(f"survey_password_{survey.id}")
        if entered_password != survey.password:
            return redirect("survey:password-prompt", slug=survey.slug)

    # Prepare choices for questions
    for question in questions:
        question.choices_list = question.options.split(',') if question.options else []

    if request.method == "POST":
        user_answer = UserAnswer.objects.create(user=request.user, survey=survey)
        for question in questions:
            answer_value = request.POST.get(f"question_{question.id}")
            if answer_value:
                Answer.objects.create(
                    question=question,
                    value=answer_value,
                    user_answer=user_answer)
                
        return redirect(reverse("survey:survey-analysis", kwargs={"slug": survey.slug}))

    return render(request, 'survey/survey_detail.html', {'survey': survey, 'questions': questions})

######################################################################################

@login_required
@user_passes_test(is_admin_or_authorized)
def delete_survey(request, slug):
    survey = get_object_or_404(Survey, slug=slug)
    if request.method == "POST":
        survey.delete()
        return redirect("survey:survey")
    return render(request, "survey/delete_survey.html", {"survey": survey})

######################################################################################

@login_required
def edit_survey(request, slug):
    survey = get_object_or_404(Survey, slug=slug, created_by=request.user)

    if request.method == "POST":
        survey.name = request.POST.get("name")
        survey.description = request.POST.get("description")
        survey.password = request.POST.get("password", "").strip()
        email_fields = request.POST.getlist("emails")
        survey.recipient_emails = ",".join([email.strip() for email in email_fields if email.strip()])
        survey.save()
        return redirect("survey:add-question", slug=slug)

    recipient_emails = survey.recipient_emails.split(",") if survey.recipient_emails else []

    return render(request, "survey/edit_survey.html", {"survey": survey,"recipient_emails": recipient_emails,})

######################################################################################

@login_required
@user_passes_test(lambda u: u.is_superuser)
def send_survey_emails(request, slug):
    survey = get_object_or_404(Survey, slug=slug)
    survey.send_survey_emails()
    messages.success(request, "Survey emails have been sent!")
    return redirect("survey:survey-detail", slug=slug)

######################################################################################

@login_required
def password_prompt(request, slug):
    survey = get_object_or_404(Survey, slug=slug)

    if request.method == "POST":
        entered_password = request.POST.get("survey_password")
        if entered_password == survey.password:
            request.session[f"survey_password_{survey.id}"] = entered_password
            return redirect("survey:survey-detail", slug=survey.slug)
        else:
            messages.error(request, "Incorrect password. Please try again.")

    return render(request, "survey/password_prompt.html", {"survey": survey})

######################################################################################

@login_required
@user_passes_test(is_admin_or_authorized)
def add_question(request, slug):
    survey = get_object_or_404(Survey, slug=slug)

    if request.method == "POST":
        if "publish" in request.POST:
            survey.published = True
            survey.save()
            return redirect("survey:survey")
        else:
            label = request.POST.get("label")
            field_type = request.POST.get("field_type")
            options = request.POST.getlist("options")
            dimension = request.POST.get("dimension")
            area = request.POST.get("area")
            is_required = request.POST.get("is_required") == "on"

            if label and field_type:
                Question.objects.create(
                    survey=survey,
                    label=label,
                    field_type=field_type,
                    options=",".join([opt.strip()for opt in options if opt.strip()]),
                    dimension=dimension,
                    area=area,
                    is_required=is_required,)
                
            return redirect("survey:add-question", slug=slug)
        
    return render(request, "survey/add_question.html", {"survey": survey})

######################################################################################

@login_required
@user_passes_test(is_admin_or_authorized)
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == "POST":
        question.label = request.POST.get("label", question.label)
        question.field_type = int(request.POST.get("field_type", question.field_type))
        options = request.POST.getlist("options[]")
        question.options = ",".join([opt.strip()for opt in options if opt.strip()])
        question.dimension = request.POST.get("dimension", question.dimension)
        question.area = request.POST.get("area", question.area)
        question.is_required = request.POST.get("is_required") == "on"
        question.save()

        return redirect("survey:add-question", slug=question.survey.slug)
    
    options_list = question.split_choices if question.options else []
    return render(request, "survey/edit_question.html", {"question": question, "options_list": options_list})

######################################################################################

@login_required
@user_passes_test(is_admin_or_authorized)
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    survey_slug = question.survey.slug
    if request.method == "POST":
        question.delete()
        return redirect("survey:add-question", slug=survey_slug)
    return render(request, "survey/delete_question.html", {"question": question})

######################################################################################

@login_required
def survey_analysis(request, slug):
    survey = get_object_or_404(Survey, slug=slug)
    user_filter = request.GET.get('user')

    if request.user.is_superuser or survey.created_by == request.user:
        # Admins or survey creators can see all responses
        if user_filter:
            user_answers = UserAnswer.objects.filter(survey=survey, user__username=user_filter)
        else:
            user_answers = UserAnswer.objects.filter(survey=survey)
    else:
        # Regular users can see only their own responses
        user_answers = UserAnswer.objects.filter(survey=survey, user=request.user)

    answers = Answer.objects.filter(user_answer__in=user_answers)

    # Initialize data for analysis
    dimension_data = defaultdict(list)
    area_data = defaultdict(list)

    # Organize answers by dimensions and areas
    for answer in answers:
        # Convert the string answer to a numerical value based on its position in choices
        choices = answer.question.options.split(",")
        value_as_int = choices.index(answer.value.strip()) + 1  # Assign 1-based index

        # Add the numerical value to respective dimension and area data
        if answer.question.dimension:
            dimension_data[answer.question.dimension].append(value_as_int)
        if answer.question.area:
            area_data[answer.question.area].append(value_as_int)

    # Calculate averages for dimensions
    dimension_summary = {dim: sum(values) / len(values) for dim, values in dimension_data.items()}
    area_summary = {area: sum(values) / len(values) for area, values in area_data.items()}

    # Generate Matplotlib pie chart for dimensions
    plt.figure(figsize=(7, 7))
    plt.pie(dimension_summary.values(), labels=dimension_summary.keys(), autopct='%1.1f%%')
    plt.title("Analysis by Dimensions")

    # Convert plot to displayable image
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    dimension_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    # Generate bar chart for areas
    plt.figure(figsize=(8, 8))
    colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
    plt.bar(area_summary.keys(), area_summary.values(), color=colors[:len(area_summary.keys())])
    plt.title("Analysis by Areas")
    plt.ylabel("Average Score")
    plt.xticks(rotation=75, fontsize=10)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    area_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    # Get a list of all users who completed the survey (only for admins or creators)
    users = []
    if request.user.is_superuser or survey.created_by == request.user:
        users = UserAnswer.objects.filter(survey=survey).values_list('user__username', flat=True).distinct()

    return render(request, 'survey/analysis.html', {
        'survey': survey,
        'dimension_summary': dimension_summary,
        'area_summary': area_summary,
        'dimension_chart': dimension_chart,
        'area_chart': area_chart,
        'users': users,
        'selected_user': user_filter,
    })

######################################################################################

@login_required
def results_page(request):
    if request.user.is_superuser:
        responses = UserAnswer.objects.select_related('survey', 'user').all()
    else:
        responses = UserAnswer.objects.select_related('survey', 'user').filter(
            Q(user=request.user) | Q(survey__created_by=request.user)
        )
    return render(request, 'survey/results.html', {'responses': responses})

######################################################################################

@login_required
@user_passes_test(lambda u: u.is_superuser or u.surveys.exists())
def delete_analysis(request, slug, user_id):
    survey = get_object_or_404(Survey, slug=slug, created_by=request.user)
    user_answer = get_object_or_404(UserAnswer, survey=survey, user_id=user_id)
    user_answer.delete()
    messages.success(request, "The analysis has been successfully removed.")
    return redirect(reverse("results-page"))

######################################################################################

@login_required
@user_passes_test(lambda u: u.is_superuser or u.surveys.exists())
def delete_response(request, response_id):
    response = get_object_or_404(UserAnswer, id=response_id)

    if request.user != response.survey.created_by and not request.user.is_superuser:
        return HttpResponseForbidden("You are not allowed to delete this response.")

    response.delete()
    return redirect('survey:results-page')

######################################################################################