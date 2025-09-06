from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, PasswordChangeForm
from .models import CustomUser, Vacancy
from django.contrib.auth.models import User

class EmployerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label='Имя')
    last_name = forms.CharField(max_length=30, required=True, label='Фамилия')
    phone = forms.CharField(max_length=15, required=True, label='Телефон')
    city = forms.CharField(max_length=50, required=True, label='Город')
    company_name = forms.CharField(max_length=100, required=True, label='Название компании')
    agree_to_terms = forms.BooleanField(required=True, label='Соглашаюсь с правилами использования платформы IT-WorkRu и политикой конфиденциальности IT-WorkRu')
    agree_to_data_processing = forms.BooleanField(required=True, label='Я согласен на обработку персональных данных')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone', 'city', 'company_name', 'password1', 'password2', 'agree_to_terms', 'agree_to_data_processing')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'employer'
        user.phone = self.cleaned_data.get('phone')
        user.city = self.cleaned_data.get('city')
        user.company_name = self.cleaned_data.get('company_name')
        if commit:
            user.save()
        return user

class ApplicantRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label='Имя')
    last_name = forms.CharField(max_length=30, required=True, label='Фамилия')
    agree_to_terms = forms.BooleanField(required=True, label='Соглашаюсь с правилами использования платформы IT-WorkRu и политикой конфиденциальности IT-WorkRu')
    agree_to_data_processing = forms.BooleanField(required=True, label='Я согласен на обработку персональных данных')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2', 'agree_to_terms', 'agree_to_data_processing')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'applicant'
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email')  # Изменяем поле username на email

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form__person-input', 'placeholder': 'Пароль'}),
        label="Пароль",
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form__person-input', 'placeholder': 'Новый пароль'}),
        label="Новый пароль",
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form__person-input', 'placeholder': 'Повторите пароль'}),
        label="Повторите пароль",
    )

    class Meta:
        model = User
        fields = ('old_password', 'new_password1', 'new_password2')

