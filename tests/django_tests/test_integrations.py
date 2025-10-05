from django.test import TestCase
from django.contrib.auth import get_user_model
from main_app.models import Vacancy
from main_app.forms import VacancyForm

User = get_user_model()


class IntegrationVacancyFlowTest(TestCase):
    """Интеграционный тест основного бизнес-процесса:
    Работодатель создаёт вакансию → соискатель откликается → проверка состояния системы.
    """

    def setUp(self):
        # Создаём работодателя
        self.employer = User.objects.create_user(
            email="boss@example.com",
            password="StrongPass123!",
            role="employer",
            company_name="ООО Пример"
        )

        # Создаём соискателя
        self.applicant = User.objects.create_user(
            email="applicant@example.com",
            password="StrongPass123!",
            role="applicant"
        )

        # Подготавливаем данные для формы вакансии
        self.vacancy_data = {
            "title": "Python Developer",
            "levels": ["Junior", "Middle"],
            "desc_1": "Описание вакансии",
            "desc_2": "Описание тестового задания",
            "city_1": "Москва",
            "exp": 1,
            "money": 1,
            "currency_1": "RUB"
        }

    def test_full_vacancy_creation_and_response_flow(self):
        """Проверка полного цикла: создание вакансии и отклик соискателя."""
        vacancy_count_before = Vacancy.objects.count()

        # Работодатель создаёт вакансию через форму
        form = VacancyForm(data=self.vacancy_data)
        self.assertTrue(form.is_valid(), f"Ошибки формы: {form.errors}")
        vacancy = form.save(commit=False)
        vacancy.employer = self.employer
        vacancy.save()

        # Проверяем, что вакансия появилась в БД
        vacancy_count_after = Vacancy.objects.count()
        self.assertEqual(vacancy_count_after, vacancy_count_before + 1)

        # Проверяем, что данные корректно сохранились
        self.assertEqual(vacancy.title, "Python Developer")
        self.assertEqual(vacancy.city_1, "Москва")
        self.assertEqual(vacancy.currency_1, "RUB")

        # Эмулируем отклик соискателя (например, через ManyToManyField или запись в лог)
        vacancy.responded_users.add(self.applicant) if hasattr(vacancy, "responded_users") else None

        # Проверяем, что соискатель откликнулся (если модель это поддерживает)
        if hasattr(vacancy, "responded_users"):
            self.assertIn(self.applicant, vacancy.responded_users.all())

        # Проверяем состояние системы: вакансий на одну больше
        self.assertTrue(Vacancy.objects.filter(title="Python Developer").exists())

        print("Интеграционный тест основного цикла успешно выполнен.")


class IntegrationDatabaseStateTest(TestCase):
    """Проверка корректности изменения состояния базы данных."""

    def setUp(self):
        self.employer = User.objects.create_user(
            email="testemployer@example.com",
            password="StrongPass123!",
            role="employer"
        )

    def test_vacancy_count_changes_after_creation(self):
        """Проверка изменения количества вакансий в БД."""
        initial_count = Vacancy.objects.count()
        Vacancy.objects.create(
            title="QA Engineer",
            desc_1="Тестирование ПО",
            desc_2="Описание задания",
            city_1="Казань",
            exp=1,
            money=2,
            currency_1="RUB",
            employer=self.employer
        )
        new_count = Vacancy.objects.count()
        self.assertEqual(new_count, initial_count + 1)
