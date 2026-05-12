
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import webbrowser, os

app = Flask(__name__, static_folder='.', static_url_path='')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:cset155@localhost/EcomDB'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===== DATABASE MODELS =====

class User(db.Model):
    __tablename__ = 'UserINFO'
    
    userID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    is_vendor = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'userID': self.userID,
            'displayName': f"{self.first_name} {self.last_name}",
            'firstName': self.first_name,
            'lastName': self.last_name,
            'email': self.email,
            'username': self.username,
            'features': self._get_features()
        }
    
    def _get_features(self):
        if self.is_admin:
            return ['Manage Users', 'View Reports', 'Manage System Settings']
        elif self.is_vendor:
            return ['Manage Products', 'View Orders', 'Monitor Sales']
        else:
            return ['Browse Products', 'Place Orders', 'Track Shipments']


class Product(db.Model):
    __tablename__ = 'storeItems'

    itemID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.Text)
    item_price = db.Column(db.Numeric(10, 2), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('UserINFO.userID'))
    gallery = db.Column(db.JSON, default=list)
    warranty_period = db.Column(db.String(100))
    category = db.Column(db.String(100))
    colors = db.Column(db.JSON, default=list)
    sizes = db.Column(db.JSON, default=list)
    stock_count = db.Column(db.Integer, default=0)

    vendor = db.relationship('User', foreign_keys=[vendor_id], lazy='joined')

    def to_dict(self):
        reviews = Review.query.filter_by(product_id=self.itemID).all()
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else None
        return {
            'id': self.itemID,
            'name': self.item_name,
            'description': self.item_description,
            'price': float(self.item_price),
            'vendorId': self.vendor_id,
            'vendorUsername': self.vendor.username if self.vendor else None,
            'gallery': self.gallery or [],
            'warrantyPeriod': self.warranty_period or '',
            'category': self.category or '',
            'colors': self.colors or [],
            'sizes': self.sizes or [],
            'stockCount': self.stock_count or 0,
            'avgRating': avg_rating,
            'reviewCount': len(reviews),
        }


