"""atop URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView

from atop import views
from atop.tests import simulators
from atop.settings import TESTING
import sys

if (TESTING):
    test_urls =  [
        path('carmin_simulation/<carmin_server>/<method>/', simulators.carmin_simulation_dispatcher, name="carmin_simulation_dispatcher"), 
        path('carmin_simulation/<carmin_server>/pipelines/<pipeline_id>/boutiquesdescriptor', simulators.carmin_simulation_dispatcher, name="carmin_simulation_dispatcher"),
        path('urldesc_simulation/<url>/', simulators.urldesc_simulation_dispatcher, name="urldesc_simulation_dispatcher"),
]

else:
    test_urls = []

urlpatterns = [
    path('', views.home),
    path('admin/', admin.site.urls),
    path('register/', views.register, name="register"),
    path('login/', views.login, name="login"),
    path('delete/', views.delete, name="delete"),
#	path('add_tool/', views.add_tool, name="add_tool"),
    path('run_tests/', views.run_tests, name="run_tests"),
    path('validate_descriptor/', views.validate, name="validate"),
    path('logout/', views.log_out, name="log_out"),
    #path('carmin_simulation/<carmin_server>/<method>/', simulators.carmin_simulation_dispatcher, name="carmin_simulation_dispatcher"),
    #path('carmin_simulation/<carmin_server>/pipelines/<pipeline_id>/boutiquesdescriptor', simulators.carmin_simulation_dispatcher, name="carmin_simulation_dispatcher"),

] + test_urls


