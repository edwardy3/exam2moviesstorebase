from django import template
register = template.Library()
@register.filter(name='get_quantity')
def get_cart_quantity(cart, movie_id):
    # support both string and int keys safely
    if cart is None:
        return 0
    if str(movie_id) in cart:
        return cart[str(movie_id)]
    if movie_id in cart:
        return cart[movie_id]
    return 0