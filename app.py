
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

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
    
    def to_dict(self):
        return {
            'userID': self.userID,
            'displayName': f"{self.first_name} {self.last_name}",
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
    item_description = db.Column(db.String(255))
    item_price = db.Column(db.Numeric(10, 2), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('UserINFO.userID'))
    
    def to_dict(self):
        return {
            'id': self.itemID,
            'name': self.item_name,
            'description': self.item_description,
            'price': float(self.item_price),
            'vendorId': self.vendor_id
        }


class Order(db.Model):
    __tablename__ = 'UserCart'
    
    order_number = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_name = db.Column(db.String(255), nullable=False)
    item_details = db.Column(db.String(255), nullable=False)
    order_status = db.Column(db.Enum('pending', 'confirmed', 'shipped', 'out for delivery'), default='pending')
    user_id = db.Column(db.Integer, db.ForeignKey('UserINFO.userID'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'orderNumber': self.order_number,
            'itemName': self.item_name,
            'itemDetails': self.item_details,
            'status': self.order_status,
            'createdAt': self.created_at.isoformat()
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
    
    def to_dict(self):
        return {
            'id': self.req_id,
            'isRefund': self.is_refund,
            'isWarranty': self.is_warranty,
            'title': self.req_title,
            'description': self.req_desc,
            'status': self.req_status
        }


# ===== AUTHENTICATION ENDPOINTS =====

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'customer')
        
        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            return jsonify({'message': 'Invalid email or password'}), 401
        
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
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirmPassword')
        role = data.get('role', 'customer')
        
        # Validation
        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400
        
        if password != confirm_password:
            return jsonify({'message': 'Passwords do not match'}), 400
        
        if role == 'admin':
            return jsonify({'message': 'Admin self-registration not available'}), 403
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already registered'}), 409
        
        # Create new user
        username = email.split('@')[0]  # Use email prefix as username
        new_user = User(
            first_name='User',
            last_name='Account',
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_vendor=(role == 'vendor'),
            is_admin=False
        )
        
        db.session.add(new_user)8
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
    """Create a new product (vendor only)"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        # Check if user is vendor
        user = User.query.get(user_id)
        if not user or not user.is_vendor:
            return jsonify({'message': 'Only vendors can create products'}), 403
        
        new_product = Product(
            item_name=data.get('name'),
            item_description=data.get('description'),
            item_price=data.get('price'),
            vendor_id=user_id
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product': new_product.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating product: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a specific product"""
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404
        
        return jsonify(product.to_dict()), 200
    except Exception as e:
        return jsonify({'message': f'Error retrieving product: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update a product (vendor only)"""
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404
        
        data = request.get_json()
        user_id = data.get('userId')
        
        # Check authorization
        if product.vendor_id != user_id:
            return jsonify({'message': 'Unauthorized'}), 403
        
        if 'name' in data:
            product.item_name = data['name']
        if 'description' in data:
            product.item_description = data['description']
        if 'price' in data:
            product.item_price = data['price']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Product updated successfully',
            'product': product.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating product: {str(e)}'}), 500


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product (vendor only)"""
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), 404
        
        data = request.get_json() or {}
        user_id = data.get('userId')
        
        # Check authorization
        if product.vendor_id != user_id:
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
        
        new_order = Order(
            item_name=data.get('itemName'),
            item_details=data.get('itemDetails'),
            user_id=data.get('userId'),
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


@app.route('/api/cart/<int:order_id>', methods=['DELETE'])
def remove_from_cart(order_id):
    """Remove item from cart"""
    try:
        order = Order.query.get(order_id)
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
    """Get user's confirmed orders"""
    try:
        user_id = request.args.get('userId', type=int)
        if not user_id:
            return jsonify({'message': 'User ID required'}), 400
        
        orders = Order.query.filter(
            Order.user_id == user_id,
            Order.order_status != 'pending'
        ).all()
        
        return jsonify([order.to_dict() for order in orders]), 200
        
    except Exception as e:
        return jsonify({'message': f'Error retrieving orders: {str(e)}'}), 500


@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status (vendor/admin only)"""
    try:
        order = Order.query.get(order_id)
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
        is_admin = request.args.get('isAdmin', type=bool)
        
        if is_admin:
            requests_list = Request.query.all()
        else:
            requests_list = Request.query.filter_by(user_id=user_id).all()
        
        return jsonify([r.to_dict() for r in requests_list]), 200
        
    except Exception as e:
        return jsonify({'message': f'Error retrieving requests: {str(e)}'}), 500


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500


# ===== CREATE TABLES ON STARTUP =====

@app.before_request
def create_tables():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True, port=5000)