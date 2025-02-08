from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from products.models import Product, Category
from core.models import StoreLocation, Promotion

class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = 'daily'

    def items(self):
        return ['core:home', 'core:about', 'core:contact', 'core:store_locations', 'core:promotions']

    def location(self, item):
        return reverse(item)

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('products:product_detail', args=[obj.slug])

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('products:category_detail', args=[obj.slug])

class LocationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return StoreLocation.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('core:store_locations')

class PromotionSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Promotion.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('core:promotions') 