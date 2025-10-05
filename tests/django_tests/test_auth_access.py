# tests/django_tests/test_auth_access.py
from django.test import TestCase
from django.urls import reverse
from main_app.models import CustomUser

class AuthAccessTests(TestCase):
    def setUp(self):
        # Создаем пользователей с разными ролями
        self.applicant = CustomUser.objects.create_user(
            email='applicant@example.com', 
            password='apppass123', 
            role='applicant'
        )
        self.employer = CustomUser.objects.create_user(
            email='employer@example.com', 
            password='emppass123', 
            role='employer'
        )
        self.admin = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )

        # Определяем страницы
        self.pages = {
            'applicant': [
                reverse('person_account'),
                reverse('page_person'),
                reverse('page_resume'),
                reverse('featured_jobs'),
                reverse('person_notifications'),
                reverse('payment_person_history'),
            ],
            'employer': [
                reverse('company_account'),
                reverse('page_company'),
                reverse('page_vacancy'),
                reverse('company_notifications'),
                reverse('payment_company_history'),
            ],
            'auth': [
                reverse('login'),
                reverse('register_applicant'),
                reverse('register_employer'),
            ],
        }

    def test_guest_access(self):
        """Гость не имеет доступа к закрытым страницам"""
        restricted_pages = self.pages['applicant'] + self.pages['employer']
        for url in restricted_pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)  # Редирект на login

        # Страницы auth доступны
        for url in self.pages['auth']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_applicant_access(self):
        """Соискатель имеет доступ только к своим страницам"""
        self.client.login(email='applicant@example.com', password='apppass123')

        # Доступные страницы
        for url in self.pages['applicant']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        # Недоступные страницы работодателя и регистрации
        for url in self.pages['employer'] + self.pages['auth']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_employer_access(self):
        """Работодатель имеет доступ только к своим страницам"""
        self.client.login(email='employer@example.com', password='emppass123')

        # Доступные страницы
        for url in self.pages['employer']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        # Недоступные страницы соискателя и регистрации
        for url in self.pages['applicant'] + self.pages['auth']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

    def test_admin_access(self):
        """Админ не имеет доступа к приватным страницам пользователей"""
        self.client.login(email='admin@example.com', password='adminpass123')

        # Приватные страницы applicant и employer должны быть недоступны
        for url in self.pages['applicant'] + self.pages['employer']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)

        # Страницы auth также недоступны для авторизованного админа
        for url in self.pages['auth']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
