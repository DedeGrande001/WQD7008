"""
Database models for recommendation system - MovieLens Edition
"""
from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    """
    Model to store movie information from MovieLens
    """
    movie_id = models.IntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=500)
    genres = models.CharField(max_length=200, blank=True, null=True)
    year = models.IntegerField(null=True, blank=True)

    # Aggregated statistics
    avg_rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'movies'
        ordering = ['-avg_rating', '-rating_count']

    def __str__(self):
        return f"{self.title} ({self.avg_rating:.2f})"


class Rating(models.Model):
    """
    Model to store user ratings for movies
    """
    user_id = models.IntegerField(db_index=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='ratings')
    rating = models.FloatField()
    timestamp = models.BigIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ratings'
        unique_together = ('user_id', 'movie')
        indexes = [
            models.Index(fields=['user_id', 'rating']),
        ]

    def __str__(self):
        return f"User {self.user_id} rated {self.movie.title}: {self.rating}"


class RecommendationData(models.Model):
    """
    Model to store movie recommendation results
    """
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_score = models.FloatField(default=0.0)
    popularity_score = models.FloatField(default=0.0)
    genre_match_score = models.FloatField(default=0.0, null=True, blank=True)

    # For personalized recommendations
    user_id = models.IntegerField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recommendation_data'
        ordering = ['-recommendation_score']
        indexes = [
            models.Index(fields=['user_id', '-recommendation_score']),
        ]

    def __str__(self):
        return f"{self.movie.title} (Score: {self.recommendation_score:.2f})"


class RawDataset(models.Model):
    """
    Model to store raw dataset before Spark processing
    """
    data_file = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_date = models.DateTimeField(null=True, blank=True)
    record_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'raw_dataset'
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.data_file} - {'Processed' if self.processed else 'Pending'}"


class UserPreference(models.Model):
    """
    Model to store user preferences for personalized recommendations
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference')
    favorite_categories = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_preference'

    def __str__(self):
        return f"{self.user.username}'s preferences"
