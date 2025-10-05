from django.test import TestCase
from django.contrib.auth import get_user_model
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
from main_app.forms import (
    EmployerRegistrationForm,
    ApplicantRegistrationForm,
    CustomAuthenticationForm,
    CustomPasswordChangeForm,
    EditProfileForm,
    ProfileImageForm,
    SearchForm,
    VacancyForm
)
from main_app.models import Vacancy

User = get_user_model()


class EmployerRegistrationFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'email': 'ivan@example.com',
            'phone': '+79999999999',
            'city': 'Москва',
            'company_name': 'ООО Тест',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'agree_to_terms': True,
            'agree_to_data_processing': True,
        }

    def test_valid_form(self):
        form = EmployerRegistrationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_email(self):
        data = self.valid_data.copy()
        data.pop('email')
        form = EmployerRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_mismatch(self):
        data = self.valid_data.copy()
        data['password2'] = 'Different123!'
        form = EmployerRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_save_assigns_role_employer(self):
        form = EmployerRegistrationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, 'employer')
        self.assertEqual(user.company_name, 'ООО Тест')


class ApplicantRegistrationFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            'first_name': 'Петр',
            'last_name': 'Петров',
            'email': 'petr@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'agree_to_terms': True,
            'agree_to_data_processing': True,
        }

    def test_valid_form(self):
        form = ApplicantRegistrationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_invalid_missing_email(self):
        data = self.valid_data.copy()
        data.pop('email')
        form = ApplicantRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_save_assigns_role_applicant(self):
        form = ApplicantRegistrationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, 'applicant')


class CustomAuthenticationFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='login@example.com', password='StrongPass123!'
        )

    def test_valid_login(self):
        form = CustomAuthenticationForm(data={
            'username': 'login@example.com',
            'password': 'StrongPass123!'
        })
        self.assertTrue(form.is_valid())

    def test_invalid_password(self):
        form = CustomAuthenticationForm(data={
            'username': 'login@example.com',
            'password': 'WrongPassword'
        })
        self.assertFalse(form.is_valid())


class CustomPasswordChangeFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com', password='OldPass123!'
        )

    def test_valid_password_change(self):
        form = CustomPasswordChangeForm(user=self.user, data={
            'old_password': 'OldPass123!',
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.check_password('NewPass456!'))

    def test_invalid_old_password(self):
        form = CustomPasswordChangeForm(user=self.user, data={
            'old_password': 'WrongOldPass!',
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('old_password', form.errors)


class EditProfileFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='edit@example.com', password='Pass123!'
        )

    def test_valid_edit(self):
        form = EditProfileForm(data={
            'first_name': 'Анна',
            'city': 'Санкт-Петербург',
            'phone': '+79998887766',
            'gender': 'F',
            'work_status': 'S'
        }, instance=self.user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()
        self.assertEqual(updated_user.first_name, 'Анна')
        self.assertEqual(updated_user.city, 'Санкт-Петербург')

    def test_invalid_email_field(self):
        form = EditProfileForm(data={'company_email': 'not-email'}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('company_email', form.errors)


class ProfileImageFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='img@example.com', password='Test123!'
        )

    def test_upload_image(self):
        # Создаем изображение в памяти
        image = BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(image, format='JPEG')
        image.seek(0)

        uploaded_image = InMemoryUploadedFile(
            image,
            field_name='profile_image',
            name='test_image.jpg',
            content_type='image/jpeg',
            size=image.getbuffer().nbytes,
            charset=None
        )

        form = ProfileImageForm(data={}, files={'profile_image': uploaded_image})
        self.assertTrue(form.is_valid())
        form.save(self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_image)


class SearchFormTest(TestCase):
    def test_valid_search(self):
        form = SearchForm(data={'query': 'Python', 'salary_from': '50000', 'salary_to': '100000'})
        self.assertTrue(form.is_valid())

    def test_empty_search(self):
        form = SearchForm(data={})
        self.assertTrue(form.is_valid())


class VacancyFormTest(TestCase):
    def setUp(self):
        self.valid_data = {
            'title': 'Python Developer',
            'levels': ['Junior', 'Middle'],
            'desc_1': 'Описание вакансии',
            'desc_2': 'Описание тестового задания',
            'city_1': 'Москва',
            'exp': 1,
            'money': 1,
            'currency_1': 'RUB'
        }

    def test_valid_form(self):
        form = VacancyForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_invalid_levels(self):
        data = self.valid_data.copy()
        data['levels'] = ['FakeLevel']
        form = VacancyForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('levels', form.errors)

    def test_default_currency(self):
        data = self.valid_data.copy()
        data.pop('currency_1')
        form = VacancyForm(data=data)
        form.is_valid()
        self.assertEqual(form.cleaned_data.get('currency_1'), 'RUB')
