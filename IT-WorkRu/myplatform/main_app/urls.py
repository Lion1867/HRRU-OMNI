from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import delete_account

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register_employer/', views.register_employer, name='register_employer'),
    path('register_applicant/', views.register_applicant, name='register_applicant'),
    path('finder/', views.finder, name='finder'),
    path('company_account/', views.company_account, name='company_account'),
    path('person_account/', views.person_account, name='person_account'),
    path('page_company/', views.page_company, name='page_company'),
    path('page_person/', views.page_person, name='page_person'),
    path('page_vacancy/', views.page_vacancy, name='page_vacancy'),
    path('page_resume/', views.page_resume, name='page_resume'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('blog/', views.blog, name='blog'),
    path('featured_jobs/', views.featured_jobs, name='featured_jobs'),
    path('person_notifications/', views.person_notifications, name='person_notifications'),
    path('payment_person_history/', views.payment_person_history, name='payment_person_history'),
    path('company_notifications/', views.company_notifications, name='company_notifications'),
    path('payment_company_history/', views.payment_company_history, name='payment_company_history'),
    path('delete_account/', delete_account, name='delete_account'),
    path('interview_applicant_main/<str:unique_link>/', views.interview_applicant_main, name='interview_applicant_main'),
    path('save_answer/', views.save_answer, name='save_answer'),
    path('vacancy/<int:vacancy_id>/apply/', views.apply_for_vacancy, name='apply_for_vacancy'),
    path('create_interview/', views.create_interview, name='create_interview'),
    path('api/interview/update-match/', views.update_interview_match, name='update_interview_match'),
    path('save_interview_video_response/', views.save_interview_video_response, name='save_interview_video_response'),
    path('interview-details/<int:interview_id>/', views.get_interview_details, name='interview_details'),
]
