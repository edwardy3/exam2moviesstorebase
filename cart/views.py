from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.db import models
from movies.models import Movie
from .utils import calculate_cart_total
from .models import Order, Item
from django.contrib.auth.decorators import login_required

def index(request):
    cart_total = 0
    movies_in_cart = []
    cart = request.session.get('cart', {})
    movie_ids = [int(k) for k in cart.keys()]
    if movie_ids:
        movies_in_cart = Movie.objects.filter(id__in=movie_ids)
        cart_total = calculate_cart_total(cart, movies_in_cart)

    template_data = {}
    template_data['title'] = 'Cart'
    template_data['movies_in_cart'] = movies_in_cart
    template_data['cart_total'] = cart_total
    return render(request, 'cart/index.html', {'template_data': template_data})

def add(request, id):
    get_object_or_404(Movie, id=id)
    cart = request.session.get('cart', {})
    cart[str(id)] = request.POST['quantity']
    request.session['cart'] = cart
    return redirect('cart.index')

def clear(request):
    request.session['cart'] = {}
    return redirect('cart.index')

@login_required
def purchase(request):
    cart = request.session.get('cart', {})
    movie_ids = [int(k) for k in cart.keys()]

    if not movie_ids:
        return redirect('cart.index')
    
    movies_in_cart = Movie.objects.filter(id__in=movie_ids)
    cart_total = calculate_cart_total(cart, movies_in_cart)

    order = Order()
    order.user = request.user
    order.total = cart_total
    # assign per-user sequential order_number starting at 1
    last_order_number = Order.objects.filter(user=request.user).aggregate(
        max_number=models.Max('order_number')
    )['max_number'] or 0
    order.order_number = last_order_number + 1
    # capture optional lat/lng from POST
    latitude = request.POST.get('latitude') or request.session.get('purchase_lat')
    longitude = request.POST.get('longitude') or request.session.get('purchase_lng')
    if latitude and longitude:
        try:
            order.latitude = float(latitude)
            order.longitude = float(longitude)
        except (ValueError, TypeError):
            pass
    order.save()

    for movie in movies_in_cart:
        item = Item()
        item.movie = movie
        item.price = movie.price
        item.order = order
        item.quantity = cart[str(movie.id)]
        # Persist purchase coordinates at item level as well
        if order.latitude is not None and order.longitude is not None:
            item.latitude = order.latitude
            item.longitude = order.longitude
        item.save()

    request.session['cart'] = {}
    template_data = {}
    template_data['title'] = 'Purchase confirmation'
    template_data['order_id'] = order.id
    template_data['order_number'] = order.order_number
    return render(request, 'cart/purchase.html', {'template_data': template_data})