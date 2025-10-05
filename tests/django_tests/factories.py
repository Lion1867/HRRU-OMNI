import factory
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


# === Базовая фабрика пользователя ===
class CustomUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False


# === Подфабрики для разных ролей ===
class EmployerFactory(CustomUserFactory):
    role = "employer"


class ApplicantFactory(CustomUserFactory):
    role = "applicant"


# === Фабрика вакансий ===
class VacancyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vacancy

    title = factory.Faker("job")
    employer = factory.SubFactory(EmployerFactory)
    city_1 = factory.Faker("city")
    salary_from_1 = "50000"
    salary_to_1 = "100000"
    currency_1 = "RUB"
    exp = 1


# === Фабрика интервью ===
class InterviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Interview

    applicant = factory.SubFactory(ApplicantFactory)
    vacancy = factory.SubFactory(VacancyFactory)
    gender = "МУЖ"
    hr_name = factory.Faker("name")


# === Фабрика вопросов интервью ===
class InterviewQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewQuestion

    interview = factory.SubFactory(InterviewFactory)
    text = factory.Faker("sentence")
    question_order = 1


# === Фабрика видеореспондов ===
class VideoResponseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VideoResponse

    question = factory.SubFactory(InterviewQuestionFactory)
    file = factory.django.FileField(filename="test.mp4", data=b"video data")


# === Фабрика резюме ===
class ResumeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Resume

    user = factory.SubFactory(ApplicantFactory)
    specialization = factory.Faker("job")
    key_skills = ["Python", "Django"]
    work_experience = [{"position": "Junior Developer", "company": "ABC Corp"}]
    general_experience_number = "2"


# === Фабрика отклика на вакансию ===
class VacancyResponseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VacancyResponse

    applicant = factory.SubFactory(ApplicantFactory)
    vacancy = factory.SubFactory(VacancyFactory)
