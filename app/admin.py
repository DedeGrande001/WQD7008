"""
Django admin configuration - MovieLens Edition
"""
from django.contrib import admin
from .models import Movie, Rating, RecommendationData, RawDataset, UserPreference


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['movie_id', 'title', 'genres', 'year', 'avg_rating', 'rating_count', 'created_at']
    list_filter = ['year', 'created_at']
    search_fields = ['title', 'movie_id', 'genres']
    ordering = ['-avg_rating', '-rating_count']
    list_per_page = 50


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'movie', 'rating', 'timestamp', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user_id', 'movie__title']
    ordering = ['-created_at']
    list_per_page = 100


@admin.register(RecommendationData)
class RecommendationDataAdmin(admin.ModelAdmin):
    list_display = ['movie', 'recommendation_score', 'popularity_score', 'user_id', 'created_at']
    list_filter = ['created_at']
    search_fields = ['movie__title', 'user_id']
    ordering = ['-recommendation_score']
    list_per_page = 50


@admin.register(RawDataset)
class RawDatasetAdmin(admin.ModelAdmin):
    list_display = ['id', 'data_file', 'upload_date', 'processed', 'processed_date', 'record_count']
    list_filter = ['processed', 'upload_date']
    search_fields = ['data_file']
    ordering = ['-upload_date']


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'favorite_categories', 'created_at', 'updated_at']
    search_fields = ['user__username']
    ordering = ['-created_at']
