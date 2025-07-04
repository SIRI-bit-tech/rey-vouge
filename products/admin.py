from django.contrib import admin
from .models import Category, Product, ProductImage, Review
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
import csv
import io
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.db.models import F
from django.contrib.admin.widgets import AdminFileWidget

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('name',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('user', 'rating', 'comment', 'created_at')
    can_delete = False

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_status', 'stock', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'is_featured', 'is_new_arrival')
    search_fields = ('name', 'description', 'sku')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['update_stock', 'mark_as_featured', 'mark_as_new_arrival']
    change_list_template = 'admin/products/product/change_list.html'
    inlines = [ProductImageInline, ReviewInline]
    list_editable = ('is_active', 'stock')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.import_csv, name='product_import_csv'),
            path('export-csv/', self.export_csv, name='product_export_csv'),
            path('inventory/', self.inventory_view, name='product_inventory'),
            path('update-stock/', self.update_stock_view, name='update_stock'),
        ]
        return custom_urls + urls

    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['SKU', 'Name', 'Category', 'Description', 'Price', 'Stock', 'Is Active'])
        
        products = Product.objects.all().select_related('category')
        for product in products:
            writer.writerow([
                product.sku,
                product.name,
                product.category.name,
                product.description,
                product.price,
                product.stock,
                product.is_active
            ])
        
        return response

    def stock_status(self, obj):
        if obj.stock <= 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.stock <= 10:
            return format_html('<span style="color: orange;">Low Stock ({0})</span>', obj.stock)
        return format_html('<span style="color: green;">In Stock ({0})</span>', obj.stock)
    stock_status.short_description = 'Stock Status'

    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"Marked {queryset.count()} products as featured")
    mark_as_featured.short_description = "Mark as featured"

    def mark_as_new_arrival(self, request, queryset):
        queryset.update(is_new_arrival=True)
        self.message_user(request, f"Marked {queryset.count()} products as new arrival")
    mark_as_new_arrival.short_description = "Mark as new arrival"

    def import_csv(self, request):
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, 'Please upload a CSV file.')
                return redirect('..')
            
            try:
                decoded_file = csv_file.read().decode('utf-8')
                csv_data = csv.DictReader(io.StringIO(decoded_file))
                
                for row in csv_data:
                    category, _ = Category.objects.get_or_create(name=row['category'])
                    Product.objects.update_or_create(
                        sku=row['sku'],
                        defaults={
                            'name': row['name'],
                            'description': row['description'],
                            'price': float(row['price']),
                            'stock': int(row['stock']),
                            'category': category,
                            'is_active': row['is_active'].lower() == 'true'
                        }
                    )
                
                messages.success(request, 'Successfully imported products.')
            except Exception as e:
                messages.error(request, f'Error importing products: {str(e)}')
            
            return redirect('..')
        
        context = {
            'title': 'Import Products',
            'opts': self.model._meta,
        }
        return render(request, 'admin/products/import_csv.html', context)

    def inventory_view(self, request):
        # Get all products
        products = Product.objects.select_related('category').all()
        
        # Get inventory statistics
        total_products = products.count()
        low_stock = products.filter(stock__lte=10).count()
        out_of_stock = products.filter(stock=0).count()
        
        # Get products by category
        categories = Category.objects.all()
        category_stats = []
        for category in categories:
            category_products = products.filter(category=category)
            category_stats.append({
                'name': category.name,
                'total': category_products.count(),
                'low_stock': category_products.filter(stock__lte=10).count(),
                'out_of_stock': category_products.filter(stock=0).count(),
            })
        
        context = {
            'title': 'Inventory Management',
            'products': products,
            'total_products': total_products,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'category_stats': category_stats,
            'opts': self.model._meta,
        }
        return render(request, 'admin/products/inventory.html', context)

    def update_stock_view(self, request):
        if request.method == 'POST':
            product_id = request.POST.get('product_id')
            new_stock = request.POST.get('new_stock')
            
            try:
                product = Product.objects.get(id=product_id)
                product.stock = int(new_stock)
                product.save()
                messages.success(request, f'Successfully updated stock for {product.name}')
            except Exception as e:
                messages.error(request, f'Error updating stock: {str(e)}')
            
            return redirect('..')
        
        context = {
            'title': 'Update Stock',
            'products': Product.objects.all(),
            'opts': self.model._meta,
        }
        return render(request, 'admin/products/stock_update.html', context)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__email', 'comment')
    readonly_fields = ('created_at',)
