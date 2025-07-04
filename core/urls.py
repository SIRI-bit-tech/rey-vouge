from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
    path('admin/newsletter/', views.admin_newsletter, name='admin_newsletter'),
    path('admin/newsletter/send/', views.send_newsletter, name='send_newsletter'),
    path('newsletter/delete/<int:subscriber_id>/', views.delete_subscriber, name='delete_subscriber'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('store-locations/', views.store_locations, name='store_locations'),
    path('promotions/', views.promotions, name='promotions'),
    path('log-javascript-error/', views.log_javascript_error, name='log_javascript_error'),
    
    # Legal pages
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('return-policy/', views.return_policy, name='return_policy'),
] 