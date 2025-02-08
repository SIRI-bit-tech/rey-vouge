from django.contrib import admin
from .models import Category, Product, ProductImage, Review, ClothingSize, ClothingColor
from django import forms

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(ClothingSize)
class ClothingSizeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    ordering = ('order', 'name')
    list_editable = ('order', 'is_active')

@admin.register(ClothingColor)
class ClothingColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'color_code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    ordering = ('display_name',)
    list_editable = ('is_active',)

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
    list_display = ('name', 'category', 'price', 'stock', 'is_active', 'is_featured', 'created_at')
    list_filter = ('category', 'is_active', 'is_featured', 'is_new_arrival')
    search_fields = ('name', 'description', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ReviewInline]
    filter_horizontal = ('available_clothing_sizes', 'available_clothing_colors')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'sku', 'description', 'price', 'sale_price', 'stock')
        }),
        ('Sizes and Colors', {
            'fields': ('available_clothing_sizes', 'available_clothing_colors', 'available_sizes', 'colors'),
            'description': 'For clothing items, use the multi-select fields. For other items, use the text fields.'
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_new_arrival')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        })
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.category:
            category_name = obj.category.name.lower()
            if 'cloth' in category_name or 'dress' in category_name or 'shirt' in category_name:
                form.base_fields['available_sizes'].widget.attrs['disabled'] = True
                form.base_fields['colors'].widget.attrs['disabled'] = True
            else:
                form.base_fields['available_clothing_sizes'].widget.attrs['disabled'] = True
                form.base_fields['available_clothing_colors'].widget.attrs['disabled'] = True
        return form

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__email', 'comment')
    readonly_fields = ('created_at',)
