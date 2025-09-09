from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from .forms import EmployerRegistrationForm, ApplicantRegistrationForm, CustomAuthenticationForm, EditProfileForm, ProfileImageForm, VacancyForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import requests
from .models import Interview, Vacancy, VacancyResponse, CustomUser, VideoResponse

def register_employer(request):
    if request.method == 'POST':
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = EmployerRegistrationForm()
    return render(request, 'register_employer.html', {'form': form})

def register_applicant(request):
    if request.method == 'POST':
        form = ApplicantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = ApplicantRegistrationForm()
    return render(request, 'register_applicant.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "E-mail и/или пароль введены некорректно.")
        else:
            messages.error(request, "E-mail и/или пароль введены некорректно.")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'login.html', {'form': form})

def home(request):
    user = request.user

    interviews = []
    vacancies_count = 0
    responses_count = 0

    if user.is_authenticated:
        # Если соискатель — получаем интервью
        if user.role == 'applicant':
            interviews = Interview.objects.filter(applicant=user)

        # Если работодатель — считаем вакансии и отклики
        elif user.role == 'employer':
            vacancies = Vacancy.objects.filter(employer=user)
            vacancies_count = vacancies.count()
            responses_count = VacancyResponse.objects.filter(vacancy__employer=user).count()

    return render(request, 'home.html', {
        'interviews': interviews,
        'vacancies_count': vacancies_count,
        'responses_count': responses_count
    })

def blog(request):
    return render(request, 'blog.html')

def custom_404(request, exception=None):
    return render(request, '404_page.html', status=404)

'''
@login_required
def company_account(request):
    user = request.user
    vacancies = []
    responses = []
    existing_interviews = []

    if user.role == 'employer':
        vacancies = Vacancy.objects.filter(employer=user)
        responses = VacancyResponse.objects.filter(vacancy__in=vacancies).select_related('applicant', 'vacancy')

        # Находим уже созданные интервью
        existing_interviews = Interview.objects.filter(
            vacancy__in=vacancies
        ).values_list('applicant_id', 'vacancy_id')

    # Преобразуем в JSON-совместимый формат
    existing_interviews_json = json.dumps(list(existing_interviews))

    return render(request, 'company_account.html', {
        'vacancies': vacancies,
        'responses': responses,
        'existing_interviews_json': existing_interviews_json  # <-- передаем JSON напрямую
    })
'''
'''def company_account(request):
    user = request.user
    vacancies = []
    responses = []
    existing_interviews = []

    if user.role == 'employer':
        vacancies = Vacancy.objects.filter(employer=user)

        # Получаем отклики и подгружаем связанные интервью
        responses = VacancyResponse.objects.filter(
            vacancy__in=vacancies
        ).select_related('applicant', 'vacancy')

        interviews = Interview.objects.filter(
            vacancy__in=vacancies
        ).select_related('applicant', 'vacancy')

        # создаём словарь: (applicant_id, vacancy_id) -> interview
        interview_map = {
            (i.applicant_id, i.vacancy_id): i for i in interviews
        }

        # добавляем соответствующее интервью в каждый отклик
        for r in responses:
            r.interview = interview_map.get((r.applicant_id, r.vacancy_id))

        existing_interviews = interview_map.keys()

    existing_interviews_json = json.dumps(list(existing_interviews))

    return render(request, 'company_account.html', {
        'vacancies': vacancies,
        'responses': responses,
        'existing_interviews_json': existing_interviews_json
    })'''