class Order(db.Model):
    __tablename__ = 'UserCart'
    
    order_number = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_name = db.Column(db.String(255), nullable=False)
    item_details = db.Column(db.String(255), nullable=False)
    order_status = db.Column(db.Enum('pending', 'confirmed', 'shipped', 'out for delivery'), default='pending')
    user_id = db.Column(db.Integer, db.ForeignKey('UserINFO.userID'))
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        size, color = '', ''
        if self.item_details:
            for part in self.item_details.split(','):
                part = part.strip()
                if part.lower().startswith('size:'):
                    size = part[5:].strip()
                elif part.lower().startswith('color:'):
                    color = part[6:].strip()

        product = Product.query.filter_by(item_name=self.item_name).first()
        price = float(product.item_price) if product else 0
        vendor_email = product.vendor.email if product and product.vendor else 'N/A'

        return {
            'id': self.order_number,
            'product_name': self.item_name,
            'size': size,
            'color': color,
            'vendorEmail': vendor_email,
            'price': price,
            'quantity': self.quantity,
            'status': self.order_status,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class Request(db.Model):
    __tablename__ = 'requests'
    
    req_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    is_refund = db.Column(db.Boolean, default=False)
    is_warranty = db.Column(db.Boolean, default=False)
    req_title = db.Column(db.String(255), nullable=False)
    req_desc = db.Column(db.String(255), nullable=False)
    req_status = db.Column(db.Enum('pending', 'rejected', 'confirmed', 'processing', 'complete'), default='pending')
    user_id = db.Column(db.Integer, db.ForeignKey('UserINFO.userID'))
    order_id = db.Column(db.Integer, db.ForeignKey('UserCart.order_number'), nullable=True)

    order = db.relationship('Order', foreign_keys=[order_id], lazy='joined')

    def to_dict(self):
        req_type = 'warranty' if self.is_warranty else ('refund' if self.is_refund else 'complaint')
        return {
            'id': self.req_id,
            'type': req_type,
            'isRefund': self.is_refund,
            'isWarranty': self.is_warranty,
            'title': self.req_title,
            'description': self.req_desc,
            'status': self.req_status,
            'orderId': self.order_id,
            'orderProduct': self.order.item_name if self.order else None,
        }


class Review(db.Model):
    __tablename__ = 'reviews'

    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('storeItems.itemID'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('UserINFO.userID'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], lazy='joined')

    def to_dict(self):
        return {
            'id': self.review_id,
            'productId': self.product_id,
            'userId': self.user_id,
            'username': self.user.username if self.user else 'Unknown',
            'rating': self.rating,
            'text': self.review_text or '',
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ===== PAGE ROUTES =====

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/store')
def store():
    return app.send_static_file('store.html')

@app.route('/my-account')
def my_account():
    return app.send_static_file('my_account.html')

@app.route('/my-orders')
def my_orders():
    return app.send_static_file('my_orders.html')

@app.route('/received-orders')
def received_orders():
    return app.send_static_file('received_orders.html')


# ===== AUTHENTICATION ENDPOINTS =====

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password')
        role = data.get('role', 'customer')

        if not username or not password:
            return jsonify({'message': 'Username and password required'}), 400

        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password, password):
            return jsonify({'message': 'Invalid email or password'}), 401

        if not user.is_approved and not user.is_admin:
            return jsonify({'message': 'Your account is pending admin approval'}), 403

        # Check role authorization
        if role == 'vendor' and not user.is_vendor:
            return jsonify({'message': 'This account is not authorized as a vendor'}), 403
        if role == 'admin' and not user.is_admin:
            return jsonify({'message': 'This account is not authorized as an admin'}), 403
        
        return jsonify({
            'message': 'Login successful',
            'role': 'admin' if user.is_admin else ('vendor' if user.is_vendor else 'customer'),
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Login error: {str(e)}'}), 500


@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle user registration"""
    try:
        data = request.get_json()
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password')
        confirm_password = data.get('confirmPassword')
        role = data.get('role', 'customer')

        if not all([first_name, last_name, username, email, password]):
            return jsonify({'message': 'All fields are required'}), 400

        if password != confirm_password:
            return jsonify({'message': 'Passwords do not match'}), 400

        if role == 'admin':
            return jsonify({'message': 'Admin self-registration not available'}), 403

        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already registered'}), 409

        if User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username already taken'}), 409

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_vendor=(role == 'vendor'),
            is_admin=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'Account created successfully',
            'role': 'vendor' if new_user.is_vendor else 'customer',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Signup error: {str(e)}'}), 500


# ===== PRODUCT ENDPOINTS =====

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products"""
    try:
        products = Product.query.all()
        return jsonify([product.to_dict() for product in products]), 200
    except Exception as e:
        return jsonify({'message': f'Error retrieving products: {str(e)}'}), 500


@app.route('/api/products', methods=['POST'])
def create_product():
    try:
        data = request.get_json()
        user_id = data.get('userId')

        user = db.session.get(User, user_id)
        if not user or (not user.is_vendor and not user.is_admin):
            return jsonify({'message': 'Only vendors or admins can create products'}), 403

        vendor_id = data.get('vendorId', user_id) if user.is_admin else user_id

        new_product = Product(
            item_name=data.get('name'),
            item_description=data.get('description'),
            item_price=data.get('price'),
            vendor_id=vendor_id,
            gallery=data.get('gallery', []),
            category=data.get('category', ''),
            colors=data.get('colors', []),
            sizes=data.get('sizes', []),
            warranty_period=data.get('warrantyPeriod', ''),
            stock_count=data.get('stockCount', 0),
        )

        db.session.add(new_product)
        db.session.commit()

        return jsonify({'message': 'Product created successfully', 'product': new_product.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating product: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a specific product"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        return jsonify(product.to_dict()), 200
    except Exception as e:
        return jsonify({'message': f'Error retrieving product: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        data = request.get_json()
        user_id = data.get('userId')
        user = db.session.get(User, user_id)

        if not user or (not user.is_admin and product.vendor_id != user_id):
            return jsonify({'message': 'Unauthorized'}), 403

        if 'name' in data:
            product.item_name = data['name']
        if 'description' in data:
            product.item_description = data['description']
        if 'price' in data:
            product.item_price = data['price']
        if 'category' in data:
            product.category = data['category']
        if 'colors' in data:
            product.colors = data['colors']
        if 'sizes' in data:
            product.sizes = data['sizes']
        if 'warrantyPeriod' in data:
            product.warranty_period = data['warrantyPeriod']
        if 'stockCount' in data:
            product.stock_count = data['stockCount']
        if 'gallery' in data:
            product.gallery = data['gallery']

        db.session.commit()

        return jsonify({'message': 'Product updated successfully', 'product': product.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating product: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product (vendor only)"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        data = request.get_json() or {}
        user_id = data.get('userId')

        user = db.session.get(User, user_id) if user_id else None
        if not user or (not user.is_admin and product.vendor_id != user_id):
            return jsonify({'message': 'Unauthorized'}), 403

        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'message': 'Product deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting product: {str(e)}'}), 500


@app.route('/api/products/search', methods=['GET'])
def search_products():
    """Search products by name or description"""
    try:
        query = request.args.get('q', '')
        min_price = request.args.get('minPrice', type=float)
        max_price = request.args.get('maxPrice', type=float)
        
        products = Product.query
        
        if query:
            products = products.filter(
                (Product.item_name.ilike(f'%{query}%')) |
                (Product.item_description.ilike(f'%{query}%'))
            )
        
        if min_price is not None:
            products = products.filter(Product.item_price >= min_price)
        
        if max_price is not None:
            products = products.filter(Product.item_price <= max_price)
        
        results = products.all()
        return jsonify([product.to_dict() for product in results]), 200
        
    except Exception as e:
        return jsonify({'message': f'Search error: {str(e)}'}), 500


# ===== CART/ORDER ENDPOINTS =====

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Get user's cart/orders"""
    try:
        user_id = request.args.get('userId', type=int)
        if not user_id:
            return jsonify({'message': 'User ID required'}), 400
        
        orders = Order.query.filter_by(user_id=user_id, order_status='pending').all()
        return jsonify([order.to_dict() for order in orders]), 200
        
    except Exception as e:
        return jsonify({'message': f'Error retrieving cart: {str(e)}'}), 500


@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    """Add item to cart"""
    try:
        data = request.get_json()

        product = db.session.get(Product, data.get('productId'))
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        qty = int(data.get('quantity', 1))
        if product.stock_count < qty:
            return jsonify({'message': 'Not enough stock available'}), 400

        details_parts = []
        if data.get('size'):
            details_parts.append(f"Size: {data['size']}")
        if data.get('color'):
            details_parts.append(f"Color: {data['color']}")
        item_details = ', '.join(details_parts) or 'No options selected'

        product.stock_count -= qty

        new_order = Order(
            item_name=product.item_name,
            item_details=item_details,
            user_id=data.get('userId'),
            quantity=qty,
            order_status='pending'
        )
        
        db.session.add(new_order)
        db.session.commit()
        
        return jsonify({
            'message': 'Item added to cart',
            'order': new_order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error adding to cart: {str(e)}'}), 500


@app.route('/api/cart/<int:order_id>', methods=['PUT'])
def update_cart_item(order_id):
    """Update cart item quantity"""
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'message': 'Item not found'}), 404

        if order.order_status != 'pending':
            return jsonify({'message': 'Cannot modify confirmed orders'}), 400

        data = request.get_json()
        if 'quantity' in data:
            order.quantity = data['quantity']

        db.session.commit()
        return jsonify({'message': 'Cart updated', 'order': order.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating cart: {str(e)}'}), 500


@app.route('/api/cart/<int:order_id>', methods=['DELETE'])
def remove_from_cart(order_id):
    """Remove item from cart"""
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'message': 'Item not found'}), 404
        
        if order.order_status != 'pending':
            return jsonify({'message': 'Cannot remove confirmed orders'}), 400
        
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({'message': 'Item removed from cart'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error removing from cart: {str(e)}'}), 500


@app.route('/api/checkout', methods=['POST'])
def checkout():
    """Checkout and confirm orders"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        # Update all pending orders to confirmed
        orders = Order.query.filter_by(user_id=user_id, order_status='pending').all()
        
        if not orders:
            return jsonify({'message': 'No items in cart'}), 400
        
        for order in orders:
            order.order_status = 'confirmed'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Checkout successful',
            'orders': [order.to_dict() for order in orders]
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Checkout error: {str(e)}'}), 500


# ===== ORDER ENDPOINTS =====

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get orders — customer by userId, vendor by vendorId, all for admin"""
    try:
        user_id = request.args.get('userId', type=int)
        vendor_id = request.args.get('vendorId', type=int)
        is_admin = request.args.get('isAdmin', '').lower() == 'true'

        if is_admin:
            orders = Order.query.filter(Order.order_status != 'pending').all()
        elif vendor_id:
            vendor_product_names = [
                p.item_name for p in Product.query.filter_by(vendor_id=vendor_id).all()
            ]
            orders = Order.query.filter(
                Order.item_name.in_(vendor_product_names),
                Order.order_status != 'pending'
            ).all()
        elif user_id:
            orders = Order.query.filter(
                Order.user_id == user_id,
                Order.order_status != 'pending'
            ).all()
        else:
            return jsonify({'message': 'User ID required'}), 400

        return jsonify([order.to_dict() for order in orders]), 200

    except Exception as e:
        return jsonify({'message': f'Error retrieving orders: {str(e)}'}), 500


@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status (vendor/admin only)"""
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({'message': 'Order not found'}), 404
        
        data = request.get_json()
        new_status = data.get('status')
        
        valid_statuses = ['pending', 'confirmed', 'shipped', 'out for delivery']
        if new_status not in valid_statuses:
            return jsonify({'message': 'Invalid status'}), 400
        
        order.order_status = new_status
        db.session.commit()
        
        return jsonify({
            'message': 'Order status updated',
            'order': order.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating order: {str(e)}'}), 500


# ===== PRODUCT GALLERY ENDPOINTS =====

@app.route('/api/products/<int:product_id>/gallery', methods=['POST'])
def add_gallery_image(product_id):
    """Add an image URL to a product's gallery"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        data = request.get_json()
        image_url = data.get('imageUrl')
        if not image_url:
            return jsonify({'message': 'imageUrl required'}), 400

        gallery = list(product.gallery or [])
        gallery.append(image_url)
        product.gallery = gallery
        db.session.commit()

        return jsonify({'message': 'Image added', 'gallery': product.gallery}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error adding image: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>/gallery/<int:image_index>', methods=['DELETE'])
def delete_gallery_image(product_id, image_index):
    """Remove an image from a product's gallery by index"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404

        gallery = list(product.gallery or [])
        if image_index < 0 or image_index >= len(gallery):
            return jsonify({'message': 'Image index out of range'}), 404

        gallery.pop(image_index)
        product.gallery = gallery
        db.session.commit()

        return jsonify({'message': 'Image deleted', 'gallery': product.gallery}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting image: {str(e)}'}), 500


# ===== REQUESTS (COMPLAINTS/WARRANTY) ENDPOINTS =====

@app.route('/api/complaints', methods=['POST'])
def create_complaint():
    """Create a complaint"""
    try:
        data = request.get_json()
        
        new_request = Request(
            is_refund=False,
            is_warranty=False,
            req_title=data.get('title'),
            req_desc=data.get('description'),
            user_id=data.get('userId'),
            req_status='pending'
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return jsonify({
            'message': 'Complaint submitted',
            'request': new_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating complaint: {str(e)}'}), 500


@app.route('/api/warranty', methods=['POST'])
def create_warranty():
    """Create a warranty request"""
    try:
        data = request.get_json()
        
        new_request = Request(
            is_refund=False,
            is_warranty=True,
            req_title=data.get('title'),
            req_desc=data.get('description'),
            user_id=data.get('userId'),
            req_status='pending'
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return jsonify({
            'message': 'Warranty request submitted',
            'request': new_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating warranty request: {str(e)}'}), 500


@app.route('/api/refund', methods=['POST'])
def create_refund():
    """Create a refund request"""
    try:
        data = request.get_json()
        
        new_request = Request(
            is_refund=True,
            is_warranty=False,
            req_title=data.get('title'),
            req_desc=data.get('description'),
            user_id=data.get('userId'),
            req_status='pending'
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return jsonify({
            'message': 'Refund request submitted',
            'request': new_request.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating refund request: {str(e)}'}), 500


@app.route('/api/requests', methods=['GET'])
def get_requests():
    """Get user's requests (admin can see all)"""
    try:
        user_id = request.args.get('userId', type=int)
        is_admin = request.args.get('isAdmin', '').lower() == 'true'
        
        if is_admin:
            requests_list = Request.query.all()
        else:
            requests_list = Request.query.filter_by(user_id=user_id).all()
        
        return jsonify([r.to_dict() for r in requests_list]), 200
        
    except Exception as e:
        return jsonify({'message': f'Error retrieving requests: {str(e)}'}), 500


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(_error):
    return jsonify({'message': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(_error):
    return jsonify({'message': 'Internal server error'}), 500


# ===== VENDOR LIST ENDPOINT =====

@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    try:
        vendors = User.query.filter_by(is_vendor=True, is_approved=True).all()
        return jsonify([{'userID': v.userID, 'username': v.username, 'email': v.email} for v in vendors]), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ===== ADMIN USER APPROVAL ENDPOINTS =====

@app.route('/api/admin/pending-users', methods=['GET'])
def get_pending_users():
    try:
        pending = User.query.filter_by(is_approved=False, is_admin=False).all()
        return jsonify([{
            'userID': u.userID,
            'email': u.email,
            'username': u.username,
            'is_vendor': u.is_vendor
        } for u in pending]), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@app.route('/api/admin/users/<int:user_id>/approve', methods=['PUT'])
def approve_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        user.is_approved = True
        db.session.commit()
        return jsonify({'message': 'User approved'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


@app.route('/api/admin/users/<int:user_id>/reject', methods=['DELETE'])
def reject_user(user_id):
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User rejected and removed'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ===== REVIEW ENDPOINTS =====

@app.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def get_reviews(product_id):
    try:
        reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
        avg = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
        return jsonify({'reviews': [r.to_dict() for r in reviews], 'average': avg, 'count': len(reviews)}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>/reviews', methods=['POST'])
def add_review(product_id):
    try:
        data = request.get_json()
        user_id = data.get('userId')
        rating = data.get('rating')
        if not user_id or not rating or not (1 <= int(rating) <= 5):
            return jsonify({'message': 'userId and rating (1–5) required'}), 400
        if Review.query.filter_by(product_id=product_id, user_id=user_id).first():
            return jsonify({'message': 'You have already reviewed this product'}), 409
        review = Review(
            product_id=product_id,
            user_id=user_id,
            rating=int(rating),
            review_text=data.get('text', '')
        )
        db.session.add(review)
        db.session.commit()
        return jsonify({'message': 'Review submitted', 'review': review.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ===== UNIFIED REQUEST ENDPOINT =====

@app.route('/api/requests', methods=['POST'])
def create_request():
    try:
        data = request.get_json()
        req_type = data.get('type', 'complaint')
        title = data.get('title', '').strip()
        desc = data.get('description', '').strip()
        if not title or not desc:
            return jsonify({'message': 'Title and description are required'}), 400

        order_id = data.get('orderId')
        if req_type in ('refund', 'warranty') and not order_id:
            return jsonify({'message': 'Please select an order for refund/warranty requests'}), 400

        new_req = Request(
            is_refund=(req_type == 'refund'),
            is_warranty=(req_type == 'warranty'),
            req_title=title,
            req_desc=desc,
            user_id=data.get('userId'),
            order_id=order_id,
            req_status='pending'
        )
        db.session.add(new_req)
        db.session.commit()
        return jsonify({'message': 'Request submitted', 'request': new_req.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        webbrowser.open('http://localhost:5000')
    app.run(debug=True, port=5000)