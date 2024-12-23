from django.urls import path
from . import views

app_name = 'survey'

urlpatterns = [
    path('', views.survey, name="survey"),
    path('create/', views.create_survey, name="create_survey"),
    path('edit/<slug:slug>/', views.edit_survey, name="edit-survey"),
    path('delete/<slug:slug>/', views.delete_survey, name="delete-survey"),
    path('results/', views.results_page, name="results-page"),
    path('<slug:slug>/', views.survey_detail, name="survey-detail"),
    path('password-prompt/<slug:slug>/', views.password_prompt, name="password-prompt"),
    path('add-question/<slug:slug>/', views.add_question, name="add-question"),
    path('edit-question/<int:question_id>/', views.edit_question, name="edit-question"),
    path('delete-question/<int:question_id>/', views.delete_question, name="delete-question"),
    path('<slug:slug>/analysis/', views.survey_analysis, name="survey-analysis"),
    path('<slug:slug>/delete-analysis/<int:user_id>/', views.delete_analysis, name="delete-analysis"),
    path('delete-response/<int:response_id>/', views.delete_response, name='delete-response'),

]
