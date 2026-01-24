"""
Simplified URL configuration for API
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.health_check, name='health_check'),
    path('health/', views.health_check, name='health'),
    path('stats/', views.stats_api, name='stats'),
    path('dashboard/', views.stats_page, name='dashboard'),
    path('recommendations/', views.recommendations_api, name='recommendations'),
    path('movies/', views.recommendations_page, name='movies'),
]
