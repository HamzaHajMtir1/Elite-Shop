from django.core.management.base import BaseCommand
from django.utils.text import slugify
from store.models import Category, Product


class Command(BaseCommand):
    help = 'Populate the database with sample products and categories'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Creating sample categories...'))
        
        # Create Categories
        categories_data = [
            {
                'name': 'Electronics',
                'description': 'Latest electronic gadgets and devices'
            },
            {
                'name': 'Fashion',
                'description': 'Trendy clothing and accessories'
            },
            {
                'name': 'Home & Living',
                'description': 'Everything for your home'
            },
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=slugify(cat_data['name']),
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description']
                }
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created category: {category.name}'))
        
        self.stdout.write(self.style.SUCCESS('\nCreating sample products...'))
        
        # Create Products
        products_data = [
            # Electronics
            {
                'name': 'Wireless Headphones Pro',
                'category': 'Electronics',
                'price': 149.99,
                'old_price': 199.99,
                'description': 'Premium wireless headphones with active noise cancellation and 30-hour battery life.',
                'stock': 25,
                'featured': True
            },
            {
                'name': 'Smart Watch Series 5',
                'category': 'Electronics',
                'price': 299.99,
                'old_price': 349.99,
                'description': 'Advanced fitness tracking, heart rate monitor, and mobile notifications.',
                'stock': 15,
                'featured': True
            },
            {
                'name': 'Bluetooth Speaker',
                'category': 'Electronics',
                'price': 79.99,
                'description': 'Portable waterproof speaker with incredible sound quality.',
                'stock': 40,
                'featured': False
            },
            {
                'name': 'Wireless Keyboard & Mouse',
                'category': 'Electronics',
                'price': 59.99,
                'description': 'Ergonomic wireless keyboard and mouse combo for comfortable typing.',
                'stock': 30,
                'featured': False
            },
            {
                'name': 'USB-C Hub Adapter',
                'category': 'Electronics',
                'price': 39.99,
                'description': '7-in-1 USB-C hub with HDMI, USB 3.0, and SD card reader.',
                'stock': 50,
                'featured': False
            },
            
            # Fashion
            {
                'name': 'Premium Leather Jacket',
                'category': 'Fashion',
                'price': 189.99,
                'old_price': 249.99,
                'description': 'Genuine leather jacket with modern design and comfortable fit.',
                'stock': 12,
                'featured': True
            },
            {
                'name': 'Designer Sunglasses',
                'category': 'Fashion',
                'price': 129.99,
                'description': 'UV protection sunglasses with polarized lenses.',
                'stock': 20,
                'featured': True
            },
            {
                'name': 'Casual Sneakers',
                'category': 'Fashion',
                'price': 89.99,
                'old_price': 119.99,
                'description': 'Comfortable all-day wear sneakers in multiple colors.',
                'stock': 35,
                'featured': False
            },
            {
                'name': 'Cotton T-Shirt Pack',
                'category': 'Fashion',
                'price': 49.99,
                'description': 'Premium cotton t-shirts, pack of 3 in assorted colors.',
                'stock': 50,
                'featured': False
            },
            {
                'name': 'Denim Jeans',
                'category': 'Fashion',
                'price': 69.99,
                'description': 'Classic fit denim jeans with stretch comfort.',
                'stock': 28,
                'featured': False
            },
            
            # Home & Living
            {
                'name': 'Smart LED Bulbs (4-Pack)',
                'category': 'Home & Living',
                'price': 45.99,
                'description': 'WiFi-enabled color-changing LED bulbs compatible with voice assistants.',
                'stock': 40,
                'featured': True
            },
            {
                'name': 'Premium Coffee Maker',
                'category': 'Home & Living',
                'price': 159.99,
                'old_price': 199.99,
                'description': 'Programmable coffee maker with thermal carafe and auto-brew.',
                'stock': 18,
                'featured': True
            },
            {
                'name': 'Memory Foam Pillow',
                'category': 'Home & Living',
                'price': 39.99,
                'description': 'Ergonomic memory foam pillow for better sleep quality.',
                'stock': 45,
                'featured': False
            },
            {
                'name': 'Stainless Steel Cookware Set',
                'category': 'Home & Living',
                'price': 199.99,
                'old_price': 279.99,
                'description': '10-piece professional cookware set with non-stick coating.',
                'stock': 10,
                'featured': False
            },
            {
                'name': 'Decorative Wall Mirror',
                'category': 'Home & Living',
                'price': 79.99,
                'description': 'Modern round mirror perfect for any room.',
                'stock': 22,
                'featured': False
            },
        ]
        
        for product_data in products_data:
            category_name = product_data.pop('category')
            category = categories[category_name]
            
            product, created = Product.objects.get_or_create(
                slug=slugify(product_data['name']),
                defaults={
                    **product_data,
                    'category': category,
                    'available': True
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created product: {product.name}'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Total Categories: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'Total Products: {Product.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('='*50))
