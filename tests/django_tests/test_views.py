import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from main_app.models import Vacancy, VacancyResponse, Interview, InterviewQuestion, VideoResponse, CustomUser
import json
User = get_user_model()

@pytest.mark.django_db
class TestViews:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.client = Client()
        self.tmp_path = tmp_path

        # Пользователи
        self.applicant = User.objects.create_user(
            email="applicant@example.com", password="testpass", role="applicant"
        )
        self.employer = User.objects.create_user(
            email="employer@example.com", password="testpass", role="employer"
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="testpass"
        )

        # Вакансия и отклик
        self.vacancy = Vacancy.objects.create(title="Vac1", employer=self.employer)
        self.vacancy_response = VacancyResponse.objects.create(
            vacancy=self.vacancy, applicant=self.applicant
        )

        # Интервью и вопросы
        self.interview = Interview.objects.create(
            applicant=self.applicant,
            vacancy=self.vacancy,
            unique_link="unique123",
            match_percentage=0
        )
        self.question = InterviewQuestion.objects.create(
            interview=self.interview, text="Вопрос 1"
        )

    # -------------------- Страницы --------------------
    def test_home_pages(self):
        urls = ['home', 'blog']
        for url_name in urls:
            url = reverse(url_name)
            response = self.client.get(url)
            assert response.status_code == 200

    def test_nonexistent_page(self):
        response = self.client.get("/non-existent-url/")
        assert response.status_code in [404, 200]

    # -------------------- Регистрация --------------------
    def test_register_applicant_employer(self):
        users_data = [
            {
                "url_name": "register_applicant",
                "email": "new_app@example.com",
                "data": {
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "email": "new_app@example.com",
                    "password1": "complexpass123",
                    "password2": "complexpass123",
                    "agree_to_terms": "on",                
                    "agree_to_data_processing": "on",
                },
            },
            {
                "url_name": "register_employer",
                "email": "new_emp@example.com",
                "data": {
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "email": "new_emp@example.com",
                    "password1": "complexpass123",
                    "password2": "complexpass123",
                    "phone": "+79991234567",
                    "city": "Москва",
                    "company_name": "IT Company",
                    "agree_to_terms": "on",
                    "agree_to_data_processing": "on",
                },
            },
        ]

        for user in users_data:
            url = reverse(user["url_name"])
            response = self.client.post(url, user["data"], follow=True)

            # Проверяем, прошла ли форма валидацию
            if response.context and 'form' in response.context:
                form = response.context['form']
                assert form.is_valid(), f"Ошибки формы: {form.errors.as_json()}"

            # Проверяем успешную регистрацию (redirect на home)
            assert response.status_code in [200, 302], f"Статус: {response.status_code}"



    # -------------------- Логин --------------------
    def test_login(self):
        # Успешный
        response = self.client.post(reverse('login'), {
            "username": self.applicant.email,
            "password": "testpass"
        })
        # Проверяем, что пользователь залогинен
        assert response.wsgi_request.user.is_authenticated
        # Или проверяем редирект явно
        assert response.status_code == 302
        assert response.url == "/"  # или другой URL

    # -------------------- CRUD вакансий --------------------
    def test_vacancy_crud(self):
        self.client.login(email=self.employer.email, password="testpass")

        # Создать
        url = reverse('page_vacancy')
        data = {
            "title": "New Vacancy",
            "desc_1": "Описание",
            "city_1": "Москва",
            "salary_from_1": "50000",
            "salary_to_1": "100000",
            "currency_1": "RUB",
            "exp": "1",
            "levels": "Junior",
            "relocation": "on",
            "resume_required": "on",
            "money": "1",
            "skills_hidden": "Python,Django",
            "employment_hidden": "Полная занятость",
            "work_hidden": "Полный день",
            "specialization_hidden": "Разработка",
            "languages_hidden": "Русский,Английский",
            "education_hidden": "Высшее",
        }
        response = self.client.post(url, data)
        assert response.status_code == 302
        assert Vacancy.objects.filter(title="New Vacancy").exists()

    # -------------------- Отклик на вакансию --------------------
    def test_apply_for_vacancy(self):
        self.client.login(email=self.applicant.email, password="testpass")
        url = reverse('apply_for_vacancy', args=[self.vacancy.id])
        response = self.client.post(url)
        resp_json = response.json()
        assert resp_json['success'] is True
        assert VacancyResponse.objects.filter(vacancy=self.vacancy, applicant=self.applicant).exists()

    # -------------------- Company Account --------------------
    def test_company_account_view(self):
        self.client.login(email=self.employer.email, password="testpass")
        response = self.client.get(reverse('company_account'))
        assert response.status_code == 200
        # Проверяем наличие вакансий в контексте
        assert self.vacancy in response.context['vacancies']

    # -------------------- Удаление аккаунта --------------------
    def test_delete_account(self):
        self.client.login(email=self.applicant.email, password="testpass")
        response = self.client.post(reverse('delete_account'))
        resp_json = response.json()
        assert resp_json['success'] is True
        assert not User.objects.filter(email=self.applicant.email).exists()

    # -------------------- Интервью --------------------
    def test_interview_views(self):
        # Создаём видео для вопроса
        video = SimpleUploadedFile("test.webm", b"fake video", content_type="video/webm")
        self.question.video = video
        self.question.save()

        # Создаём фото HR (опционально)
        photo = SimpleUploadedFile("hr.jpg", b"fake image", content_type="image/jpeg")
        self.interview.hr_photo = photo
        self.interview.save()

        self.client.login(email=self.applicant.email, password="testpass")
        url = reverse('interview_applicant_main', args=[self.interview.unique_link])
        response = self.client.get(url)
        assert response.status_code == 200

    # -------------------- Сохранение ответа на вопрос --------------------
    def test_save_answer(self):
        url = reverse('save_answer')
        data = {"question_id": self.question.id, "transcribed_text": "Мой ответ"}
        response = self.client.post(url, json.dumps(data), content_type="application/json")
        resp_json = response.json()
        self.question.refresh_from_db()
        assert resp_json['success'] is True
        assert self.question.text_answer == "Мой ответ"

    # -------------------- Обновление процента совпадения --------------------
    def test_update_interview_match(self):
        url = reverse('update_interview_match')
        data = {"session_id": self.interview.unique_link, "percentage": 85, "conversation_log": ["Бот: Q", "Пользователь: A"]}
        response = self.client.post(url, json.dumps(data), content_type="application/json")
        resp_json = response.json()
        self.interview.refresh_from_db()
        assert resp_json['success'] is True
        assert self.interview.match_percentage == 85

    # -------------------- Сохранение видеоответа --------------------
    def test_save_interview_video_response(self):
        self.client.login(email=self.applicant.email, password="testpass")
        url = reverse('save_interview_video_response')
        video_file = self.tmp_path / "video.mp4"
        video_file.write_bytes(b"fake video content")
        with open(video_file, "rb") as f:
            response = self.client.post(url, {"video_response": f, "question_id": self.question.id})
        resp_json = response.json()
        assert resp_json['success'] is True
        assert VideoResponse.objects.filter(question=self.question).exists()

    # -------------------- Тесты профиля --------------------
    def test_page_person_profile(self):
        self.client.login(email=self.applicant.email, password="testpass")
        url = reverse('page_person')

        # GET страница
        response = self.client.get(url)
        assert response.status_code == 200

        # POST обновление профиля
        data = {
            "first_name": "Иван",
            "last_name": "Иванов",
            "email": self.applicant.email,
            "action": "save_changes",  # обязательно для срабатывания сохранения
        }
        response = self.client.post(url, data)

        
        # Проверяем редирект после успешного сохранения
        assert response.status_code in [302, 301]

        # Обновляем объект из БД
        self.applicant.refresh_from_db()

        # Проверяем, что данные сохранились
        assert self.applicant.first_name == "Иван"
        assert self.applicant.last_name == "Иванов"


    def test_page_company_profile(self):
        self.client.login(email=self.employer.email, password="testpass")
        url = reverse('page_company')
        response = self.client.get(url)
        assert response.status_code == 200
        # POST обновление компании
        data = {"company_name": "Компания", "description": "Описание"}
        response = self.client.post(url, data)
        assert response.status_code == 302

    def test_register_employer_view(self):
        """
        Проверяет корректную регистрацию работодателя через view register_employer.
        """

        url = reverse('register_employer')

        # Корректные данные
        data = {
            "first_name": "Сергей",
            "last_name": "Петров",
            "email": "sergey@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "phone": "+79995556677",
            "city": "Москва",
            "company_name": "TechCorp",
            "agree_to_terms": "on",
            "agree_to_data_processing": "on",
        }

        # Отправляем POST-запрос
        response = self.client.post(url, data, follow=True)

        # Проверяем, что форма прошла валидацию и пользователь создан
        assert response.status_code in [200, 302]
        assert User.objects.filter(email="sergey@example.com").exists()

        # Проверяем, что после успешной регистрации редирект на 'home'
        if response.redirect_chain:
            redirect_url, status_code = response.redirect_chain[-1]
            assert redirect_url in [reverse('home'), '/']


    def test_register_employer_invalid_form(self):
        """
        Проверяет случай, когда форма невалидна.
        Например, разные пароли.
        """

        url = reverse('register_employer')
        data = {
            "first_name": "Иван",
            "last_name": "Неверный",
            "email": "wrong@example.com",
            "password1": "12345678",
            "password2": "87654321",  # не совпадают
            "phone": "+79990000000",
            "city": "Москва",
            "company_name": "BadCompany",
            "agree_to_terms": "on",
            "agree_to_data_processing": "on",
        }

        response = self.client.post(url, data)
        assert response.status_code == 200  # остаёмся на странице
        assert not User.objects.filter(email="wrong@example.com").exists()

        # Проверяем наличие текста ошибки (через messages или контекст формы)
        if hasattr(response, "context") and "form" in response.context:
            form = response.context["form"]
            assert not form.is_valid()
            assert "password2" in form.errors or "password_mismatch" in str(form.errors)