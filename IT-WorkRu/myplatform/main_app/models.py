from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('employer', 'Работодатель'),
        ('applicant', 'Соискатель'),
    )

    GENDER_CHOICES = (
        ('M', 'Мужской'),
        ('F', 'Женский'),
    )

    WORK_STATUS_CHOICES = (
        ('S', 'В поиске работы'),
        ('N', 'Не ищу работу'),
    )

    inn = models.CharField(max_length=50, blank=True, null=True, verbose_name='ИНН')
    ogr = models.CharField(max_length=50, blank=True, null=True, verbose_name='ОГРН/ОГРНИП')
    kpp = models.CharField(max_length=50, blank=True, null=True, verbose_name='КПП')
    desc = models.TextField(blank=True, null=True, verbose_name='Описание компании')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M', verbose_name='Пол')
    work_status = models.CharField(max_length=1, choices=WORK_STATUS_CHOICES, default='S', verbose_name='Статус на сайте')
    email = models.EmailField(unique=True, verbose_name='E-mail физического лица')
    company_email = models.EmailField(blank=True, null=True, verbose_name='E-mail компании')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    first_name = models.CharField(max_length=30, verbose_name='Имя')
    last_name = models.CharField(max_length=30, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=30, blank=True, null=True, verbose_name='Отчество')
    birth_date = models.DateField(blank=True, null=True, verbose_name='Дата рождения')
    phone = models.CharField(max_length=15, blank=True, null=True, verbose_name='Телефон')
    city = models.CharField(max_length=50, blank=True, null=True, verbose_name='Город')
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True, verbose_name='Фото профиля')
    citizenship = models.CharField(max_length=50, blank=True, null=True, verbose_name='Гражданство')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Адрес')
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name='Индекс')
    vk_link = models.CharField(max_length=200, blank=True, null=True, verbose_name='ВКонтакте')
    site_link = models.CharField(max_length=200, blank=True, null=True, verbose_name='Сайт компании')
    ok_link = models.CharField(max_length=200, blank=True, null=True, verbose_name='Одноклассники')
    telegram_link = models.CharField(max_length=200, blank=True, null=True, verbose_name='Telegram')
    whatsapp_link = models.CharField(max_length=200, blank=True, null=True, verbose_name='WhatsApp')
    skype_link = models.CharField(max_length=200, blank=True, null=True, verbose_name='Skype')

    telephone_show = models.BooleanField(default=False, verbose_name="Отображать номер телефона в резюме")
    social_network_show = models.BooleanField(default=False,
                                              verbose_name="Отображать ссылки на профили социальных сетей в резюме")

    company_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название компании')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def clean(self):
        if self.role == 'employer':
            if not self.phone or not self.city or not self.company_name:
                raise ValidationError("Телефон, город и название компании обязательны для работодателей.")

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.get_role_display()})'



class Vacancy(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    employer = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='vacancies',
        verbose_name='Работодатель'
    )
    title = models.CharField(max_length=255, verbose_name='Название вакансии')

    desc_1 = models.TextField(blank=True, null=True, verbose_name='Описание вакансии')
    desc_2 = models.TextField(blank=True, null=True, verbose_name='Описание тестового задания')

    city_1 = models.CharField(max_length=50, blank=True, null=True, verbose_name='Город')
    address_1 = models.CharField(max_length=255, blank=True, null=True, verbose_name='Адрес')
    postal_code_1 = models.CharField(max_length=10, blank=True, null=True, verbose_name='Индекс')
    salary_from_1 = models.CharField(max_length=7, blank=True, null=True, verbose_name='Зарплата от')
    salary_to_1 = models.CharField(max_length=7, blank=True, null=True, verbose_name='Зарплата до')
    # Поле для хранения выбранных уровней.
    # Выбранные варианты будем сохранять как строку, например: "Junior,Middle"
    levels = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Уровни компетенций'
    )

    relocation = models.BooleanField(
        default=False,
        verbose_name='Релокейт соискателя'
    )
    resume_required = models.BooleanField(
        default=False,
        verbose_name='Обязательно наличие резюме'
    )

    EXPERIENCE_CHOICES = (
        (0, "Нет опыта"),
        (1, "От 1 до 3 лет"),
        (2, "От 3 до 6 лет"),
        (3, "Более 6"),
    )
    exp = models.PositiveSmallIntegerField(
        choices=EXPERIENCE_CHOICES,
        verbose_name='Опыт работы', blank=True, null=True
    )

    SALARY_CHOICES = (
        (1, "На руки"),
        (0, "До вычета налогов"),
    )
    money = models.IntegerField(
        choices=SALARY_CHOICES,
        default=1,
        verbose_name='Тип зарплаты', blank=True, null=True
    )

    skills_hidden = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Ключевые навыки'
    )

    currency_1 = models.CharField(
        max_length=3,
        choices=[
            ('RUB', '₽'),
            ('USD', '$'),
            ('EUR', '€'),
            ('CNY', '¥'),
        ],
        default='RUB',
        verbose_name='Валюта зарплаты', blank=False, null=False
    )

    employment_hidden = models.CharField(max_length=255, blank=True, null=True, verbose_name='Тип занятости')
    work_hidden = models.CharField(max_length=255, blank=True, null=True, verbose_name='График работы')
    specialization_hidden = models.CharField(max_length=255, blank=True, null=True,
                                             verbose_name='Специализация')
    languages_hidden = models.CharField(max_length=255, blank=True, null=True,
                                             verbose_name='Владение языками')
    education_hidden = models.CharField(max_length=255, blank=True, null=True,
                                             verbose_name='Уровень образования')
    def clean(self):
        if not self.employer_id:
            return
        if self.employer.role != 'employer':
            raise ValidationError('Только работодатели могут создавать вакансии.')

    def __str__(self):
        company = self.employer.company_name if self.employer.company_name else ''
        return f"{self.title} - {company}"

    class Meta:
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"


