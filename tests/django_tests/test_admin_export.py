# tests/django_tests/test_admin_export.py
import io
import pandas as pd
from django.test import TestCase
from django.urls import reverse
from main_app.models import CustomUser, Vacancy, VacancyResponse

class AdminExportTests(TestCase):
    def setUp(self):
        # Создаем суперпользователя
        self.admin = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )

        # Создаем тестовые вакансии
        self.vacancy1 = Vacancy.objects.create(
            title="Python Developer",
            employer=self.admin
        )
        self.vacancy2 = Vacancy.objects.create(
            title="Frontend Developer",
            employer=self.admin
        )

        # Создаем отклики на вакансии
        self.response1 = VacancyResponse.objects.create(
            vacancy=self.vacancy1,
            applicant=self.admin
        )
        self.response2 = VacancyResponse.objects.create(
            vacancy=self.vacancy2,
            applicant=self.admin
        )

        # URL для выгрузки отчета
        self.export_url = reverse('admin_export_xlsx')  # Используй реальный роут

    def test_export_access(self):
        """Проверяем доступ к странице экспорта только для администратора"""
        # Без логина
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 302)  # Редирект на login

        # Логин как админ
        self.client.login(email='admin@example.com', password='adminpass123')
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_export_content(self):
        """Проверяем структуру и данные выгруженного XLSX файла"""
        self.client.login(email='admin@example.com', password='adminpass123')
        response = self.client.get(self.export_url)
        self.assertTrue(response.content.startswith(b'PK'))  # XLSX — zip-архив

        file_like = io.BytesIO(response.content)
        df = pd.read_excel(file_like)

        # Колонки должны соответствовать актуальным данным
        expected_columns = ['Vacancy Title', 'Applicant Email', 'Responded At']
        self.assertListEqual(list(df.columns), expected_columns)

        # Проверяем содержимое первой строки
        first_row = df.iloc[0]
        self.assertEqual(first_row['Vacancy Title'], self.vacancy1.title)
        self.assertEqual(first_row['Applicant Email'], self.response1.applicant.email)
        self.assertIsNotNone(first_row['Responded At'])  # Дата отклика должна быть заполнена