class EditProfileForm(UserChangeForm):
    city = forms.CharField(max_length=50, required=False, label='Город')
    first_name = forms.CharField(max_length=30, required=False, label='Имя')
    last_name = forms.CharField(max_length=30, required=False, label='Фамилия')
    middle_name = forms.CharField(max_length=30, required=False, label='Отчество')
    birth_date = forms.DateField(required=False, label='Дата рождения', widget=forms.DateInput(attrs={'type': 'date'}))
    phone = forms.CharField(max_length=15, required=False, label='Телефон')
    address = forms.CharField(max_length=255, required=False, label='Адрес')
    citizenship = forms.CharField(max_length=50, required=False, label='Гражданство')
    postal_code = forms.CharField(max_length=10, required=False, label='Индекс')
    inn = forms.CharField(max_length=50, required=False, label='ИНН')
    ogr = forms.CharField(max_length=50, required=False, label='ОГРН/ОГРНИП')
    kpp = forms.CharField(max_length=50, required=False, label='КПП')
    site_link = forms.CharField(max_length=200, required=False, label='Сайт компании')
    company_email = forms.EmailField(required=False, label='E-mail компании')
    vk_link = forms.CharField(max_length=200, required=False, label='ВКонтакте')
    ok_link = forms.CharField(max_length=200, required=False, label='Одноклассники')
    telegram_link = forms.CharField(max_length=200, required=False, label='Telegram')
    whatsapp_link = forms.CharField(max_length=200, required=False, label='WhatsApp')
    skype_link = forms.CharField(max_length=200, required=False, label='Skype')
    desc = forms.CharField(
        widget=forms.Textarea(attrs={
            'id': 'editor',
            'class': 'form__person-input',
            'style': 'height: 200px; font-family: Arial, sans-serif !important; font-size: var(--fz-m) !important;',
        }), required=False, label='Описание компании'
    )
    telephone_show = forms.BooleanField(required=False, label="Отображать номер телефона в резюме")
    social_network_show = forms.BooleanField(required=False,
                                             label="Отображать ссылки на профили социальных сетей в резюме")

    # Добавляем поле для выбора пола
    gender = forms.ChoiceField(
        choices=[('M', 'Мужской'), ('F', 'Женский')],
        required=False,
        label='Пол'
    )

    work_status = forms.ChoiceField(
        choices=[('S', 'В поиске работы'), ('N', 'Не ищу работу')],
        required=False,
        label='Статус на сайте'
    )

    class Meta:
        model = CustomUser
        fields = ('city', 'first_name', 'last_name', 'middle_name', 'birth_date', 'phone', 'address', 'citizenship',
                  'postal_code', 'vk_link', 'ok_link', 'telegram_link', 'whatsapp_link', 'skype_link', 'gender', 'work_status', 'telephone_show', 'social_network_show', 'inn', 'ogr', 'kpp', 'site_link', 'company_email', 'desc')

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('first_name'):
            user.first_name = self.cleaned_data['first_name']
        if self.cleaned_data.get('last_name'):
            user.last_name = self.cleaned_data['last_name']
        if self.cleaned_data.get('middle_name'):
            user.middle_name = self.cleaned_data['middle_name']
        if self.cleaned_data.get('city'):
            user.city = self.cleaned_data['city']
        if self.cleaned_data.get('birth_date'):
            user.birth_date = self.cleaned_data['birth_date']
        if self.cleaned_data.get('phone'):
            user.phone = self.cleaned_data['phone']
        if self.cleaned_data.get('address'):
            user.address = self.cleaned_data['address']
        if self.cleaned_data.get('citizenship'):
            user.citizenship = self.cleaned_data['citizenship']
        if self.cleaned_data.get('postal_code'):
            user.postal_code = self.cleaned_data['postal_code']
        if self.cleaned_data.get('inn'):
            user.inn = self.cleaned_data['inn']
        if self.cleaned_data.get('ogr'):
            user.ogr = self.cleaned_data['ogr']
        if self.cleaned_data.get('kpp'):
            user.kpp = self.cleaned_data['kpp']
        if self.cleaned_data.get('desc'):
            user.desc = self.cleaned_data['desc']
        if self.cleaned_data.get('site_link'):
            user.site_link = self.cleaned_data['site_link']
        if self.cleaned_data.get('company_email'):
            user.company_email = self.cleaned_data['company_email']
        if self.cleaned_data.get('vk_link'):
            user.vk_link = self.cleaned_data['vk_link']
        if self.cleaned_data.get('ok_link'):
            user.ok_link = self.cleaned_data['ok_link']
        if self.cleaned_data.get('telegram_link'):
            user.telegram_link = self.cleaned_data['telegram_link']
        if self.cleaned_data.get('whatsapp_link'):
            user.whatsapp_link = self.cleaned_data['whatsapp_link']
        if self.cleaned_data.get('skype_link'):
            user.skype_link = self.cleaned_data['skype_link']
        if self.cleaned_data.get('gender'):
            user.gender = self.cleaned_data['gender']
        if self.cleaned_data.get('work_status'):
            user.work_status = self.cleaned_data['work_status']
        if self.cleaned_data.get('telephone_show') is not None:
            user.telephone_show = self.cleaned_data['telephone_show']
        if self.cleaned_data.get('social_network_show') is not None:
            user.social_network_show = self.cleaned_data['social_network_show']
        if commit:
            user.save()
        return user

class ProfileImageForm(forms.Form):
    profile_image = forms.ImageField(required=False, label='Фото профиля')

    def save(self, user):
        if 'profile_image' in self.cleaned_data:
            user.profile_image = self.cleaned_data['profile_image']
            user.save()

class SearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Специальность, должность или компания',
            'class': 'search-input'
        })
    )
    salary_from = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'От',
            'class': 'salary-input'
        })
    )
    salary_to = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'До',
            'class': 'salary-input'
        })
    )

