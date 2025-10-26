from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Product, CartItem, Category, Order, OrderItem, Customer
import uuid
from django.utils.text import slugify


def get_cart_count(request):
    """Helper function to get cart item count"""
    session_key = request.session.session_key
    if not session_key:
        return 0
    
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    else:
        cart_items = CartItem.objects.filter(session_key=session_key)
    
    return sum(item.quantity for item in cart_items)


def home(request):
    """Home page view"""
    categories = Category.objects.all()[:3]
    featured_products = Product.objects.filter(featured=True, available=True)[:8]
    new_products = Product.objects.filter(available=True).order_by('-created_at')[:8]
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'new_products': new_products,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/home.html', context)


def product_list(request):
    """Products listing page with filters and search"""
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Category filter
    category_slug = request.GET.get('category', '')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:  # newest
        products = products.order_by('-created_at')
    
    context = {
        'products': products,
        'categories': categories,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, product_id, slug):
    """Single product detail page"""
    product = get_object_or_404(Product, id=product_id, available=True)
    
    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/product_detail.html', context)


def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check stock
    if product.stock < 1:
        messages.error(request, f'Sorry, "{product.name}" is out of stock.')
        return redirect(request.META.get('HTTP_REFERER', 'products'))
    
    quantity = int(request.POST.get('quantity', 1))
    
    # Ensure session exists
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    # Handle cart for authenticated vs anonymous users
    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(
            product=product,
            user=request.user,
            defaults={'quantity': quantity}
        )
    else:
        cart_item, created = CartItem.objects.get_or_create(
            product=product,
            session_key=session_key,
            defaults={'quantity': quantity}
        )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    messages.success(request, f'"{product.name}" added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'products'))


def cart(request):
    """Shopping cart page"""
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    else:
        cart_items = CartItem.objects.filter(session_key=session_key)
    
    total = sum(item.total_price() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/cart.html', context)


def remove_from_cart(request, cart_item_id):
    """Remove item from cart"""
    item = get_object_or_404(CartItem, id=cart_item_id)
    
    # Check ownership
    if request.user.is_authenticated:
        if item.user != request.user:
            messages.error(request, 'You cannot remove this item.')
            return redirect('cart')
    else:
        if item.session_key != request.session.session_key:
            messages.error(request, 'You cannot remove this item.')
            return redirect('cart')
    
    item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


def update_cart(request, cart_item_id):
    """Update cart item quantity"""
    item = get_object_or_404(CartItem, id=cart_item_id)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            if quantity <= item.product.stock:
                item.quantity = quantity
                item.save()
                messages.success(request, 'Cart updated.')
            else:
                messages.error(request, f'Only {item.product.stock} items available.')
        else:
            item.delete()
            messages.success(request, 'Item removed from cart.')
    
    return redirect('cart')


def checkout(request):
    """Checkout page"""
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    else:
        cart_items = CartItem.objects.filter(session_key=session_key)
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    total = sum(item.total_price() for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/checkout.html', context)


def process_checkout(request):
    """Process checkout and create order"""
    if request.method != 'POST':
        return redirect('checkout')
    
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    # Get cart items
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    else:
        cart_items = CartItem.objects.filter(session_key=session_key)
    
    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')
    
    # Calculate total
    total = sum(item.total_price() for item in cart_items)
    shipping_cost = 0 if total >= 100 else 7.00
    
    # Create order
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        order_number=str(uuid.uuid4())[:13].upper(),
        full_name=request.POST.get('full_name'),
        email=request.POST.get('email'),
        phone=request.POST.get('phone'),
        address=request.POST.get('address'),
        city=request.POST.get('city'),
        postal_code=request.POST.get('postal_code'),
        country=request.POST.get('country', 'Tunisia'),
        total_amount=total,
        shipping_cost=shipping_cost,
        payment_method=request.POST.get('payment_method', 'cod'),
        status='pending'
    )
    
    # Create order items
    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            product_price=cart_item.product.price,
            quantity=cart_item.quantity
        )
        
        # Update stock
        cart_item.product.stock -= cart_item.quantity
        cart_item.product.save()
    
    # Clear cart
    cart_items.delete()
    
    # If payment method is Stripe, handle payment (placeholder for now)
    if order.payment_method == 'stripe':
        # TODO: Integrate Stripe payment here
        order.payment_completed = True
        order.save()
    
    messages.success(request, f'Order placed successfully! Order number: {order.order_number}')
    return redirect('order_confirmation', order_id=order.id)


def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user can view this order
    if request.user.is_authenticated:
        if order.user != request.user:
            messages.error(request, 'You do not have permission to view this order.')
            return redirect('home')
    
    context = {
        'order': order,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/order_confirmation.html', context)


def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        
        # Log the user in
        login(request, user)
        messages.success(request, 'Account created successfully!')
        return redirect('home')
    
    context = {
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/register.html', context)


def user_login(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Merge session cart with user cart
            session_key = request.session.session_key
            if session_key:
                session_cart_items = CartItem.objects.filter(session_key=session_key)
                for item in session_cart_items:
                    user_cart_item, created = CartItem.objects.get_or_create(
                        product=item.product,
                        user=user,
                        defaults={'quantity': item.quantity}
                    )
                    if not created:
                        user_cart_item.quantity += item.quantity
                        user_cart_item.save()
                    item.delete()
            
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.error(request, 'Invalid username or password.')
            return redirect('login')
    
    context = {
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/login.html', context)


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile(request):
    """User profile page"""
    orders = Order.objects.filter(user=request.user)
    order_count = orders.count()
    completed_orders = orders.filter(status='delivered').count()
    pending_orders = orders.filter(status__in=['pending', 'processing']).count()
    
    context = {
        'order_count': order_count,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/profile.html', context)


@login_required
def order_history(request):
    """User order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/order_history.html', context)


@login_required
def order_detail(request, order_id):
    """Single order detail"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/order_confirmation.html', context)


def contact(request):
    """Contact page with form submission"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Here you can add logic to:
        # 1. Send email to admin
        # 2. Save to database (create a ContactMessage model)
        # 3. Send auto-reply to customer
        
        # For now, just show a success message
        messages.success(
            request, 
            f'Thank you {name}! Your message has been received. We will get back to you soon at {email}.'
        )
        return redirect('contact')
    
    context = {
        'cart_count': get_cart_count(request)
    }
    return render(request, 'store/contact.html', context)
