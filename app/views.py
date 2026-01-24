"""
Simplified API views for recommendation system
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Avg, Count
from .models import Movie, RecommendationData


def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'recommendation-system',
        'message': 'System is running'
    })


def stats_api(request):
    """Get system statistics"""
    try:
        total_movies = Movie.objects.count()
        total_recommendations = RecommendationData.objects.count()

        # Calculate average rating
        avg_rating_dict = Movie.objects.aggregate(avg_rating=Avg('avg_rating'))
        avg_rating = round(avg_rating_dict['avg_rating'] or 0, 2)

        # Get top 10 recommendations
        top_recommendations = list(
            RecommendationData.objects
            .select_related('movie')
            .values('movie__title', 'movie__genres', 'recommendation_score')
            .order_by('-recommendation_score')[:10]
        )

        return JsonResponse({
            'success': True,
            'data': {
                'total_movies': total_movies,
                'total_recommendations': total_recommendations,
                'average_rating': avg_rating,
                'top_recommendations': top_recommendations
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def recommendations_api(request):
    """Get all recommendations (with optional pagination)"""
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        genre = request.GET.get('genre', '')

        query = RecommendationData.objects.select_related('movie')

        # Filter by genre if provided
        if genre:
            query = query.filter(movie__genres__icontains=genre)

        # Get total count
        total = query.count()

        # Get paginated results
        recommendations = list(
            query.values(
                'movie__title',
                'movie__genres',
                'movie__year',
                'recommendation_score'
            ).order_by('-recommendation_score')[offset:offset+limit]
        )

        return JsonResponse({
            'success': True,
            'data': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'recommendations': recommendations
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def stats_page(request):
    """Render the statistics dashboard page"""
    return render(request, 'app/stats.html')


def recommendations_page(request):
    """Render the recommendations list page"""
    return render(request, 'app/recommendations.html')
