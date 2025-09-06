from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Vacancy, Interview, InterviewQuestion, InterviewQuestionInline, VacancyResponse, VideoResponse
from .forms import VacancyForm

class VacancyInline(admin.TabularInline):
    model = Vacancy
    extra = 1  # Количество пустых полей для добавления новых вакансий

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Поля, которые будут отображаться в списке пользователей, включая роль
    list_display = ('email', 'role', 'is_active', 'is_staff')

    # Поля для поиска
    search_fields = ('email', 'first_name', 'last_name', 'role')
    list_filter = ('is_active', 'is_staff', 'role')

    # Поля для отображения при редактировании пользователя
    fieldsets = (
        (None, {'fields': ('email', 'password', 'first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    # Настройка отображаемых полей на основе роли
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            if obj.role == 'employer':
                fieldsets = (
                    (None, {'fields': ('email', 'password', 'company_email', 'profile_image', 'last_name', 'first_name', 'middle_name', 'gender', 'birth_date', 'phone', 'city', 'company_name', 'site_link', 'inn','ogr','kpp', 'postal_code', 'address', 'vk_link', 'ok_link', 'telegram_link', 'whatsapp_link', 'skype_link', 'desc')}),
                    ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
                    ('Important dates', {'fields': ('last_login',)}),
                )
            elif obj.role == 'applicant':
                fieldsets = (
                    (None, {'fields': ('email', 'password',  'profile_image', 'last_name', 'first_name', 'middle_name', 'gender', 'birth_date', 'citizenship', 'city', 'postal_code', 'address', 'phone', 'telephone_show', 'vk_link', 'ok_link', 'telegram_link', 'whatsapp_link', 'skype_link', 'social_network_show')}),
                    ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
                    ('Important dates', {'fields': ('last_login',)}),
                )
        return fieldsets

    # Настройка полей при создании нового пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')},
         ),
    )

    ordering = ('email',)

    # Добавляем вакансии только для работодателей
    def get_inline_instances(self, request, obj=None):
        if obj and obj.role == 'employer':  # Если это работодатель
            return [VacancyInline(self.model, self.admin_site)]
        return []

@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'desc_1', 'desc_2', 'city_1', 'address_1', 'postal_code_1', 'employment_hidden', 'work_hidden', 'specialization_hidden', 'languages_hidden', 'education_hidden', 'relocation', 'resume_required', 'exp', 'money', 'skills_hidden', 'salary_from_1', 'salary_to_1', 'currency_1')
    search_fields = ('title', 'employer__company_name')
    form = VacancyForm

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'vacancy', 'gender', 'created_at', 'unique_link')
    search_fields = ('applicant__email', 'vacancy__title')
    inlines = [InterviewQuestionInline]

@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ('interview', 'text', 'video', 'question_order', 'text_answer')
    search_fields = ('interview__applicant__email', 'text')

@admin.register(VacancyResponse)
class VacancyResponseAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'vacancy', 'responded_at')
    ordering = ('-responded_at',)

    def get_queryset(self, request):
        # Возвращаем все записи, независимо от пользователя
        return VacancyResponse.objects.all()

@admin.register(VideoResponse)
class VideoResponseAdmin(admin.ModelAdmin):
    list_display = ('question', 'file', 'uploaded_at')