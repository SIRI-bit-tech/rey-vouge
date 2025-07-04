from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from cloudinary.models import CloudinaryField
import uuid
from django.db.models import Q
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = CloudinaryField('image', 
        folder='categories/',
        transformation={
            'width': 800,
            'height': 600,
            'crop': 'fill',
            'quality': 'auto:good'
        },
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('products:product_list_by_category', args=[self.slug])

    def product_count(self):
        return self.products.count()
    product_count.short_description = 'Number of Products'

class Product(models.Model):
    CLOTHING_SIZES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('2XL', 'Double Extra Large'),
        ('3XL', 'Triple Extra Large'),
        ('4XL', '4 Extra Large'),
        ('5XL', '5 Extra Large'),
        ('6XL', '6 Extra Large'),
        ('7XL', '7 Extra Large'),
        ('8XL', '8 Extra Large'),
        ('9XL', '9 Extra Large'),
        ('10XL', '10 Extra Large'),
    ]
    
    SHOE_SIZES = [
        ('34', '34'),
        ('35', '35'),
        ('36', '36'),
        ('37', '37'),
        ('38', '38'),
        ('39', '39'),
        ('40', '40'),
        ('41', '41'),
        ('42', '42'),
        ('43', '43'),
        ('44', '44'),
        ('45', '45'),
        ('46', '46'),
        ('47', '47'),
        ('48', '48'),
        ('49', '49'),
        ('50', '50'),
    ]
    
    PERFUME_SIZES = [
        ('30ml', '30ml'),
        ('50ml', '50ml'),
        ('65ml', '65ml'),
        ('75ml', '75ml'),
        ('100ml', '100ml'),
        ('200ml', '200ml'),
        ('300ml', '300ml'),
        ('500ml', '500ml'),
        ('1000ml', '1000ml'),
    ]
    
    COLORS = [
        ('black', 'Black'),
        ('white', 'White'),
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
        ('brown', 'Brown'),
        ('gray', 'Gray'),
        ('navy', 'Navy'),
        ('beige', 'Beige'),
        ('navy-blue', 'Navy Blue'),
        ('champagne', 'Champagne'),
        ('pink', 'Pink'),
        ('orange', 'Orange'),
        ('purple', 'Purple'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('turquoise', 'Turquoise'),
        ('pearl', 'Pearl'),
        ('ivory', 'Ivory'),
        ('lilac', 'Lilac'),
    ]
    
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    available_sizes = models.CharField(max_length=200, help_text='Enter sizes separated by commas. For clothes: S,M,L. For shoes: 38,39,40. For perfumes: 50ml,100ml')
    colors = models.CharField(max_length=200, help_text='Enter colors separated by commas (e.g., red,blue,black)', blank=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # SEO fields
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate a unique slug
            base_slug = slugify(self.name)
            unique_id = str(uuid.uuid4())[:8]
            self.slug = f"{base_slug}-{unique_id}"
        
        if not self.sku:
            # Generate a unique SKU
            self.sku = f"REY-{str(uuid.uuid4())[:8].upper()}"
        
        # Generate SEO metadata if not provided
        if not self.meta_title:
            self.meta_title = f"{self.name} - REY PREMIUM VOGUE"
        
        if not self.meta_description:
            self.meta_description = f"{self.description[:157]}..." if len(self.description) > 160 else self.description
        
        if not self.meta_keywords:
            keywords = [self.name, self.category.name, 'fashion', 'premium clothing']
            self.meta_keywords = ', '.join(keywords)
        
        # Clean and format sizes based on category
        if self.available_sizes:
            sizes = [s.strip() for s in self.available_sizes.split(',')]
            category_name = self.category.name.lower()
            
            if 'perfume' in category_name:
                valid_sizes = dict(self.PERFUME_SIZES)
                self.available_sizes = ','.join(s for s in sizes if s in valid_sizes)
            elif 'shoe' in category_name:
                valid_sizes = dict(self.SHOE_SIZES)
                self.available_sizes = ','.join(s for s in sizes if s in valid_sizes)
            else:  # Default to clothing sizes
                valid_sizes = dict(self.CLOTHING_SIZES)
                self.available_sizes = ','.join(s.upper() for s in sizes if s.upper() in valid_sizes)
        
        # Clean and format colors
        if self.colors:
            if self.colors.lower().strip() == 'none':
                self.colors = ''  # Set to empty string if 'none' is specified
            else:
                colors = [c.strip().lower() for c in self.colors.split(',')]
                valid_colors = dict(self.COLORS)
                self.colors = ','.join(c for c in colors if c in valid_colors)
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('products:product_detail', kwargs={'slug': self.slug})
    
    @property
    def discount_percentage(self):
        if self.sale_price and self.price:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return round(discount)
        return 0
    
    @property
    def is_on_sale(self):
        return bool(self.sale_price and self.sale_price < self.price)
    
    @property
    def average_rating(self):
        if self.reviews.exists():
            return round(self.reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0
    
    @property
    def size_list(self):
        return [size.strip() for size in self.available_sizes.split(',')] if self.available_sizes else []
    
    @property
    def color_list(self):
        return [color.strip() for color in self.colors.split(',')] if self.colors else []
    
    def get_similar_products(self, limit=4):
        """Get similar products based on category and tags."""
        similar_products = Product.objects.filter(
            Q(category=self.category) |
            Q(colors__icontains=self.colors) if self.colors else Q()
        ).exclude(id=self.id).filter(is_active=True)
        
        # Add price range filter
        price_range = Decimal('0.5')  # 50% above or below the current product's price
        min_price = self.price * (1 - price_range)
        max_price = self.price * (1 + price_range)
        
        similar_products = similar_products.filter(
            price__gte=min_price,
            price__lte=max_price
        )
        
        return similar_products.distinct()[:limit]
    
    def get_frequently_bought_together(self, limit=3):
        """Get products frequently bought together based on order history."""
        from orders.models import OrderItem
        
        # Get all orders that contain this product
        orders_with_this_product = OrderItem.objects.filter(
            product=self
        ).values_list('order', flat=True)
        
        # Get other products from those orders
        frequently_bought_products = Product.objects.filter(
            orderitem__order__in=orders_with_this_product
        ).exclude(
            id=self.id
        ).annotate(
            times_bought_together=models.Count('id')
        ).filter(
            is_active=True
        ).order_by('-times_bought_together')
        
        return frequently_bought_products[:limit]
    
    def get_viewed_together(self, limit=4):
        """Get products that are often viewed together with this product."""
        from core.models import ProductView
        
        # Get all sessions where this product was viewed
        sessions_with_this_product = ProductView.objects.filter(
            product=self
        ).values_list('session_id', flat=True)
        
        # Get other products viewed in those sessions
        viewed_together_products = Product.objects.filter(
            productview__session_id__in=sessions_with_this_product
        ).exclude(
            id=self.id
        ).annotate(
            view_count=models.Count('id')
        ).filter(
            is_active=True
        ).order_by('-view_count')
        
        return viewed_together_products[:limit]

    @property
    def stock_status(self):
        if self.stock <= 0:
            return 'out_of_stock'
        elif self.stock <= 10:
            return 'low_stock'
        return 'in_stock'

    @property
    def stock_status_display(self):
        if self.stock <= 0:
            return 'Out of Stock'
        elif self.stock <= 10:
            return f'Low Stock ({self.stock} remaining)'
        return 'In Stock'

    @property
    def is_available(self):
        return self.stock > 0 and self.is_active

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = CloudinaryField('image',
        folder='products/',
        transformation={
            'width': 1200,
            'height': 1200,
            'crop': 'fill',
            'quality': 'auto:good'
        }
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-is_primary', 'id']
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
    def save(self, *args, **kwargs):
        if not self.alt_text:
            self.alt_text = f"{self.product.name} - Image"
        super().save(*args, **kwargs)

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=20)  # Changed to support all size types
    color = models.CharField(max_length=50)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    image = CloudinaryField('image',  # Changed to use CloudinaryField
        folder='product_variants/',
        transformation={
            'width': 1200,
            'height': 1200,
            'crop': 'fill',
            'quality': 'auto:good'
        },
        null=True,
        blank=True
    )
    
    class Meta:
        unique_together = ('product', 'size', 'color')
        ordering = ['size', 'color']
    
    def __str__(self):
        return f"{self.product.name} - {self.size} {self.color}"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            # Generate SKU based on product name, size, and color
            base = slugify(f"{self.product.name}-{self.size}-{self.color}")
            self.sku = base[:100]  # Ensure it fits in the field
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)
    
    def get_price(self):
        return Decimal(str(self.price or self.product.price))
