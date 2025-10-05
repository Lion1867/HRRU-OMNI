import pytest
import time
from django.core.exceptions import ValidationError
from django.utils import timezone
from main_app.models import (
    CustomUser,
    Vacancy,
    Interview,
    InterviewQuestion,
    VideoResponse,
    Resume,
    VacancyResponse,
)
from .factories import (
    EmployerFactory,
    ApplicantFactory,
    VacancyFactory,
    InterviewFactory,
    InterviewQuestionFactory,
    VideoResponseFactory,
    ResumeFactory,
    VacancyResponseFactory,
)


@pytest.mark.django_db
class TestCustomUserModel:
    def test_create_user(self):
        user = CustomUser.objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="John",
            last_name="Doe",
        )
        assert user.email == "test@example.com"
        assert user.check_password("password123")
        assert not user.is_superuser
        assert not user.is_staff

    def test_create_superuser(self):
        superuser = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="admin123",
            first_name="Admin",
            last_name="User",
        )
        assert superuser.is_superuser
        assert superuser.is_staff

    def test_user_str(self):
        user = ApplicantFactory(first_name="Иван", last_name="Петров")
        assert str(user) == "Иван Петров (Соискатель)"

    def test_employer_validation(self):
        user = CustomUser(
            email="employer@example.com",
            first_name="Employer",
            last_name="Test",
            role="employer",
            phone="",  # Ошибка — нет телефона
            city="",
            company_name="",
        )
        with pytest.raises(ValidationError):
            user.clean()

    def test_employer_valid(self):
        user = CustomUser(
            email="employer@example.com",
            first_name="Employer",
            last_name="Test",
            role="employer",
            phone="+79991234567",
            city="Москва",
            company_name="IT Company",
        )
        user.clean()
        user.save()
        assert user.phone == "+79991234567"

    def test_applicant_can_have_empty_phone(self):
        user = CustomUser(
            email="applicant@example.com",
            first_name="Applicant",
            last_name="Test",
            role="applicant",
            phone="",  # Для соискателя необязательно
            city="",
            company_name="",
        )
        user.clean()
        user.save()


@pytest.mark.django_db
class TestVacancyModel:
    def test_vacancy_creation(self):
        employer = EmployerFactory(phone="+79991234567", city="Москва", company_name="IT Corp")
        vacancy = VacancyFactory(employer=employer)
        assert vacancy.title
        assert vacancy.employer == employer
        assert vacancy.created_at is not None

    def test_vacancy_clean_for_non_employer(self):
        applicant = ApplicantFactory()
        vacancy = Vacancy(employer=applicant, title="Test Vacancy")
        with pytest.raises(ValidationError):
            vacancy.clean()

    def test_vacancy_str(self):
        employer = EmployerFactory(company_name="MyCompany")
        vacancy = Vacancy(title="Python Dev", employer=employer)
        assert str(vacancy) == "Python Dev - MyCompany"


@pytest.mark.django_db
class TestInterviewModel:
    def test_interview_creation(self):
        applicant = ApplicantFactory()
        vacancy = VacancyFactory()
        interview = InterviewFactory(applicant=applicant, vacancy=vacancy)
        assert interview.applicant == applicant
        assert interview.vacancy == vacancy
        assert interview.created_at is not None
        assert interview.unique_link

    def test_interview_clean_for_non_applicant(self):
        employer = EmployerFactory()
        vacancy = VacancyFactory()
        interview = Interview(applicant=employer, vacancy=vacancy, gender="МУЖ")
        with pytest.raises(ValidationError):
            interview.clean()

    def test_interview_save_calls_clean(self):
        employer = EmployerFactory()
        vacancy = VacancyFactory()
        interview = Interview(applicant=employer, vacancy=vacancy, gender="МУЖ")
        with pytest.raises(ValidationError):
            interview.save()


@pytest.mark.django_db
class TestInterviewQuestionModel:
    def test_question_creation(self):
        interview = InterviewFactory()
        question = InterviewQuestionFactory(interview=interview, text="Why do you want this job?")
        assert question.interview == interview
        assert question.text == "Why do you want this job?"
        assert question.question_order > 0

    def test_auto_order_on_save(self):
        interview = InterviewFactory()
        q1 = InterviewQuestionFactory(interview=interview, question_order=1)
        q2 = InterviewQuestionFactory(interview=interview)
        assert q2.question_order == 2

    def test_video_responses(self):
        question = InterviewQuestionFactory()
        vr = VideoResponseFactory(question=question)
        assert vr in question.video_responses.all()
        assert vr.uploaded_at is not None


@pytest.mark.django_db
class TestResumeModel:
    def test_resume_creation(self):
        user = ApplicantFactory()
        resume = ResumeFactory(user=user)
        assert resume.user == user
        assert resume.specialization
        assert isinstance(resume.key_skills, list)
        assert resume.created_at is not None
        assert resume.updated_at is not None

    def test_resume_updated_at_changes(self):
        resume = ResumeFactory()
        old_updated = resume.updated_at
        time.sleep(0.001)  # небольшая задержка, чтобы timestamp изменился
        resume.specialization = "Updated Specialization"
        resume.save()
        assert resume.updated_at > old_updated



@pytest.mark.django_db
class TestVacancyResponseModel:
    def test_response_creation(self):
        applicant = ApplicantFactory()
        vacancy = VacancyFactory()
        response = VacancyResponseFactory(applicant=applicant, vacancy=vacancy)
        assert response.applicant == applicant
        assert response.vacancy == vacancy
        assert response.responded_at is not None

    def test_response_str(self):
        applicant = ApplicantFactory(first_name="Alice", last_name="Smith")
        vacancy = VacancyFactory(title="Senior Python Dev")
        response = VacancyResponse(applicant=applicant, vacancy=vacancy)
        assert str(response) == "Alice Smith (Соискатель) откликнулся на вакансию Senior Python Dev"