class VacancyForm(forms.ModelForm):
    # Определяем варианты для чекбоксов.
    LEVEL_CHOICES = [
        ('Junior', 'Junior'),
        ('Middle', 'Middle'),
        ('Senior', 'Senior'),
    ]

    # Поле, которое по умолчанию будет отрисовано в виде набора чекбоксов.
    levels = forms.MultipleChoiceField(
        choices=LEVEL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Уровни'
    )

    desc_1 = forms.CharField(
        widget=forms.Textarea(attrs={
            'id': 'editor_1',
            'class': 'form__person-input',
            'style': 'height: 200px; font-family: Arial, sans-serif !important; font-size: var(--fz-m) !important;',
        }), required=False, label='Описание вакансии'
    )

    desc_2 = forms.CharField(
        widget=forms.Textarea(attrs={
            'id': 'editor_2',
            'class': 'form__person-input',
            'style': 'height: 200px; font-family: Arial, sans-serif !important; font-size: var(--fz-m) !important;',
        }), required=False, label='Описание тестового задания'
    )

    city_1 = forms.CharField(max_length=50, required=False, label='Город')
    address_1 = forms.CharField(max_length=255, required=False, label='Адрес')
    postal_code_1 = forms.CharField(max_length=10, required=False, label='Индекс')
    salary_from_1 = forms.CharField(max_length=7, required=False, label='Зарплата от')
    salary_to_1 = forms.CharField(max_length=7, required=False, label='Зарплата до')
    employment_hidden = forms.CharField(max_length=255, required=False, label='Тип занятости')
    work_hidden = forms.CharField(max_length=255, required=False, label='График работы')
    specialization_hidden = forms.CharField(max_length=255, required=False, label='Специализация')
    languages_hidden = forms.CharField(max_length=255, required=False, label='Владение языками')
    education_hidden = forms.CharField(max_length=255, required=False, label='Уровень образования')
    relocation = forms.BooleanField(
        required=False,
        label="Релокейт соискателя"
    )
    resume_required = forms.BooleanField(
        required=False,
        label="Обязательно наличие резюме"
    )

    exp = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[
            (0, "Нет опыта"),
            (1, "От 1 до 3 лет"),
            (2, "От 3 до 6 лет"),
            (3, "Более 6")
        ],
        required=True,
        label='Опыт работы'
    )

    money = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[
            (1, "На руки"),
            (0, "До вычета налогов")
        ],
        required=False,
        initial=1,
        label='Тип зарплаты'
    )

    skills_hidden = forms.CharField(
        max_length=255,
        required=False,
        label='Ключевые навыки',
        #widget=forms.HiddenInput(attrs={'id': 'skills_input'})
        widget=forms.TextInput(attrs={'id': 'skills_input'})
    )

    CURRENCY_CHOICES = [
        ('RUB', '₽'),
        ('USD', '$'),
        ('EUR', '€'),
        ('CNY', '¥'),
    ]

    currency_1 = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form__person-input'}),
        required=False,
        label='Валюта зарплаты'
    )

    class Meta:
        model = Vacancy
        # Не забываем добавить поле 'levels'
        fields = ['title', 'levels', 'desc_1', 'desc_2', 'city_1', 'address_1', 'postal_code_1', 'employment_hidden', 'work_hidden', 'specialization_hidden', 'languages_hidden', 'education_hidden', 'resume_required', 'relocation', 'exp', 'money', 'skills_hidden', 'salary_from_1', 'salary_to_1', 'currency_1']

    def __init__(self, *args, **kwargs):
        super(VacancyForm, self).__init__(*args, **kwargs)
        # Если объект уже существует и в нем сохранены уровни,
        # задаем начальное значение для поля levels в виде списка.
        if self.instance and self.instance.levels:
            self.initial['levels'] = self.instance.levels.split(',')

    def clean_levels(self):
        """
        Если в POST-данных присутствует 'levels_hidden', используем его,
        иначе — стандартное значение из поля levels.
        Проверяем корректность выбранных значений и сохраняем их как строку.
        """
        # Попытка получить данные из скрытого поля.
        data_hidden = self.data.get('levels_hidden')
        if data_hidden is not None:
            # Если скрытый инпут присутствует, работаем с его содержимым
            data_list = data_hidden.split(',') if data_hidden.strip() else []
        else:
            # Иначе используем данные, прошедшие валидацию через стандартный виджет
            data_list = self.cleaned_data.get('levels')
            if isinstance(data_list, str):
                data_list = data_list.split(',') if data_list.strip() else []

        # Проверяем, что все выбранные значения допустимы
        valid_choices = [choice[0] for choice in self.LEVEL_CHOICES]
        for val in data_list:
            if val not in valid_choices:
                raise forms.ValidationError(f"Некорректное значение: {val}")

        # Сохраняем выбранные уровни как строку с разделителем запятая.
        return ",".join(data_list) if data_list else ""

    def clean_currency_1(self):
        currency = self.cleaned_data.get('currency_1')
        return currency if currency else 'RUB'