def company_account(request):
    user = request.user
    vacancies = []
    responses = []
    existing_interviews = []

    if user.role == 'employer':
        vacancies = Vacancy.objects.filter(employer=user)

        # Получаем отклики и подгружаем связанные интервью
        responses = list(VacancyResponse.objects.filter(
            vacancy__in=vacancies
        ).select_related('applicant', 'vacancy'))

        interviews = Interview.objects.filter(
            vacancy__in=vacancies
        ).select_related('applicant', 'vacancy').prefetch_related('questions')

        # создаём словарь: (applicant_id, vacancy_id) -> interview
        interview_map = {
            (i.applicant_id, i.vacancy_id): i for i in interviews
        }

        # добавляем соответствующее интервью в каждый отклик
        for r in responses:
            r.interview = interview_map.get((r.applicant_id, r.vacancy_id))

        # --- СОРТИРУЕМ НА СТОРОНЕ PYTHON ---
        def get_match_percentage(response):
            # Если интервью нет или match_percentage не задан — ставим -1
            return response.interview.match_percentage if response.interview and response.interview.match_percentage is not None else -1

        # Сортировка: сначала с высоким %, потом с низким, в конце — без данных
        responses.sort(key=lambda r: get_match_percentage(r), reverse=True)

        existing_interviews = interview_map.keys()

    existing_interviews_json = json.dumps(list(existing_interviews))

    return render(request, 'company_account.html', {
        'vacancies': vacancies,
        'responses': responses,
        'existing_interviews_json': existing_interviews_json
    })

@login_required  
def person_account(request):
    # Получаем резюме текущего пользователя
    resume = Resume.objects.filter(user=request.user).first()  # Берём первое (или можно last() — по дате обновления)

    return render(request, 'person_account.html', {
        'resume': resume  # Передаём резюме в шаблон (None, если нет)
    })

@login_required
def page_company(request):
    # Основная форма
    form = EditProfileForm(request.POST or None, instance=request.user)

    # Форма для изменения изображения
    image_form = ProfileImageForm(request.POST or None, request.FILES or None)

    password_form = CustomPasswordChangeForm(user=request.user, data=request.POST or None)

    if request.method == 'POST':
        if request.POST.get('action') == 'save_changes':  # Сохранение основной формы
            if form.is_valid():
                form.save()
                messages.success(request, "Ваш профиль успешно обновлен.")
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
        elif request.POST.get('action') == 'change_password':
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Ваш пароль успешно изменен.")
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
        elif request.POST.get('action') == 'delete_image':  # Удаление изображения
            request.user.profile_image.delete(save=False)
            request.user.profile_image = None
            request.user.save()
            messages.success(request, "Фото профиля успешно удалено.")
        elif request.FILES.get('profile_image'):  # Сохранение изображения
            if image_form.is_valid():
                image_form.save(request.user)
                messages.success(request, "Фото профиля успешно обновлено.")
            else:
                messages.error(request, "Ошибка при загрузке изображения.")

        return redirect('page_company')

    return render(request, 'page_company.html', {'form': form, 'image_form': image_form, 'password_form': password_form})

from django.http import JsonResponse
@login_required
def delete_account(request):
    user = request.user
    user.delete()  # Удаляем пользователя из базы данных
    return JsonResponse({"success": True}, status=200)

from django.contrib.auth import update_session_auth_hash
from .forms import CustomPasswordChangeForm
@login_required
def page_person(request):
    # Основная форма
    form = EditProfileForm(request.POST or None, instance=request.user)

    # Форма для изменения изображения
    image_form = ProfileImageForm(request.POST or None, request.FILES or None)

    password_form = CustomPasswordChangeForm(user=request.user, data=request.POST or None)

    if request.method == 'POST':
        if request.POST.get('action') == 'save_changes':  # Сохранение основной формы
            if form.is_valid():
                form.save()
                messages.success(request, "Ваш профиль успешно обновлен.")
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
        elif request.POST.get('action') == 'change_password':
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Ваш пароль успешно изменен.")
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
        elif request.POST.get('action') == 'delete_image':  # Удаление изображения
            request.user.profile_image.delete(save=False)
            request.user.profile_image = None
            request.user.save()
            messages.success(request, "Фото профиля успешно удалено.")
        elif request.FILES.get('profile_image'):  # Сохранение изображения
            if image_form.is_valid():
                image_form.save(request.user)
                messages.success(request, "Фото профиля успешно обновлено.")
            else:
                messages.error(request, "Ошибка при загрузке изображения.")

        return redirect('page_person')

    return render(request, 'page_person.html', {'form': form, 'image_form': image_form, 'password_form': password_form})

def page_vacancy(request):
    return render(request, 'page_vacancy.html')

def page_resume(request):
    return render(request, 'page_resume.html')

