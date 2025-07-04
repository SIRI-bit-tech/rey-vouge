from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem, Payment
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.utils.html import format_html
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from core.utils import send_email
import csv
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ('product', 'quantity', 'price', 'get_total_price')
    can_delete = False
    extra = 0
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_info', 'total_amount', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__email', 'shipping_address')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'total_amount')
    inlines = [OrderItemInline]
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'export_orders']
    change_list_template = 'admin/orders/order/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-csv/', self.export_orders_csv, name='export_orders_csv'),
            path('analytics/', self.order_analytics, name='order_analytics'),
        ]
        return custom_urls + urls
    
    def customer_info(self, obj):
        return format_html(
            '<strong>{}:</strong> {}<br>'
            '<strong>Phone:</strong> {}<br>'
            '<strong>Address:</strong> {}',
            obj.user.email,
            f"{obj.user.first_name} {obj.user.last_name}",
            obj.user.phone_number,
            obj.shipping_address
        )
    customer_info.short_description = 'Customer Information'
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self._send_status_update_emails(queryset, 'processing')
        self.message_user(request, f'Successfully marked {updated} orders as processing')
    mark_as_processing.short_description = "Mark selected orders as processing"
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.update(status='shipped')
        self._send_status_update_emails(queryset, 'shipped')
        self.message_user(request, f'Successfully marked {updated} orders as shipped')
    mark_as_shipped.short_description = "Mark selected orders as shipped"
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered')
        self._send_status_update_emails(queryset, 'delivered')
        self.message_user(request, f'Successfully marked {updated} orders as delivered')
    mark_as_delivered.short_description = "Mark selected orders as delivered"

    def export_orders_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="orders_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number', 'Customer Email', 'Status', 'Payment Status',
            'Total Amount', 'Created At', 'Items'
        ])
        
        orders = self.get_queryset(request)
        for order in orders:
            items = ", ".join([f"{item.product.name} (x{item.quantity})" for item in order.items.all()])
            writer.writerow([
                order.order_number,
                order.user.email,
                order.status,
                order.payment_status,
                order.total_amount,
                order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                items
            ])
        
        return response

    def order_analytics(self, request):
        # Date ranges
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Daily orders and revenue
        daily_stats = list(Order.objects.filter(
            created_at__range=(start_date, end_date)
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total_orders=Count('id'),
            total_revenue=Sum('total_amount')
        ).order_by('date'))
        
        # Convert date objects to ISO format for JSON serialization
        for stat in daily_stats:
            stat['date'] = stat['date'].isoformat()
            stat['total_revenue'] = float(stat['total_revenue'] if stat['total_revenue'] else 0)
        
        # Status breakdown
        status_breakdown = Order.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Payment status breakdown
        payment_breakdown = Order.objects.values('payment_status').annotate(
            count=Count('id')
        ).order_by('payment_status')
        
        # Average order value
        avg_order_value = Order.objects.filter(
            status__in=['processing', 'shipped', 'delivered'],
            payment_status='paid'
        ).aggregate(
            avg_value=Sum('total_amount') / Count('id')
        )['avg_value'] or 0
        
        context = {
            'title': 'Order Analytics',
            'daily_stats': daily_stats,
            'status_breakdown': status_breakdown,
            'payment_breakdown': payment_breakdown,
            'avg_order_value': float(avg_order_value),
            'start_date': start_date,
            'end_date': end_date,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/orders/analytics.html', context)
    
    def _send_status_update_emails(self, orders, status):
        for order in orders:
            context = {
                'order': order,
                'status': status.title(),
                'site_url': settings.SITE_DOMAIN
            }
            
            try:
                send_email(
                    subject=f'Order {order.order_number} Status Update',
                    template_name='orders/email/shipping_update.html',
                    to_email=order.user.email,
                    to_name=f"{order.user.first_name} {order.user.last_name}",
                    context=context
                )
            except Exception as e:
                messages.error(self.request, f'Failed to send email for order {order.order_number}: {str(e)}')

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('get_total_price_display',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'modified_at', 'get_total_display', 'is_active', 'reminder_count')
    list_filter = ('is_active', 'created_at', 'modified_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'modified_at', 'get_total_display')
    inlines = [CartItemInline]
    date_hierarchy = 'created_at'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'order', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reference', 'order__order_number')
    readonly_fields = ('reference', 'created_at', 'modified_at')
