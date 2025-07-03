from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Category, Product, Review
from .serializers import CategorySerializer, ProductSerializer, ReviewSerializer
from django.template.loader import render_to_string
from django.contrib import messages
from django.urls import reverse
from orders.models import Cart, CartItem
import json

def get_unique_values(queryset, field):
    """Helper function to get unique values from a field in a queryset"""
    values = set()
    for item in queryset:
        field_value = getattr(item, field)
        if field_value:
            # Split the string if it contains multiple values
            if ',' in field_value:
                values.update(v.strip() for v in field_value.split(','))
            else:
                values.add(field_value.strip())
    return sorted(list(values))

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    # Get unique sizes and colors from actual products
    available_sizes = get_unique_values(products, 'available_sizes')
    available_colors = get_unique_values(products, 'colors')
    
    # Filter by search query
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and min_price.isdigit():
        products = products.filter(price__gte=float(min_price))
    if max_price and max_price.isdigit():
        products = products.filter(price__lte=float(max_price))
    
    # Filter by size
    sizes = request.GET.getlist('size')
    if sizes:
        size_query = Q()
        for size in sizes:
            size_query |= Q(available_sizes__icontains=size)
        products = products.filter(size_query)
    
    # Filter by color
    colors = request.GET.getlist('color')
    if colors:
        color_query = Q()
        for color in colors:
            color_query |= Q(colors__icontains=color)
        products = products.filter(color_query)
    
    # Filter by new arrivals
    if request.GET.get('new_arrivals'):
        products = products.filter(is_new_arrival=True)
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    if sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    elif sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'oldest':
        products = products.order_by('created_at')
    else:
        products = products.order_by('-created_at')  # Default sorting
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    context = {
        'category': category,
        'categories': categories,
        'products': products,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
        'selected_sizes': sizes,
        'selected_colors': colors,
        'current_sort': sort,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    
    # Get recommendations
    similar_products = product.get_similar_products()
    frequently_bought = product.get_frequently_bought_together()
    viewed_together = product.get_viewed_together()
    
    context = {
        'product': product,
        'similar_products': similar_products,
        'frequently_bought': frequently_bought,
        'viewed_together': viewed_together,
    }
    return render(request, 'products/product_detail.html', context)

@login_required
def add_review(request, slug):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        }, status=405)

    try:
        data = json.loads(request.body)
        product = get_object_or_404(Product, slug=slug)
        
        # Validate rating
        try:
            rating = int(data.get('rating', 0))
            if not 1 <= rating <= 5:
                raise ValueError('Rating must be between 1 and 5')
        except (TypeError, ValueError) as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        
        # Validate comment
        comment = data.get('comment', '').strip()
        if not comment:
            return JsonResponse({
                'success': False,
                'error': 'Comment is required'
            }, status=400)
        
        # Check if user has already reviewed this product
        review, created = Review.objects.get_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        if not created:
            review.rating = rating
            review.comment = comment
            review.save()
            message = 'Your review has been updated successfully'
        else:
            message = 'Your review has been added successfully'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'review': {
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%B %d, %Y'),
                'user_name': review.user.get_full_name() or review.user.username
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def product_search(request):
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__icontains=query) |
            Q(colors__icontains=query) |
            Q(available_sizes__icontains=query)
        ).distinct()
    else:
        products = Product.objects.filter(is_active=True)
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    context = {
        'query': query,
        'products': products,
        'categories': Category.objects.all(),
        'sizes': dict(Product.SIZES),
        'colors': dict(Product.COLORS),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_list.html', context)
    return render(request, 'products/product_list.html', context)

def product_filter(request):
    products = Product.objects.filter(is_active=True)
    
    # Get all filter parameters
    filters = {}
    
    # Category filter - handle single category selection
    category = request.GET.get('category')
    if category:
        products = products.filter(category__slug=category)
        filters['current_category'] = category
    
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and min_price.isdigit():
        products = products.filter(price__gte=float(min_price))
        filters['min_price'] = min_price
    if max_price and max_price.isdigit():
        products = products.filter(price__lte=float(max_price))
        filters['max_price'] = max_price
    
    # Size filter
    sizes = request.GET.getlist('size')
    if sizes:
        size_query = Q()
        for size in sizes:
            size_query |= Q(available_sizes__icontains=size)
        products = products.filter(size_query)
        filters['selected_sizes'] = sizes
    
    # Color filter
    colors = request.GET.getlist('color')
    if colors:
        color_query = Q()
        for color in colors:
            color_query |= Q(colors__icontains=color)
        products = products.filter(color_query)
        filters['selected_colors'] = colors
    
    # Sort products
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    else:  # newest
        products = products.order_by('-created_at')
    
    filters['current_sort'] = sort_by
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 12)  # 12 products per page
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    context = {
        'products': products_page,
        'categories': Category.objects.all(),
        'sizes': dict(Product.SIZES),
        'colors': dict(Product.COLORS),
        **filters  # Include all filter parameters in context
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/product_list.html', context)
    return render(request, 'products/product_list.html', context)

def product_reviews(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    
    # Pagination for reviews
    paginator = Paginator(reviews, 5)  # 5 reviews per page
    page = request.GET.get('page', 1)
    reviews_page = paginator.get_page(page)
    
    context = {
        'product': product,
        'reviews': reviews_page,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'products/partials/reviews_list.html', context)
    return render(request, 'products/reviews.html', context)

# API Views
class ProductListAPI(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Product.objects.all()
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset

class ProductDetailAPI(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

class CategoryListAPI(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

def quick_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    html = render_to_string('products/partials/quick_view.html', {
        'product': product,
        'request': request
    })
    return JsonResponse({
        'html': html,
        'success': True
    })

def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'redirect_url': f"{reverse('accounts:login')}?next={request.path}"
        })

    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    size = request.POST.get('size')
    color = request.POST.get('color')

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        color=color,
        defaults={'quantity': quantity}
    )

    if not item_created:
        cart_item.quantity += quantity
        cart_item.save()

    cart_count = sum(item.quantity for item in cart.items.all())
    
    return JsonResponse({
        'success': True,
        'message': f'Added {quantity} item(s) to cart',
        'cart_count': cart_count
    })

@login_required
def add_to_wishlist(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'redirect_url': f"{reverse('accounts:login')}?next={request.path}"
        })

    product = get_object_or_404(Product, id=product_id)
    wishlist = request.user.wishlist
    
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        added = False
    else:
        wishlist.products.add(product)
        added = True
    
    wishlist_count = wishlist.products.count()
    
    return JsonResponse({
        'success': True,
        'added': added,
        'wishlist_count': wishlist_count
    })

def categories_view(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'products/categories.html', {
        'categories': categories
    })

def product_list_by_category(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category, is_active=True)
    
    # Get unique sizes and colors from actual products in this category
    available_sizes = get_unique_values(products, 'available_sizes')
    available_colors = get_unique_values(products, 'colors')
    
    # Apply sorting if specified
    sort = request.GET.get('sort', '-created_at')
    if sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')
    elif sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get wishlist count if user is authenticated
    wishlist_count = None
    if request.user.is_authenticated:
        wishlist_count = request.user.wishlist.products.count()
    
    context = {
        'category': category,
        'categories': Category.objects.all(),
        'products': products,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
        'current_sort': sort,
        'wishlist_count': wishlist_count
    }
    
    return render(request, 'products/product_list.html', context)
