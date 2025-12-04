"""
Django Admin configuration for User Management and RBAC models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from .models import User, Role, UserRole, Station
from .models import Route, MSDBSMap


class UserCreationForm(forms.ModelForm):
    """Form for creating new users with password confirmation."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Form for updating users with read-only password display."""
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change the password using "
            "<a href=\"../password/\">this form</a>."
        ),
    )

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name', 'phone', 'is_active', 'is_staff', 'is_superuser')


class UserRoleInline(admin.TabularInline):
    """Inline admin for managing user roles within the User admin."""
    model = UserRole
    extra = 1
    fields = ('role', 'station', 'active')
    raw_id_fields = ('station',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    form = UserChangeForm
    add_form = UserCreationForm
    
    list_display = ('email', 'full_name', 'phone', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('email', 'full_name', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone')}),
        ('Role Dates', {'fields': ('role_in', 'role_out')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone', 'password1', 'password2'),
        }),
    )
    
    inlines = [UserRoleInline]
    readonly_fields = ('date_joined', 'last_login')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""
    list_display = ('code', 'name', 'description')
    search_fields = ('code', 'name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        (None, {'fields': ('code', 'name', 'description')}),
    )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin interface for UserRole model."""
    list_display = ('user', 'role', 'station', 'active', 'created_at', 'updated_at')
    list_filter = ('active', 'role', 'created_at')
    search_fields = ('user__email', 'user__full_name', 'role__name', 'station__name')
    ordering = ('-created_at',)
    raw_id_fields = ('user', 'station')
    
    fieldsets = (
        (None, {'fields': ('user', 'role', 'station', 'active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    """Admin interface for Station model."""
    list_display = ('code', 'name', 'type', 'city', 'parent_station')
    list_filter = ('type', 'city')
    search_fields = ('name', 'code', 'city', 'address')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('type', 'code', 'name')
        }),
        ('Location Details', {
            'fields': ('address', 'city', 'lat', 'lng', 'geofence_radius_m')
        }),
        ('Hierarchy', {
            'fields': ('parent_station',),
            'description': 'For DBS stations, select the parent Mother Station (MS)'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Filter parent_station to only show MS type stations
        if 'parent_station' in form.base_fields:
            form.base_fields['parent_station'].queryset = Station.objects.filter(type='MS')
        return form

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    """Admin interface for Route model."""
    list_display = ('name', 'code', 'ms', 'dbs', 'planned_rtkm_km', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default', 'ms', 'dbs')
    search_fields = ('name', 'code', 'ms__name', 'dbs__name')
    ordering = ('name',)
    raw_id_fields = ('ms', 'dbs')

@admin.register(MSDBSMap)
class MSDBSMapAdmin(admin.ModelAdmin):
    """Admin interface for MS-DBS Mapping."""
    list_display = ('ms', 'dbs', 'active')
    list_filter = ('active', 'ms', 'dbs')
    search_fields = ('ms__name', 'dbs__name')
    ordering = ('ms', 'dbs')
    raw_id_fields = ('ms', 'dbs')
