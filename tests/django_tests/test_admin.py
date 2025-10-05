# tests/test_admin.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from main_app.admin import CustomUserAdmin, VacancyAdmin, VacancyResponseAdmin, ResumeAdmin
from main_app.models import CustomUser, Vacancy, VacancyResponse, Resume

User = get_user_model()

class AdminTests(TestCase):

    def setUp(self):
        # Клиент и суперпользователь
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        self.client.login(email="admin@example.com", password="adminpass123")

        # Примеры объектов
        self.employer = User.objects.create_user(email="employer@example.com", password="pass", role="employer")
        self.applicant = User.objects.create_user(email="applicant@example.com", password="pass", role="applicant")
        self.vacancy = Vacancy.objects.create(title="Python Dev", employer=self.employer)
        self.resume = Resume.objects.create(
            user=self.applicant,
            specialization="Backend",
            general_experience_number=3
        )
        self.response = VacancyResponse.objects.create(vacancy=self.vacancy, applicant=self.applicant)

        # Админ site
        self.site = AdminSite()

    def test_user_admin_fieldsets(self):
        """Проверка fieldsets в зависимости от роли"""
        admin = CustomUserAdmin(User, self.site)

        employer_fieldsets = admin.get_fieldsets(request=None, obj=self.employer)
        applicant_fieldsets = admin.get_fieldsets(request=None, obj=self.applicant)

        # Проверяем, что поле company_name есть у работодателя
        employer_fields = [f for _, opts in employer_fieldsets for f in opts['fields']]
        self.assertIn('company_name', employer_fields[0] if isinstance(employer_fields[0], tuple) else employer_fields)

        # Проверяем, что citizenship есть у соискателя
        applicant_fields = [f for _, opts in applicant_fieldsets for f in opts['fields']]
        self.assertIn('citizenship', applicant_fields[0] if isinstance(applicant_fields[0], tuple) else applicant_fields)

    def test_admin_list_display_and_search(self):
        """Проверка list_display и search_fields"""
        vacancy_admin = VacancyAdmin(Vacancy, self.site)
        self.assertIn('title', vacancy_admin.list_display)
        self.assertIn('employer__company_name', vacancy_admin.search_fields)

        response_admin = VacancyResponseAdmin(VacancyResponse, self.site)
        self.assertIn('responded_at', response_admin.list_display)

        resume_admin = ResumeAdmin(Resume, self.site)
        self.assertIn('specialization', resume_admin.list_display)
        self.assertIn('user__email', resume_admin.search_fields)

    def test_admin_inline_for_employer(self):
        """Проверка, что VacancyInline появляется только у работодателя"""
        admin = CustomUserAdmin(User, self.site)
        inlines_employer = admin.get_inline_instances(request=None, obj=self.employer)
        inlines_applicant = admin.get_inline_instances(request=None, obj=self.applicant)

        self.assertTrue(any(type(i).__name__ == 'VacancyInline' for i in inlines_employer))
        self.assertEqual(len(inlines_applicant), 0)

    def test_admin_views_accessible(self):
        """Проверка, что админка открывается и объекты видны"""
        self.client.force_login(self.admin_user)

        # Главная админка
        url = reverse('admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Список вакансий
        vacancy_url = reverse('admin:main_app_vacancy_changelist')
        response = self.client.get(vacancy_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.vacancy.title)

        # Список откликов
        response_url = reverse('admin:main_app_vacancyresponse_changelist')
        response = self.client.get(response_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.response.applicant))  # <- заменили

        # Список резюме
        resume_url = reverse('admin:main_app_resume_changelist')
        response = self.client.get(resume_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.resume.specialization)
