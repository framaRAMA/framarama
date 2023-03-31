
from django.db import models
from django.contrib.auth.models import AbstractUser

''' Use our own User model

    It is a little bit tricky to exchange the user model when not doing so at the
    very initial project setup (usually you will do this before executing any migration
    on initial project setup).
    
    The reason behind this is, that all table will reference the standard User model
    in the tables (auth.User), which need to be updated manually when changing it
    later.
    
    With default user model:
        CREATE TABLE IF NOT EXISTS "config_frame" (
            ... some columns and one referencing user ...
            "user_id" bigint NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
            ...
        );

    With custom user model:
        CREATE TABLE IF NOT EXISTS "config_frame" (
            ... some columns and one referencing user ...
            "user_id" bigint NOT NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED,
            ...
        );

    Details see:
        https://www.caktusgroup.com/blog/2019/04/26/how-switch-custom-django-user-model-mid-project/
    
    Migration in code:
        * check if third party applications are also accessing User model direclty (they should change it)
        * replace User with get_user_model() (code) or settings.AUTH_USER_MODEL (model keys)
        * create new "accounts" app and define the model using old "auth_user" table (models.py)
        * register admin pages to use new model (admin.py)
    
    Migration in database:
        * run "makemigrations" command
        * run "migrate account" command, will now run into InconsistentMigrationHistory error
        * fake account migration and update existing content type by manual SQL:
          echo "INSERT INTO django_migrations (app, name, applied) VALUES ('account', '0001_initial', CURRENT_TIMESTAMP);" | python manage.py dbshell
          echo "UPDATE django_content_type SET app_label = 'account' WHERE app_label = 'auth' and model = 'user';" | python manage.py dbshell
    
    At this point the new User model can be changed/updated and we can use normal migration
    process with new user model.

    If required - which was also done here - remove the Meta class from model and run a
    "makemigrations" & "migrate" combo again.
'''
class User(AbstractUser):

    def __str__(self):
        return self.username

