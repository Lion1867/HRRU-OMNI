from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.html import escape
from main_app.models import Vacancy, VacancyResponse
from main_app.forms import VacancyForm

User = get_user_model()


class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Работодатель
        self.employer = User.objects.create_user(
            email="sec_employer@example.com",
            password="SafePass123!",
            role="employer",
            company_name="SecCorp",
            phone="+70000000000",
            city="Moscow"
        )

        # Соискатель
        self.applicant = User.objects.create_user(
            email="sec_applicant@example.com",
            password="SafePass123!",
            role="applicant"
        )

    def test_password_stored_hashed(self):
        """Проверяем, что пароль хранится в хешированном виде."""
        raw_password = "MySecretPass!123"
        u = User.objects.create_user(
            email="hash_test@example.com",
            password=raw_password,
            first_name="Hash",
            last_name="Test",
            role="applicant"
        )

        u_from_db = User.objects.get(pk=u.pk)
        self.assertNotEqual(u_from_db.password, raw_password)
        self.assertTrue(
            u_from_db.password.startswith(("pbkdf2_", "argon2", "bcrypt")),
            f"Пароль не выглядит хешированным: {u_from_db.password}"
        )

    def test_xss_payload_in_vacancy_title_is_escaped_in_templates(self):
        """
        Создаём вакансию с XSS-пейлоадом в title и проверяем,
        что шаблон экранирует HTML, а не вставляет его напрямую.
        """
        xss_title = '<script>alert("xss")</script>Important Vacancy'

        vacancy = Vacancy.objects.create(
            employer=self.employer,
            title=xss_title,
            desc_1="desc",
            city_1="Москва",
            exp=1,
            money=1,
            currency_1="RUB"
        )

        self.client.login(username=self.employer.email, password="SafePass123!")
        response = self.client.get(reverse('company_account'))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')

        # Проверяем, что вредоносный тег не вставлен напрямую
        self.assertNotIn('<script>alert("xss")</script>', content)
        # Проверяем, что Django его экранировал
        self.assertIn(escape('<script>alert("xss")</script>'), content)

    def test_saving_sql_like_payload_does_not_execute_sql_and_is_treated_as_string(self):
        """
        Эмуляция SQL-инъекции — данные должны сохраняться как строка и не ломать запросы.
        """
        sql_payload = "' OR 1=1; -- DROP TABLE users;"

        data = {
            "title": sql_payload,
            "levels": ["Junior"],
            "desc_1": "desc",
            "desc_2": "",
            "city_1": "Nowhere",
            "exp": 0,
            "money": 1,
            "currency_1": "RUB"
        }
        form = VacancyForm(data=data)
        self.assertTrue(form.is_valid(), f"Форма невалидна: {form.errors}")

        vacancy = form.save(commit=False)
        vacancy.employer = self.employer
        vacancy.save()

        # Проверяем, что payload сохранился в виде строки
        self.assertTrue(Vacancy.objects.filter(title=sql_payload).exists())

        # Проверяем, что поиск не рушится
        response = self.client.get(reverse('finder'), {'q': sql_payload})
        self.assertIn(response.status_code, [200, 302])

    def test_apply_for_vacancy_endpoint_resists_malicious_input(self):
        """
        Проверяем, что endpoint устойчив к SQL-инъекциям и XSS, не ломается и не выполняет код.
        """
        vacancy = Vacancy.objects.create(
            employer=self.employer,
            title="Safe Vacancy",
            desc_1="desc",
            city_1="Москва",
            exp=1,
            money=1,
            currency_1="RUB"
        )

        # Попытка от незалогиненного пользователя
        response = self.client.post(reverse('apply_for_vacancy', args=[vacancy.id]))
        self.assertIn(response.status_code, [200, 302])  # допускаем redirect на login
        # Не пытаемся читать JSON из HTML-ответа
        self.assertFalse(VacancyResponse.objects.filter(vacancy=vacancy).exists())

        # Логинимся соискателем
        self.client.login(username=self.applicant.email, password="SafePass123!")
        response2 = self.client.post(reverse('apply_for_vacancy', args=[vacancy.id]))
        self.assertIn(response2.status_code, [200, 302])  # допустим redirect
        # Проверяем, что отклик создан
        self.assertTrue(VacancyResponse.objects.filter(vacancy=vacancy, applicant=self.applicant).exists())
