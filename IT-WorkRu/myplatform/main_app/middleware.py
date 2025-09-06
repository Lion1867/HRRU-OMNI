from django.shortcuts import redirect
from django.urls import reverse


class BlockAuthenticatedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Получаем unique_link из URL
        path_parts = request.path.split('/')
        if len(path_parts) > 2:  # Проверка на наличие unique_link в URL
            unique_link = path_parts[-2]

            # Список страниц, требующих авторизации
            restricted_pages = [
                reverse('company_account'),
                reverse('page_company'),
                reverse('page_vacancy'),
                reverse('person_account'),
                reverse('page_person'),
                reverse('page_resume'),
                reverse('featured_jobs'),
                reverse('person_notifications'),
                reverse('payment_person_history'),
                reverse('company_notifications'),
                reverse('payment_company_history'),
                reverse('interview_applicant_main', args=[unique_link]),
            ]

            # Проверяем, авторизован ли пользователь
            if not request.user.is_authenticated and request.path in restricted_pages:
                return redirect('login')  # Перенаправляем на страницу входа

            if request.user.is_authenticated:
                # Условия для работодателя
                employer_restricted_pages = [
                    reverse('company_account'),
                    reverse('page_company'),
                    reverse('page_vacancy'),
                    reverse('company_notifications'),
                    reverse('payment_company_history'),
                ]
                if request.user.role != 'employer' and request.path in employer_restricted_pages:
                    return redirect('home')  # Перенаправляем на главную страницу

                # Условия для соискателя
                applicant_restricted_pages = [
                    reverse('person_account'),
                    reverse('page_person'),
                    reverse('page_resume'),
                    reverse('featured_jobs'),
                    reverse('person_notifications'),
                    reverse('payment_person_history'),
                    reverse('interview_applicant_main', args=[unique_link]),
                ]
                if request.user.role != 'applicant' and request.path in applicant_restricted_pages:
                    return redirect('home')  # Перенаправляем на главную страницу

                # Условия для предотвращения доступа к страницам регистрации и входа
                restricted_auth_pages = [
                    reverse('login'),
                    reverse('register_employer'),
                    reverse('register_applicant'),
                ]
                if request.path in restricted_auth_pages:
                    return redirect('home')  # Перенаправляем на главную страницу

        response = self.get_response(request)
        return response
