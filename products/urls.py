from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.categories_view, name='categories'),
    path('products/', views.product_list, name='product_list'),
    path('category/<slug:category_slug>/', views.product_list_by_category, name='product_list_by_category'),
    path('filter/', views.product_filter, name='product_filter'),
    path('quick-view/<int:product_id>/', views.quick_view, name='quick_view'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),
    path('search/', views.product_search, name='product_search'),
    path('<slug:slug>/reviews/', views.product_reviews, name='product_reviews'),
    path('add-review/<slug:slug>/', views.add_review, name='add_review'),
    path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    # API endpoints
    path('api/products/', views.ProductListAPI.as_view(), name='product_list_api'),
    path('api/products/<int:pk>/', views.ProductDetailAPI.as_view(), name='product_detail_api'),
    path('api/categories/', views.CategoryListAPI.as_view(), name='category_list_api'),
] 