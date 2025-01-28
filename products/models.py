from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    
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

class Product(models.Model):
    CLOTHING_SIZES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
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
    ]
    
    PERFUME_SIZES = [
        ('30ml', '30ml'),
        ('50ml', '50ml'),
        ('65ml', '65ml'),
        ('75ml', '75ml'),
        ('100ml', '100ml'),
        ('200ml', '200ml'),
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
    ]
    
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    available_sizes = models.CharField(max_length=200, help_text='Enter sizes separated by commas. For clothes: S,M,L. For shoes: 38,39,40. For perfumes: 50ml,100ml')
    colors = models.CharField(max_length=200, help_text='Enter colors separated by commas (e.g., red,blue,black)', blank=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
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
    
    def get_price(self):
        return self.sale_price if self.sale_price else self.price
    
    @property
    def discount_percentage(self):
        if self.sale_price:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return round(discount)
        return 0
    
    @property
    def size_list(self):
        return [size.strip() for size in self.available_sizes.split(',')] if self.available_sizes else []
    
    @property
    def color_list(self):
        return [color.strip() for color in self.colors.split(',')] if self.colors else []

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-is_primary', 'id']
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
    def save(self, *args, **kwargs):
        if self.is_primary:
            # Set all other images of this product to not primary
            ProductImage.objects.filter(product=self.product).update(is_primary=False)
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
