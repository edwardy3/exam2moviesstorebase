from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='movies.index'),
    path('<int:id>/', views.show, name='movies.show'),
    path('<int:id>/review/create/', views.create_review, name='movies.create_review'),
    path('<int:id>/review/<int:review_id>/edit/', views.edit_review, name='movies.edit_review'),
    path('<int:id>/review/<int:review_id>/delete/', views.delete_review, name='movies.delete_review'),
    path('<int:id>/rate/', views.rate_movie, name='movies.rate'),
    path('popularity-map/', views.popularity_map, name='movies.popularity_map'),
    path('api/popular-by-polygon/', views.api_popular_movies_by_polygon, name='movies.api_popular_by_polygon'),
]