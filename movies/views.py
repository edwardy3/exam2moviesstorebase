from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Review, Rating
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Avg
from cart.models import Item
import json


def index(request):
    search_term = request.GET.get('search')
    if search_term:
        movies = Movie.objects.filter(name__icontains=search_term)
    else:
        movies = Movie.objects.all()

    template_data = {}
    template_data['title'] = 'Movies'
    template_data['movies'] = movies
    return render(request, 'movies/index.html', {'template_data': template_data})


def show(request, id):
    movie = Movie.objects.get(id=id)
    reviews = Review.objects.filter(movie=movie)
    avg_rating = movie.ratings.aggregate(avg=Avg('value'))['avg'] or 0
    user_rating = None
    if request.user.is_authenticated:
        rating = Rating.objects.filter(movie=movie, user=request.user).first()
        user_rating = rating.value if rating else None

    template_data = {}
    template_data['title'] = movie.name
    template_data['movie'] = movie
    template_data['reviews'] = reviews
    template_data['avg_rating'] = round(avg_rating, 2) if avg_rating else None
    template_data['user_rating'] = user_rating
    return render(request, 'movies/show.html', {'template_data': template_data})


@login_required
def create_review(request, id):
    if request.method == 'POST' and request.POST['comment'] != '':
        movie = Movie.objects.get(id=id)
        review = Review()
        review.comment = request.POST['comment']
        review.movie = movie
        review.user = request.user
        review.save()
        return redirect('movies.show', id=id)
    else:
        return redirect('movies.show', id=id)


@login_required
def edit_review(request, id, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user != review.user:
        return redirect('movies.show', id=id)

    if request.method == 'GET':
        template_data = {}
        template_data['title'] = 'Edit Review'
        template_data['review'] = review
        return render(request, 'movies/edit_review.html', {'template_data': template_data})
    elif request.method == 'POST' and request.POST['comment'] != '':
        review = Review.objects.get(id=review_id)
        review.comment = request.POST['comment']
        review.save()
        return redirect('movies.show', id=id)
    else:
        return redirect('movies.show', id=id)


@login_required
def delete_review(request, id, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    review.delete()
    return redirect('movies.show', id=id)


@login_required
def rate_movie(request, id):
    movie = get_object_or_404(Movie, id=id)
    if request.method == 'POST':
        value = int(request.POST.get('rating', 0))
        if 1 <= value <= 5:
            Rating.objects.update_or_create(
                movie=movie,
                user=request.user,
                defaults={'value': value}
            )
    return redirect('movies.show', id=id)


@login_required
def popularity_map(request):
    template_data = {}
    template_data['title'] = 'Local Popularity Map'
    return render(request, 'movies/popularity_map.html', {'template_data': template_data})


def _point_in_polygon(lat, lng, polygon_coords):
    # Ray casting algorithm; polygon_coords is list of [lng, lat]
    x = lng
    y = lat
    inside = False
    for i in range(len(polygon_coords)):
        j = (i - 1) % len(polygon_coords)
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]
        intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if intersect:
            inside = not inside
    return inside


def _aggregate_movies_counts(items_qs, threshold):
    aggregated = (
        items_qs.values('movie_id', 'movie__name')
        .annotate(total_quantity=Sum('quantity'))
        .filter(total_quantity__gte=threshold)
        .order_by('-total_quantity')
    )
    return [
        {
            'movieId': row['movie_id'],
            'title': row['movie__name'],
            'purchaseCount': row['total_quantity'],
        }
        for row in aggregated
    ]


@login_required
def api_popular_movies_by_polygon(request):
    body = json.loads(request.body.decode('utf-8'))
    threshold = body.get('threshold', 0)
    geojson = body.get('geojson')

    if not geojson:
        return JsonResponse({'error': 'geojson required'}, status=400)

    # Extract geometry and coordinates
    geom = geojson.get('geometry') if geojson.get('type') == 'Feature' else geojson
    gtype = geom.get('type')
    coords = geom.get('coordinates', [])

    # Extract polygon coordinates
    if gtype == 'Polygon':
        polygons = [coords[0]]
    elif gtype == 'MultiPolygon':
        polygons = [poly[0] for poly in coords]
    else:
        return JsonResponse({'error': 'Unsupported geometry type'}, status=400)

    # Find items within polygons
    items_in = [
        it['id'] for it in Item.objects.select_related('movie').values('id', 'latitude', 'longitude')
        if it['latitude'] and it['longitude'] and 
        any(_point_in_polygon(it['latitude'], it['longitude'], poly) for poly in polygons)
    ]

    items = Item.objects.select_related('order', 'movie').filter(id__in=items_in)
    return JsonResponse({
        'threshold': threshold,
        'results': _aggregate_movies_counts(items, threshold),
    })