class Interview(models.Model):
    applicant = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='interviews',
        verbose_name=_('Соискатель'),
        limit_choices_to={'role': 'applicant'}  # Ограничиваем выбор пользователей
    )
    vacancy = models.ForeignKey(
        'Vacancy',
        on_delete=models.CASCADE,
        related_name='interviews',
        verbose_name=_('Вакансия')
    )
    gender = models.CharField(
        max_length=10,
        choices=[
            ('МУЖ', 'Мужской'),
            ('ЖЕН', 'Женский')
        ],
        verbose_name='Пол'
    )
    hr_name = models.CharField(
        max_length=100,
        verbose_name=_('Имя HR'),
        blank=True,  # Это поле может быть пустым, если HR не указан
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    unique_link = models.CharField(max_length=255, unique=True, verbose_name=_('Уникальная ссылка'), default=uuid.uuid4)

    match_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_('Процент соответствия вакансии'),
        null=True,
        blank=True,
        help_text=_('Например: 87.50 — означает 87.5% соответствия требованиям вакансии')
    )

    summary = models.TextField(
        verbose_name=_('Суммаризация интервью'),
        null=True,
        blank=True,
        help_text=_('Краткое содержание интервью, полученное от ИИ')
    )

    class Meta:
        verbose_name = _('Интервью')
        verbose_name_plural = _('Интервью')

    def __str__(self):
        return f'Интервью {self.applicant} - {self.vacancy}'

    def clean(self):
        """Проверка перед сохранением, является ли пользователь соискателем"""
        if self.applicant.role != 'applicant':
            raise ValidationError(_('Выбранный пользователь не является соискателем'))

    def save(self, *args, **kwargs):
        """Вызов clean() перед сохранением"""
        self.clean()
        super().save(*args, **kwargs)

class InterviewQuestion(models.Model):
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('Интервью')
    )
    text = models.TextField(verbose_name=_('Текст вопроса'))
    text_answer = models.TextField(blank=True, null=True, verbose_name=_('Текст ответа'))
    video = models.FileField(upload_to='interview_videos/', blank=True, null=True, verbose_name=_('Видеофайл'))
    question_order = models.PositiveIntegerField(verbose_name=_('Порядок вопроса'), default=0)

    class Meta:
        verbose_name = _('Вопрос интервью')
        verbose_name_plural = _('Вопросы интервью')

    def __str__(self):
        return f'Вопрос #{self.id} ({self.text[:30]}...)'

from django.utils.html import format_html, format_html_join
class InterviewQuestionInline(admin.TabularInline):
    model = InterviewQuestion
    extra = 1
    fields = ('text', 'video', 'question_order', 'text_answer', 'video_responses_list')
    readonly_fields = ('video_responses_list',)
    verbose_name = _('Вопрос интервью')
    verbose_name_plural = _('Вопросы интервью')

    def video_responses_list(self, obj):
        responses = obj.video_responses.all()
        if not responses.exists():
            return "—"
        return format_html_join(
            '<br><br>',
            '<video width="320" height="240" controls>'
            '<source src="{}" type="video/webm">'
            'Ваш браузер не поддерживает видео.'
            '</video><br><small>{}</small>',
            ((resp.file.url, resp.uploaded_at.strftime("%Y-%m-%d %H:%M")) for resp in responses)
        )

    video_responses_list.short_description = "Видеоответы"


from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models import Max
# Сигнал для автоматической нумерации вопросов
@receiver(pre_save, sender=InterviewQuestion)
def set_question_order(sender, instance, **kwargs):
    # Получаем максимальный порядковый номер для текущего интервью
    if instance.pk is None:  # Только для новых вопросов
        max_order = InterviewQuestion.objects.filter(interview=instance.interview).aggregate(Max('question_order'))['question_order__max']
        instance.question_order = (max_order or 0) + 1  # Присваиваем максимальный порядковый номер + 1

class VacancyResponse(models.Model):
    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='responses', limit_choices_to={'role': 'applicant'}, verbose_name="Соискатель")
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='responses', verbose_name="Вакансия")
    responded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отклика")

    def __str__(self):
        try:
            return f"{self.applicant} откликнулся на вакансию {self.vacancy.title}"
        except Exception as e:
            return f"Ошибка: {e}"

    class Meta:
        verbose_name = "Отклик на вакансию"
        verbose_name_plural = "Отклики на вакансии"

class VideoResponse(models.Model):
    question = models.ForeignKey(
        'InterviewQuestion',
        on_delete=models.CASCADE,
        related_name='video_responses',
        verbose_name=_('Вопрос')
    )
    file = models.FileField(
        upload_to='interview_video_responses/',
        verbose_name=_('Файл видеоответа')
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата загрузки'))

    class Meta:
        verbose_name = _('Видеоответ')
        verbose_name_plural = _('Видеоответы')

    def __str__(self):
        return f'Ответ на вопрос {self.question.id} от {self.uploaded_at}'
