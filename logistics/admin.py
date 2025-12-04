from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered 

# Note: You can remove 'from .models import *' as it's no longer necessary

# Define the name of your app. This should match the name in settings.py or apps.py
# If your app is named 'store', use 'store'.
APP_NAME = 'logistics' 

# 1. Get the list of all models in the specified app
models = apps.get_app_config(APP_NAME).get_models()

# 2. Loop through all models and register them
for model in models:
    try:
        # 3. Define a generic ModelAdmin class to display all fields
        class GenericModelAdmin(admin.ModelAdmin):
            # This line dynamically sets list_display to include all field names
            list_display = [field.name for field in model._meta.fields]
            
        # 4. Register the model using the custom ModelAdmin
        admin.site.register(model, GenericModelAdmin)
        
    except AlreadyRegistered:
        # This handles cases where you might have manually registered 
        # a model before this loop, preventing errors.
        pass
    except Exception as e:
        # Handle other potential errors during registration
        print(f"Could not register model {model.__name__}: {e}")