def featured_jobs(request):
    return render(request, 'featured_jobs.html')

def person_notifications(request):
    user = request.user

    interviews = Interview.objects.filter(applicant=user).order_by('-created_at') if user.role == 'applicant' else []

    return render(request, 'person_notifications.html', {
        'interviews': interviews,
    })


def payment_person_history(request):
    return render(request, 'payment_person_history.html')

def company_notifications(request):
    return render(request, 'company_notifications.html')

def payment_company_history(request):
    return render(request, 'payment_company_history.html')

@login_required
def interview_applicant_main(request, unique_link):
    # Получаем интервью по уникальной ссылке
    interview = get_object_or_404(Interview, unique_link=unique_link)

    # Получаем все вопросы интервью
    questions = interview.questions.all().order_by('question_order')

    # Получаем вакансию, связанную с интервью
    vacancy = interview.vacancy

    resume = None
    if hasattr(interview, 'applicant') and interview.applicant:
        resume = Resume.objects.filter(user=interview.applicant).first()
        
    # Передаем данные в шаблон
    return render(
        request,
        'interview_applicant_main.html',
        {
            'interview': interview,
            'questions': questions,  # Передаем все вопросы в шаблон
            'vacancy': vacancy,
            'resume': resume,
        }
    )


from .models import InterviewQuestion
from django.views.decorators.csrf import csrf_exempt
import json
@csrf_exempt
def save_answer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transcribed_text = data.get('transcribed_text')
            question_id = data.get('question_id')

            if not transcribed_text or not question_id:
                return JsonResponse({'success': False, 'error': 'Отсутствуют данные'})

            # Получаем нужный вопрос по его ID
            question = get_object_or_404(InterviewQuestion, id=question_id)

            # Обновляем ответ только для этого вопроса
            question.text_answer = transcribed_text
            question.save()

            return JsonResponse({'success': True, 'message': 'Ответ сохранен'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Ошибка обработки JSON'})

    return JsonResponse({'success': False, 'error': 'Метод не разрешен'})



from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_time_posted(published_at: str) -> str:
    published_time = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%S")
    current_time = datetime.now()
    delta = relativedelta(current_time, published_time)

    # Функция для правильного склонения
    def get_correct_form(number, forms):
        if 11 <= number % 100 <= 19:
            return forms[2]  # форма для 5-20
        if number % 10 == 1:
            return forms[0]  # форма для 1
        if 2 <= number % 10 <= 4:
            return forms[1]  # форма для 2-4
        return forms[2]      # форма для остальных случаев

    if delta.years > 0:
        form = get_correct_form(delta.years, ["год", "года", "лет"])
        return f"{delta.years} {form} назад"
    if delta.months > 0:
        form = get_correct_form(delta.months, ["месяц", "месяца", "месяцев"])
        return f"{delta.months} {form} назад"
    if delta.days > 0:
        form = get_correct_form(delta.days, ["день", "дня", "дней"])
        return f"{delta.days} {form} назад"
    if delta.hours > 0:
        form = get_correct_form(delta.hours, ["час", "часа", "часов"])
        return f"{delta.hours} {form} назад"
    if delta.minutes > 0:
        form = get_correct_form(delta.minutes, ["минута", "минуты", "минут"])
        return f"{delta.minutes} {form} назад"
    if delta.seconds > 0:
        form = get_correct_form(delta.seconds, ["секунда", "секунды", "секунд"])
        return f"{delta.seconds} {form} назад"
    return "Только что"


from django.shortcuts import render
from .forms import SearchForm
import requests
import re

API_URL = "http://127.0.0.1:8001"  # Убедитесь, что здесь правильный порт

def process_salary(salary_from, salary_to, salary_currency):
    # Если хотя бы одно поле содержит "не указано"
    if "не указана" in (salary_from, salary_to, salary_currency):
        return "з/п не указана"

    # Если валюта "RUR", заменяем на символ рубля
    if salary_currency == "RUR":
        salary_currency = "₽"

    salary_text = ""
    if salary_from:
        salary_text += f"от {salary_from} "
    if salary_to:
        salary_text += f"до {salary_to} "
    if salary_currency:
        salary_text += f"{salary_currency}"

    return salary_text.strip()


def finder(request):
    all_vacancies = Vacancy.objects.all()

    responded_vacancy_ids = []
    if request.user.is_authenticated:
        responded_vacancy_ids = VacancyResponse.objects.filter(
            applicant=request.user
        ).values_list('vacancy_id', flat=True)

    return render(request, 'finder.html', {
        'all_vacancies': all_vacancies,
        'responded_vacancy_ids': list(responded_vacancy_ids)
    })


'''
def finder(request):
    form = SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data.get('query')
        salary_from = form.cleaned_data.get('salary_from')
        salary_to = form.cleaned_data.get('salary_to')

        # Определяем конечную точку API для поиска
        endpoint = f"{API_URL}/vacancies_search" if query else f"{API_URL}/vacancies"

        # Подготовка параметров запроса
        params = {'query': query} if query else {}

        if salary_from:
            try:
                salary_from = int(salary_from)
                params['salary_from'] = salary_from
            except ValueError:
                if salary_from.lower() != "з/п не указана":
                    params['salary_from'] = 0

        if salary_to:
            try:
                salary_to = int(salary_to)
                params['salary_to'] = salary_to
            except ValueError:
                if salary_to.lower() != "з/п не указана":
                    params['salary_to'] = 0

        # Отправляем запрос к API FastAPI
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()  # Проверяет, успешен ли запрос
            vacancies = response.json()

            # Проверяем, есть ли вакансии
            if not vacancies:
                return render(
                    request,
                    'finder.html',
                    {
                        'vacancies': [],
                        'message': "По вашему запросу ничего не найдено! <br> Попробуйте переформулировать запрос или изменить значения фильтров.",
                    }
                )

            # Формируем данные для отображения
            formatted_vacancies = [
                {
                    'title': vacancy['title'],
                    'keywords': re.sub(r'<.*?>', '', vacancy['keywords'] or ''),
                    'time_posted': calculate_time_posted(vacancy['published_at']),
                    'source': 'hh.ru',
                    'schedule': vacancy['employment_type'],
                    'company': vacancy['company'],
                    'location': vacancy['city'],
                    'skills': vacancy['skills'].split(', ') if vacancy['skills'] else [],
                    'salary': process_salary(vacancy['salary_from'], vacancy['salary_to'], vacancy['salary_currency']),
                    'url': vacancy['url']
                }
                for vacancy in vacancies
            ]

            return render(request, 'finder.html', {'vacancies': formatted_vacancies, 'message': None})

        except requests.RequestException:
            # Обрабатываем все ошибки API как отсутствие данных
            return render(
                request,
                'finder.html',
                {
                    'vacancies': [],
                    'message': "По вашему запросу ничего не найдено! <br> Попробуйте переформулировать запрос или изменить значения фильтров.",
                }
            )
    else:
        return render(
            request,
            'finder.html',
            {
                'vacancies': [],
                'message': "По вашему запросу ничего не найдено! <br> Попробуйте переформулировать запрос или изменить значения фильтров.",
            }
        )
'''


@login_required
def page_vacancy(request):
    if request.user.role != 'employer':  # Проверяем, что это работодатель
        messages.error(request, "Только работодатели могут добавлять вакансии.")
        return redirect('home')  # Перенаправляем на главную

    if request.method == 'POST':
        form = VacancyForm(request.POST)
        if form.is_valid():
            vacancy = form.save(commit=False)
            vacancy.employer = request.user  # Привязываем к текущему пользователю
            vacancy.save()
            messages.success(request, "Вакансия успешно отправлена на модерацию!")
            return redirect('page_vacancy')  # Перезагружаем страницу
    else:
        form = VacancyForm()

    return render(request, 'page_vacancy.html', {'form': form})


@login_required
def apply_for_vacancy(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)

    if request.method == 'POST' and request.user.role == 'applicant':
        try:
            '''
            # Проверка, что пользователь еще не откликался на эту вакансию
            if VacancyResponse.objects.filter(applicant=request.user, vacancy=vacancy).exists():
                return JsonResponse({'success': False, 'message': 'Вы уже откликнулись на эту вакансию'})
            '''

            # Создание отклика на вакансию
            VacancyResponse.objects.create(
                applicant=request.user,
                vacancy=vacancy
            )
            return JsonResponse({'success': True})
        except Exception as e:
            print(f"Error creating response: {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    else:
        print(f"Invalid request or user role: {request.method}, {request.user.role}")
        return JsonResponse({'success': False, 'message': 'Произошла ошибка'})

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from .models import Vacancy, CustomUser, Interview

'''
def create_interview(request):
    if request.method == 'POST':
        try:
            raw_body = request.body.decode('utf-8')
            print(f"Получен POST-запрос. Тело запроса: {raw_body}")

            try:
                data = json.loads(raw_body)
                print(f"Десериализованные данные: {data}")
            except json.JSONDecodeError as e:
                return JsonResponse({'status': 'error', 'message': 'Некорректный формат JSON'}, status=400)

            vacancy_title = data.get('vacancy_title')
            vacancy_skills = data.get('vacancy_skills')
            vacancy_company = data.get('vacancy_company')
            applicant_name = data.get('applicant_name')
            applicant_last_name = data.get('applicant_last_name')

            # Проверка обязательных полей
            required_fields = [
                vacancy_title, vacancy_skills, vacancy_company,
                applicant_name, applicant_last_name
            ]
            if not all(required_fields):
                missing_fields = [
                    field for field in ['vacancy_title', 'vacancy_skills', 'vacancy_company',
                                        'applicant_name', 'applicant_last_name']
                    if not data.get(field)
                ]
                return JsonResponse(
                    {'status': 'error', 'message': f'Отсутствуют обязательные поля: {missing_fields}'},
                    status=400
                )

            # Найти вакансию (без создания)
            try:
                vacancy = Vacancy.objects.get(
                    title=vacancy_title,
                    employer__company_name=vacancy_company,
                    #skills=vacancy_skills
                )
                print(f"Вакансия найдена: {vacancy}")
            except Vacancy.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Вакансия не найдена'}, status=404)

            # Найти пользователя (соискателя)
            try:
                user = CustomUser.objects.get(
                    first_name=applicant_name,
                    last_name=applicant_last_name,
                    role='applicant'
                )
                print(f"Соискатель найден: {user}")
            except CustomUser.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Соискатель не найден'}, status=404)

            # Проверка: есть ли уже такое интервью
            interview_exists = Interview.objects.filter(applicant=user, vacancy=vacancy).exists()
            if interview_exists:
                return JsonResponse({'status': 'error', 'message': 'Интервью уже существует'}, status=400)

            # Создание интервью
            interview = Interview.objects.create(
                applicant=user,
                vacancy=vacancy
            )
            print(f"Интервью создано: {interview}")

            return JsonResponse({
                'status': 'success',
                'message': 'Интервью успешно создано!',
                'interview_id': interview.id
            })

        except Exception as e:
            print(f"Ошибка: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'}, status=405)
'''
'''
import requests
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
import os
from urllib.parse import urlparse
from django.conf import settings


def create_interview(request):
    if request.method == 'POST':
        try:
            raw_body = request.body.decode('utf-8')
            print(f"Получен POST-запрос. Тело запроса: {raw_body}")

            try:
                data = json.loads(raw_body)
                print(f"Десериализованные данные: {data}")
            except json.JSONDecodeError as e:
                return JsonResponse({'status': 'error', 'message': 'Некорректный формат JSON'}, status=400)

            vacancy_title = data.get('vacancy_title')
            vacancy_skills = data.get('vacancy_skills')
            vacancy_company = data.get('vacancy_company')
            applicant_name = data.get('applicant_name')
            applicant_last_name = data.get('applicant_last_name')

            # Проверка обязательных полей
            required_fields = [
                vacancy_title, vacancy_skills, vacancy_company,
                applicant_name, applicant_last_name
            ]
            if not all(required_fields):
                missing_fields = [
                    field for field in ['vacancy_title', 'vacancy_skills', 'vacancy_company',
                                        'applicant_name', 'applicant_last_name']
                    if not data.get(field)
                ]
                return JsonResponse(
                    {'status': 'error', 'message': f'Отсутствуют обязательные поля: {missing_fields}'},
                    status=400
                )

            # Найти вакансию (без создания)
            try:
                vacancy = Vacancy.objects.get(
                    title=vacancy_title,
                    employer__company_name=vacancy_company,
                )
                print(f"Вакансия найдена: {vacancy}")
            except Vacancy.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Вакансия не найдена'}, status=404)

            # Найти пользователя (соискателя)
            try:
                user = CustomUser.objects.get(
                    first_name=applicant_name,
                    last_name=applicant_last_name,
                    role='applicant'
                )
                print(f"Соискатель найден: {user}")
            except CustomUser.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Соискатель не найден'}, status=404)

            # Проверка: есть ли уже такое интервью
            interview_exists = Interview.objects.filter(applicant=user, vacancy=vacancy).exists()
            if interview_exists:
                return JsonResponse({'status': 'error', 'message': 'Интервью уже существует'}, status=400)

            # Создание интервью
            interview = Interview.objects.create(
                applicant=user,
                vacancy=vacancy
            )
            print(f"Интервью создано: {interview}")

            # Скачивание видео по ссылке и сохранение в модель InterviewQuestion
            interview_result = data.get('interview_result', {})
            questions_data = interview_result.get('original_questions', [])
            video_links = interview_result.get('video_files', [])

            for idx, question_text in enumerate(questions_data):
                video_url = video_links[idx] if idx < len(video_links) else None

                if video_url:
                    try:
                        # Скачивание видео с URL
                        video_content = requests.get(video_url)
                        video_content.raise_for_status()  # Проверяем, что запрос успешен

                        # Сохраняем файл в модель
                        video_name = os.path.basename(urlparse(video_url).path)  # Извлекаем имя файла из URL
                        video_file = ContentFile(video_content.content, name=video_name)

                        # Создаем вопрос с видео
                        InterviewQuestion.objects.create(
                            interview=interview,
                            text=question_text,
                            video=video_file,
                            question_order=idx
                        )
                    except requests.exceptions.RequestException as e:
                        print(f"Ошибка при скачивании видео с {video_url}: {e}")
                        return JsonResponse({'status': 'error', 'message': f'Не удалось скачать видео с {video_url}'},
                                            status=500)

                else:
                    # Если видео нет, просто сохраняем вопрос без видео
                    InterviewQuestion.objects.create(
                        interview=interview,
                        text=question_text,
                        question_order=idx
                    )

            return JsonResponse({
                'status': 'success',
                'message': 'Интервью успешно создано!',
                'interview_id': interview.id
            })

        except Exception as e:
            print(f"Ошибка: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'}, status=405)
'''


import requests
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
import os
from urllib.parse import urlparse
from django.conf import settings
import base64
import uuid

def create_interview(request):
    if request.method == 'POST':
        try:
            raw_body = request.body.decode('utf-8')
            print(f"Получен POST-запрос. Тело запроса: {raw_body}")

            try:
                data = json.loads(raw_body)
                print(f"Десериализованные данные: {data}")
            except json.JSONDecodeError as e:
                return JsonResponse({'status': 'error', 'message': 'Некорректный формат JSON'}, status=400)

            vacancy_title = data.get('vacancy_title')
            vacancy_skills = data.get('vacancy_skills')
            vacancy_company = data.get('vacancy_company')
            applicant_name = data.get('applicant_name')
            applicant_last_name = data.get('applicant_last_name')
            hr_photo_base64 = data.get('image')

            # Проверка обязательных полей
            required_fields = [
                vacancy_title, vacancy_skills, vacancy_company,
                applicant_name, applicant_last_name
            ]
            if not all(required_fields):
                missing_fields = [
                    field for field in ['vacancy_title', 'vacancy_skills', 'vacancy_company',
                                        'applicant_name', 'applicant_last_name']
                    if not data.get(field)
                ]
                return JsonResponse(
                    {'status': 'error', 'message': f'Отсутствуют обязательные поля: {missing_fields}'},
                    status=400
                )

            # Найти вакансию (без создания)
            try:
                vacancy = Vacancy.objects.get(
                    title=vacancy_title,
                    employer__company_name=vacancy_company,
                )
                print(f"Вакансия найдена: {vacancy}")
            except Vacancy.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Вакансия не найдена'}, status=404)

            # Найти пользователя (соискателя)
            try:
                user = CustomUser.objects.get(
                    first_name=applicant_name,
                    last_name=applicant_last_name,
                    role='applicant'
                )
                print(f"Соискатель найден: {user}")
            except CustomUser.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Соискатель не найден'}, status=404)

            # Проверка: есть ли уже такое интервью
            interview_exists = Interview.objects.filter(applicant=user, vacancy=vacancy).exists()
            if interview_exists:
                return JsonResponse({'status': 'error', 'message': 'Интервью уже существует'}, status=400)

            # Создание интервью
            interview = Interview.objects.create(
                applicant=user,
                vacancy=vacancy,
                gender=data.get('gender'),
                hr_name=data.get('agent_name')
            )
            print(f"Интервью создано: {interview}")
            
             # Сохраняем фото, если есть
            if hr_photo_base64 and hr_photo_base64.startswith("data:image"):
                format, imgstr = hr_photo_base64.split(';base64,')  
                ext = format.split('/')[-1]  
                file_name = f"{uuid.uuid4()}.{ext}"
                interview.hr_photo = ContentFile(base64.b64decode(imgstr), name=file_name)
                interview.save()

            # Скачивание видео по ссылке и сохранение в модель InterviewQuestion
            interview_result = data.get('interview_result', {})
            questions_data = interview_result.get('original_questions', {})
            video_links = interview_result.get('video_files', [])

            for idx, (question_id, question_text) in enumerate(questions_data.items()):
                video_url = video_links[idx] if idx < len(video_links) else None

                if video_url:
                    try:
                        # Скачивание видео с URL
                        video_content = requests.get(video_url)
                        video_content.raise_for_status()  # Проверяем, что запрос успешен

                        # Сохраняем файл в модель
                        video_name = os.path.basename(urlparse(video_url).path)  # Извлекаем имя файла из URL
                        video_file = ContentFile(video_content.content, name=video_name)

                        # Создаем вопрос с видео
                        InterviewQuestion.objects.create(
                            interview=interview,
                            text=question_text,
                            video=video_file,
                            question_order=idx
                        )
                    except requests.exceptions.RequestException as e:
                        print(f"Ошибка при скачивании видео с {video_url}: {e}")
                        return JsonResponse({'status': 'error', 'message': f'Не удалось скачать видео с {video_url}'},
                                            status=500)

                else:
                    # Если видео нет, просто сохраняем вопрос без видео
                    InterviewQuestion.objects.create(
                        interview=interview,
                        text=question_text,
                        question_order=idx
                    )

            return JsonResponse({
                'status': 'success',
                'message': 'Интервью успешно создано!',
                'interview_id': interview.id
            })

        except Exception as e:
            print(f"Ошибка: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'}, status=405)

@csrf_exempt
def update_interview_match(request):
    if request.method != "POST":
        return JsonResponse({"error": "Метод не поддерживается"}, status=405)

    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")
        percentage = data.get("percentage")
        conversation_log = data.get("conversation_log", [])
        summary = data.get("summary", "")
        if not session_id or percentage is None:
            return JsonResponse({"error": "Недостающие параметры"}, status=400)

        interview = Interview.objects.get(unique_link=session_id)
        interview.match_percentage = float(percentage)
        interview.summary = summary
        interview.save()

        # ---- Разбор лога на вопросы и ответы ----
        questions = []
        answers = []

        for line in conversation_log:
            if line.startswith("Бот:"):
                questions.append(line[5:].strip())
            elif line.startswith("Пользователь:"):
                answers.append(line[13:].strip())

        # ---- Первый ответ сохраняем в существующий первый вопрос ----
        existing_questions = list(interview.questions.all().order_by('question_order'))

        if existing_questions:
            first_question = existing_questions[0]
            if answers:
                first_question.text_answer = answers[0]  # Сохраняем первый ответ
                first_question.save()
            answers = answers[1:]  # Оставшиеся ответы начиная со второго
        else:
            # Если первого вопроса нет — создаём его (но без текста вопроса)
            InterviewQuestion.objects.create(
                interview=interview,
                text="",  # или оставить пустым
                text_answer=answers[0] if answers else "",
                question_order=1
            )
            answers = answers[1:]

        # ---- Сохранение остальных пар вопрос-ответ ----
        for i, answer in enumerate(answers):
            order = i + 2  # Начинаем с 2
            question_idx = i

            if question_idx < len(questions):
                question_text = questions[question_idx]
            else:
                question_text = ""

            InterviewQuestion.objects.update_or_create(
                interview=interview,
                question_order=order,
                defaults={
                    'text': question_text,
                    'text_answer': answer,
                }
            )

        return JsonResponse({"success": True})

    except Interview.DoesNotExist:
        return JsonResponse({"error": "Интервью не найдено"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def save_interview_video_response(request):
    if request.method == 'POST' and request.FILES.get('video_response'):
        video_file = request.FILES['video_response']
        question_id = request.POST.get('question_id')

        if not question_id:
            return JsonResponse({'success': False, 'message': 'ID вопроса не передан'})

        try:
            question = InterviewQuestion.objects.get(id=int(question_id))
        except (InterviewQuestion.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Вопрос не найден'})

        # Создаём новый VideoResponse
        video_response = VideoResponse.objects.create(question=question, file=video_file)

        return JsonResponse({
            'success': True,
            'file_path': video_response.file.url
        })

    return JsonResponse({'success': False, 'message': 'Нет данных'})

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from django.core.serializers.json import DjangoJSONEncoder
import json

import re





@require_http_methods(["GET"])
@login_required
def get_interview_details(request, interview_id):
    interview = get_object_or_404(
        Interview.objects.prefetch_related('questions__video_responses'),
        id=interview_id,
        vacancy__employer=request.user
    )

    questions = list(interview.questions.all().order_by('question_order'))

    if not questions:
        return JsonResponse({'questions': []})

    # Собираем все видеоответы всех вопросов
    all_video_responses = []
    for q in questions:
        all_video_responses.extend(list(q.video_responses.all()))

    # Удаляем последнее видео, если общее число видео > числу вопросов
    if len(all_video_responses) > len(questions):
        all_video_responses.pop()  # убираем последнее видео

    # Распределяем видео по вопросам циклически
    distributed_videos = {i: [] for i in range(len(questions))}
    for idx, video in enumerate(all_video_responses):
        question_index = idx % len(questions)
        distributed_videos[question_index].append(video)

    seen = set()
    data = []

    for i, q in enumerate(questions):
        key = f"{q.text.strip()}||{q.text_answer or ''}"
        if key in seen:
            continue
        seen.add(key)

        # Получаем видео для текущего вопроса
        videos_for_question = distributed_videos.get(i, [])
        video_urls = [vid.file.url for vid in videos_for_question]

        data.append({
            'text': q.text,
            'text_answer': q.text_answer or '',
            'videos': video_urls,
        })

    formatted_summary = interview.summary if hasattr(interview, 'summary') else ''

    return JsonResponse({'summary': formatted_summary, 'questions': data}, encoder=DjangoJSONEncoder)


from .models import Resume
@csrf_exempt
@login_required
def save_resume(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Только POST-запросы разрешены'}, status=405)

    try:
        data = json.loads(request.body)

        specialization = data.get('specialization', '')
        key_skills = data.get('key_skills', [])
        key_responsibilities = data.get('key_responsibilities', [])
        work_experience = data.get('work_experience', [])
        general_experience_number = data.get('general_experience_number', [''])[0]  # первый элемент

        resume, created = Resume.objects.update_or_create(
            user=request.user,
            defaults={
                'specialization': specialization,
                'key_skills': key_skills,
                'key_responsibilities': key_responsibilities,
                'work_experience': work_experience,
                'general_experience_number': general_experience_number,
            }
        )

        status = "создано" if created else "обновлено"
        return JsonResponse({
            'status': 'success',
            'message': f'Резюме успешно {status}',
            'resume_id': resume.id
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Некорректный JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)