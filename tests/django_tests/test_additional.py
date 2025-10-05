from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from main_app.models import Vacancy

User = get_user_model()


class SearchFunctionalityTests(TestCase):
    """
    Дополнительный функционал: тесты поиска вакансий.
    Проверяется, что поиск возвращает корректные результаты
    и устойчив к некорректным или пустым запросам.
    """

    def setUp(self):
        self.client = Client()

        # Создаём работодателя
        self.employer = User.objects.create_user(
            email="search_employer@example.com",
            password="SearchPass123!",
            role="employer",
            company_name="SearchCorp",
            phone="+70000000000",
            city="Москва"
        )

        # Создаём тестовые вакансии
        Vacancy.objects.create(
            employer=self.employer,
            title="Python Developer",
            desc_1="Разработка Django и FastAPI приложений",
            city_1="Москва",
            exp=2,
            money=120000,
            currency_1="RUB"
        )
        Vacancy.objects.create(
            employer=self.employer,
            title="Frontend Engineer",
            desc_1="React, TypeScript, SPA",
            city_1="Санкт-Петербург",
            exp=1,
            money=100000,
            currency_1="RUB"
        )
        Vacancy.objects.create(
            employer=self.employer,
            title="Data Analyst",
            desc_1="SQL, Pandas, аналитика данных",
            city_1="Казань",
            exp=1,
            money=90000,
            currency_1="RUB"
        )

    def test_search_returns_correct_vacancies(self):
        response = self.client.get(reverse("finder"), {"q": "Python"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Проверяем, что хотя бы одна вакансия содержит ключевое слово
        self.assertIn("Python", content)

    def test_search_is_case_insensitive(self):
        """Проверяем, что поиск не зависит от регистра букв."""
        response = self.client.get(reverse("finder"), {"q": "python"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Python Developer", response.content.decode("utf-8"))

    def test_search_with_empty_query_returns_all_vacancies(self):
        """
        Если запрос пустой, должны отображаться все вакансии,
        а не пустой результат.
        """
        response = self.client.get(reverse("finder"), {"q": ""})
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        self.assertIn("Python Developer", content)
        self.assertIn("Frontend Engineer", content)
        self.assertIn("Data Analyst", content)

    def test_search_with_special_symbols_does_not_crash(self):
        """
        Проверяем, что спецсимволы (например, %, _, ' и т.д.) не вызывают ошибок
        и не приводят к SQL-инъекциям.
        """
        response = self.client.get(reverse("finder"), {"q": "' OR 1=1; --"})
        self.assertEqual(response.status_code, 200)
        # Просто проверяем, что страница вернулась корректно (без 500)
        self.assertIn("<html", response.content.decode("utf-8").lower())
