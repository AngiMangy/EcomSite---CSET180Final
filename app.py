
from flask import Flask, jsonify, request

app = Flask(__name__, static_folder='.', static_url_path='')

# Chat storage: {chat_id: [ {sender, receiver, text, date}, ... ]}
CHATS = {}

# Helper: Generate chat_id for customer-vendor or customer-admin (for complaint)
def get_chat_id_customer_vendor(customer_email, vendor_email):
    return f"customer:{customer_email.lower()}|vendor:{vendor_email.lower()}"

def get_chat_id_complaint(complaint_id):
    return f"complaint:{complaint_id}"
# New: Customer sends message to vendor
@app.route('/api/chat/customer-vendor', methods=['POST'])
def api_chat_customer_vendor():
    """Customer sends/receives message with a vendor."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    customer_email = data.get('customerEmail', '').strip().lower()
    vendor_email = data.get('vendorEmail', '').strip().lower()
    sender = data.get('sender', '').strip().lower()  # must be customer or vendor email
    text = data.get('text', '').strip()

    if not customer_email or not vendor_email or not sender or not text:
        return jsonify({'status': 'error', 'message': 'customerEmail, vendorEmail, sender, and text are required.'}), 400

    # Validate sender is either customer or vendor
    if sender not in [customer_email, vendor_email]:
        return jsonify({'status': 'error', 'message': 'Sender must be customer or vendor.'}), 400

    # Validate users
    customer = find_user(customer_email, 'customer')
    vendor = find_user(vendor_email, 'vendor')
    if customer is None or vendor is None:
        return jsonify({'status': 'error', 'message': 'Customer or vendor not found.'}), 404

    from datetime import datetime
    chat_id = get_chat_id_customer_vendor(customer_email, vendor_email)
    message = {
        'sender': sender,
        'receiver': vendor_email if sender == customer_email else customer_email,
        'text': text,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if chat_id not in CHATS:
        CHATS[chat_id] = []
    CHATS[chat_id].append(message)
    return jsonify({'status': 'success', 'message': 'Message sent.', 'chat': CHATS[chat_id]})


# New: Get chat history between customer and vendor
@app.route('/api/chat/customer-vendor', methods=['GET'])
def api_get_chat_customer_vendor():
    customer_email = request.args.get('customerEmail', '').strip().lower()
    vendor_email = request.args.get('vendorEmail', '').strip().lower()
    if not customer_email or not vendor_email:
        return jsonify({'status': 'error', 'message': 'customerEmail and vendorEmail are required.'}), 400
    chat_id = get_chat_id_customer_vendor(customer_email, vendor_email)
    chat = CHATS.get(chat_id, [])
    return jsonify({'status': 'success', 'chat': chat})


# New: Customer/admin chat for a complaint (return/refund/warranty)
@app.route('/api/chat/complaint', methods=['POST'])
def api_chat_complaint():
    """Customer or admin sends message about a complaint."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    complaint_id = data.get('complaintId')
    sender = data.get('sender', '').strip().lower()
    text = data.get('text', '').strip()

    if not complaint_id or not sender or not text:
        return jsonify({'status': 'error', 'message': 'complaintId, sender, and text are required.'}), 400

    # Find complaint
    complaint = next((c for c in COMPLAINTS if c['id'] == complaint_id), None)
    if complaint is None:
        return jsonify({'status': 'error', 'message': 'Complaint not found.'}), 404

    # Only allow customer or assigned admin to chat
    allowed = [complaint['email']]
    if complaint['adminEmail']:
        allowed.append(complaint['adminEmail'])
    if sender not in allowed:
        return jsonify({'status': 'error', 'message': 'Sender not allowed for this complaint chat.'}), 403

    from datetime import datetime
    chat_id = get_chat_id_complaint(complaint_id)
    receiver = allowed[1] if sender == allowed[0] and len(allowed) > 1 else allowed[0]
    message = {
        'sender': sender,
        'receiver': receiver,
        'text': text,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if chat_id not in CHATS:
        CHATS[chat_id] = []
    CHATS[chat_id].append(message)
    return jsonify({'status': 'success', 'message': 'Message sent.', 'chat': CHATS[chat_id]})


# New: Get chat history for a complaint
@app.route('/api/chat/complaint', methods=['GET'])
def api_get_chat_complaint():
    complaint_id = request.args.get('complaintId')
    if not complaint_id:
        return jsonify({'status': 'error', 'message': 'complaintId is required.'}), 400
    chat_id = get_chat_id_complaint(int(complaint_id))
    chat = CHATS.get(chat_id, [])
    return jsonify({'status': 'success', 'chat': chat})
# Complaints storage: [{id, product_id, email, date, title, description, demand, status, adminDecision, adminEmail}]
COMPLAINTS = []
NEXT_COMPLAINT_ID = 1
# New: Customer submits a complaint about a product
@app.route('/api/products/<int:product_id>/complaints', methods=['POST'])
def api_add_complaint(product_id):
    """Customer submits a complaint (return, refund, warranty claim)."""
    global NEXT_COMPLAINT_ID
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    demand = data.get('demand', '').strip().lower()  # 'return', 'refund', 'warranty'

    if not email or not title or not description or not demand:
        return jsonify({'status': 'error', 'message': 'Email, title, description, and demand are required.'}), 400

    if demand not in ['return', 'refund', 'warranty']:
        return jsonify({'status': 'error', 'message': 'Demand must be return, refund, or warranty.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    from datetime import datetime
    complaint = {
        'id': NEXT_COMPLAINT_ID,
        'product_id': product_id,
        'email': email,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'title': title,
        'description': description,
        'demand': demand,
        'status': 'pending',  # pending -> rejected/confirmed -> processing -> complete
        'adminDecision': None,
        'adminEmail': None
    }
    NEXT_COMPLAINT_ID += 1
    COMPLAINTS.append(complaint)
    return jsonify({'status': 'success', 'message': 'Complaint submitted.', 'complaint': complaint}), 201


# New: Admin reviews a complaint (pending -> rejected/confirmed)
@app.route('/api/complaints/<int:complaint_id>/review', methods=['POST'])
def api_review_complaint(complaint_id):
    """Admin reviews a complaint: confirm or reject."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    user, error = authenticate_admin(data)
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    decision = data.get('decision', '').strip().lower()  # 'confirm' or 'reject'
    if decision not in ['confirm', 'reject']:
        return jsonify({'status': 'error', 'message': 'Decision must be confirm or reject.'}), 400

    complaint = next((c for c in COMPLAINTS if c['id'] == complaint_id), None)
    if complaint is None:
        return jsonify({'status': 'error', 'message': 'Complaint not found.'}), 404

    if complaint['status'] != 'pending':
        return jsonify({'status': 'error', 'message': 'Complaint is not pending.'}), 400

    if decision == 'confirm':
        complaint['status'] = 'confirmed'
    else:
        complaint['status'] = 'rejected'
    complaint['adminDecision'] = decision
    complaint['adminEmail'] = user['email']
    return jsonify({'status': 'success', 'message': f'Complaint {decision}ed.', 'complaint': complaint})


# New: Admin updates complaint status (confirmed -> processing -> complete)
@app.route('/api/complaints/<int:complaint_id>/status', methods=['PUT'])
def api_update_complaint_status(complaint_id):
    """Admin updates complaint status: confirmed -> processing -> complete."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    user, error = authenticate_admin(data)
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    complaint = next((c for c in COMPLAINTS if c['id'] == complaint_id), None)
    if complaint is None:
        return jsonify({'status': 'error', 'message': 'Complaint not found.'}), 404

    # Only allow status progression
    if complaint['status'] == 'confirmed':
        complaint['status'] = 'processing'
    elif complaint['status'] == 'processing':
        complaint['status'] = 'complete'
    else:
        return jsonify({'status': 'error', 'message': 'Complaint status cannot be updated from current state.'}), 400
    return jsonify({'status': 'success', 'message': f'Complaint status updated to {complaint["status"]}.', 'complaint': complaint})


# New: Get complaints for a product or customer (optional filtering)
@app.route('/api/complaints', methods=['GET'])
def api_get_complaints():
    """Get complaints, optionally filter by product_id or email."""
    product_id = request.args.get('product_id', '').strip()
    email = request.args.get('email', '').strip().lower()
    filtered = COMPLAINTS
    if product_id:
        try:
            product_id = int(product_id)
            filtered = [c for c in filtered if c['product_id'] == product_id]
        except ValueError:
            pass
    if email:
        filtered = [c for c in filtered if c['email'] == email]
    return jsonify({'status': 'success', 'complaints': filtered})
# Reviews storage: {product_id: [ {email, reviewerName, rating, description, date}, ... ]}
REVIEWS = {}
# New: Add a review to a product
@app.route('/api/products/<int:product_id>/reviews', methods=['POST'])
def api_add_review(product_id):
    """Customer writes a review for a product."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()
    rating = data.get('rating')
    description = data.get('description', '').strip()

    if not email or rating is None or not description:
        return jsonify({'status': 'error', 'message': 'Email, rating, and description are required.'}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'status': 'error', 'message': 'Rating must be between 1 and 5.'}), 400
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Rating must be a number between 1 and 5.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    from datetime import datetime
    review = {
        'email': email,
        'reviewerName': user['displayName'],
        'rating': rating,
        'description': description,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if product_id not in REVIEWS:
        REVIEWS[product_id] = []
    REVIEWS[product_id].append(review)
    return jsonify({'status': 'success', 'message': 'Review added.', 'review': review}), 201


# New: Get reviews for a product (with sorting/filtering)
@app.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def api_get_reviews(product_id):
    """Get reviews for a product, with optional sorting and filtering by rating."""
    sort_by = request.args.get('sortBy', '').strip().lower()  # 'time' or 'rating'
    filter_rating = request.args.get('rating', '').strip()

    reviews = REVIEWS.get(product_id, []).copy()

    # Filter by rating if provided
    if filter_rating:
        try:
            filter_rating = int(filter_rating)
            reviews = [r for r in reviews if r['rating'] == filter_rating]
        except ValueError:
            pass

    # Sort reviews
    if sort_by == 'rating':
        reviews.sort(key=lambda r: r['rating'], reverse=True)
    else:  # Default or 'time'
        reviews.sort(key=lambda r: r['date'], reverse=True)

    return jsonify({'status': 'success', 'reviews': reviews})
from flask import Flask, jsonify, request

app = Flask(__name__, static_folder='.', static_url_path='')

USERS = [
    {
        'role': 'customer',
        'email': 'user@example.com',
        'password': 'user123',
        'displayName': 'Marketplace Buyer',
        'features': ['Browse products', 'Place orders', 'View purchase history']
    },
    {
        'role': 'vendor',
        'email': 'vendor@example.com',
        'password': 'vendor123',
        'vendorCode': 'VENDORCODE123',
        'displayName': 'Vendor Partner',
        'features': ['Manage inventory', 'Process orders', 'View sales analytics']
    },
    {
        'role': 'admin',
        'email': 'admin@example.com',
        'password': 'admin123',
        'adminCode': 'ADMINCODE',
        'displayName': 'Platform Admin',
        'features': ['Manage users', 'Review reports', 'Approve vendors']
    }
]

PRODUCTS = [
    {
        'id': 1,
        'name': 'Wireless Headphones',
        'description': 'Noise cancellation, long battery life, and fast shipping.',
        'price': 129.99,
        'vendorEmail': 'vendor@example.com',
        'category': 'Electronics',
        'color': 'Black',
        'size': 'One Size',
        'inStock': True,
        'gallery': [
            'https://via.placeholder.com/400x400?text=Headphones+1',
            'https://via.placeholder.com/400x400?text=Headphones+2',
            'https://via.placeholder.com/400x400?text=Headphones+3'
        ]
    },
    {
        'id': 2,
        'name': 'Home Office Desk',
        'description': 'Modern design with cable management and adjustable height.',
        'price': 249.99,
        'vendorEmail': 'vendor@example.com',
        'category': 'Furniture',
        'color': 'White',
        'size': 'Large',
        'inStock': True,
        'gallery': [
            'https://via.placeholder.com/400x400?text=Desk+1',
            'https://via.placeholder.com/400x400?text=Desk+2',
            'https://via.placeholder.com/400x400?text=Desk+3'
        ]
    },
    {
        'id': 3,
        'name': 'Fashion Sneakers',
        'description': 'Comfortable daily wear with premium materials.',
        'price': 89.99,
        'vendorEmail': 'vendor@example.com',
        'category': 'Fashion',
        'color': 'Blue',
        'size': 'Medium',
        'inStock': False,
        'gallery': [
            'https://via.placeholder.com/400x400?text=Sneakers+1',
            'https://via.placeholder.com/400x400?text=Sneakers+2',
            'https://via.placeholder.com/400x400?text=Sneakers+3'
        ]
    }
]

NEXT_PRODUCT_ID = 4

# Cart storage: {email: {'items': [{id, product_id, quantity, size, color, price}, ...]}}
CARTS = {}

# Order storage: [{id, email, date, items: [...], totalPrice, status, vendorConfirmed}]
ORDERS = []
NEXT_ORDER_ID = 1


def find_user(email, role):
    return next((u for u in USERS if u['role'] == role and u['email'].lower() == email.lower()), None)


def find_product(product_id):
    return next((p for p in PRODUCTS if p['id'] == product_id), None)


def get_default_features(role):
    return {
        'customer': ['Browse products', 'Place orders', 'View purchase history'],
        'vendor': ['Manage inventory', 'Process orders', 'View sales analytics']
    }.get(role, [])


def get_request_json():
    data = request.get_json(silent=True)
    if data is None:
        return None, ('Request body must be valid JSON.', 400)
    return data, None


def authenticate_vendor(data):
    role = data.get('role', '').strip().lower()
    email = data.get('email', '').strip().lower()
    vendor_code = data.get('vendorCode', '').strip()

    if role != 'vendor':
        return None, ('Only vendors may manage products.', 403)
    if not email or not vendor_code:
        return None, ('Vendor email and Vendor Shop ID are required.', 400)

    user = find_user(email, 'vendor')
    if user is None:
        return None, ('Vendor authentication failed.', 401)

    if user.get('vendorCode') != vendor_code:
        return None, ('Invalid Vendor Shop ID.', 401)

    return user, None


def authenticate_admin(data):
    role = data.get('role', '').strip().lower()
    email = data.get('email', '').strip().lower()
    admin_code = data.get('adminCode', '').strip()

    if role != 'admin':
        return None, ('Only admins may perform this action.', 403)
    if not email or not admin_code:
        return None, ('Admin email and Admin Access Code are required.', 400)

    user = find_user(email, 'admin')
    if user is None:
        return None, ('Admin authentication failed.', 401)

    if user.get('adminCode') != admin_code:
        return None, ('Invalid Admin Access Code.', 401)

    return user, None


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/store')
def store():
    return app.send_static_file('store.html')


def find_user(email, role):
    return next((u for u in USERS if u['role'] == role and u['email'].lower() == email.lower()), None)


def get_default_features(role):
    return {
        'customer': ['Browse products', 'Place orders', 'View purchase history'],
        'vendor': ['Manage inventory', 'Process orders', 'View sales analytics']
    }.get(role, [])


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'Request body must be valid JSON.'}), 400

    role = data.get('role', '').strip().lower()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    vendor_code = data.get('vendorCode', '').strip()
    admin_code = data.get('adminCode', '').strip()

    if not role or not email or not password:
        return jsonify({'status': 'error', 'message': 'Email, password, and role are required.'}), 400

    user = find_user(email, role)
    if user is None or user['password'] != password:
        return jsonify({'status': 'error', 'message': 'Invalid credentials.'}), 401

    if role == 'vendor' and user.get('vendorCode') != vendor_code:
        return jsonify({'status': 'error', 'message': 'Invalid Vendor Shop ID.'}), 401

    if role == 'admin' and user.get('adminCode') != admin_code:
        return jsonify({'status': 'error', 'message': 'Invalid Admin Access Code.'}), 401

    response = {
        'status': 'success',
        'role': user['role'],
        'user': {
            'email': user['email'],
            'displayName': user['displayName'],
            'features': user['features']
        }
    }

    if role == 'vendor':
        response['vendorCode'] = user.get('vendorCode')

    return jsonify(response)


@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'Request body must be valid JSON.'}), 400

    role = data.get('role', '').strip().lower()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirmPassword', '').strip()
    vendor_code = data.get('vendorCode', '').strip()

    if not role or not email or not password or not confirm_password:
        return jsonify({'status': 'error', 'message': 'Email, password, confirm password, and role are required.'}), 400

    if password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Passwords do not match.'}), 400

    if role == 'admin':
        return jsonify({'status': 'error', 'message': 'Admin self-registration is not available.'}), 403

    if find_user(email, role):
        return jsonify({'status': 'error', 'message': 'An account with this email already exists for the selected role.'}), 409

    if role == 'vendor' and not vendor_code:
        return jsonify({'status': 'error', 'message': 'Vendor Shop ID is required for vendor signup.'}), 400

    new_user = {
        'role': role,
        'email': email,
        'password': password,
        'displayName': 'New ' + ('Vendor' if role == 'vendor' else 'Customer'),
        'features': get_default_features(role)
    }

    if role == 'vendor':
        new_user['vendorCode'] = vendor_code

    USERS.append(new_user)

    response = {
        'status': 'success',
        'role': new_user['role'],
        'user': {
            'email': new_user['email'],
            'displayName': new_user['displayName'],
            'features': new_user['features']
        }
    }

    if role == 'vendor':
        response['vendorCode'] = new_user.get('vendorCode')

    return jsonify(response)


@app.route('/api/products', methods=['GET'])
def api_get_products():
    return jsonify({'status': 'success', 'products': PRODUCTS})


@app.route('/api/products/search', methods=['GET'])
def api_search_products():
    """
    Search and filter products by:
    - name: search in product name
    - description: partial match in description
    - vendor: filter by vendor email
    - category: filter by category
    - color: filter by color
    - size: filter by size
    - inStock: filter by availability (true/false)
    """
    name = request.args.get('name', '').strip().lower()
    description = request.args.get('description', '').strip().lower()
    vendor = request.args.get('vendor', '').strip().lower()
    category = request.args.get('category', '').strip().lower()
    color = request.args.get('color', '').strip().lower()
    size = request.args.get('size', '').strip().lower()
    in_stock = request.args.get('inStock', '').strip().lower()

    results = []
    for product in PRODUCTS:
        # Name search (case-insensitive)
        if name and name not in product['name'].lower():
            continue

        # Description search (partial match)
        if description and description not in product['description'].lower():
            continue

        # Vendor filter
        if vendor and product['vendorEmail'].lower() != vendor:
            continue

        # Category filter
        if category and product.get('category', '').lower() != category:
            continue

        # Color filter
        if color and product.get('color', '').lower() != color:
            continue

        # Size filter
        if size and product.get('size', '').lower() != size:
            continue

        # Stock filter
        if in_stock:
            if in_stock == 'true' and not product.get('inStock', True):
                continue
            elif in_stock == 'false' and product.get('inStock', True):
                continue

        results.append(product)

    return jsonify({'status': 'success', 'products': results})


@app.route('/api/products', methods=['POST'])
def api_add_product():
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    user, error = authenticate_vendor(data)
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category = data.get('category', '').strip()
    color = data.get('color', '').strip()
    size = data.get('size', '').strip()
    in_stock = data.get('inStock', True)
    gallery = data.get('gallery', [])

    if not name or not description or price is None:
        return jsonify({'status': 'error', 'message': 'Name, description, and price are required.'}), 400

    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Price must be a valid number.'}), 400

    global NEXT_PRODUCT_ID
    new_product = {
        'id': NEXT_PRODUCT_ID,
        'name': name,
        'description': description,
        'price': price,
        'vendorEmail': user['email'],
        'category': category,
        'color': color,
        'size': size,
        'inStock': in_stock,
        'gallery': gallery if isinstance(gallery, list) else []
    }
    NEXT_PRODUCT_ID += 1
    PRODUCTS.append(new_product)

    return jsonify({'status': 'success', 'product': new_product}), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    role = data.get('role', '').strip().lower()
    if role == 'vendor':
        user, error = authenticate_vendor(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    elif role == 'admin':
        user, error = authenticate_admin(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    else:
        return jsonify({'status': 'error', 'message': 'Invalid role for product update.'}), 403

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    if role == 'vendor' and product['vendorEmail'].lower() != user['email'].lower():
        return jsonify({'status': 'error', 'message': 'You may only update your own products.'}), 403

    # Admins can update any product, no ownership check needed

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category = data.get('category', '').strip()
    color = data.get('color', '').strip()
    size = data.get('size', '').strip()
    in_stock = data.get('inStock')

    if not name or not description or price is None:
        return jsonify({'status': 'error', 'message': 'Name, description, and price are required.'}), 400

    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Price must be a valid number.'}), 400

    product.update({
        'name': name,
        'description': description,
        'price': price,
        'category': category,
        'color': color,
        'size': size,
        'inStock': in_stock if in_stock is not None else product.get('inStock', True)
    })

    return jsonify({'status': 'success', 'product': product})


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    role = data.get('role', '').strip().lower()
    if role == 'vendor':
        user, error = authenticate_vendor(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    elif role == 'admin':
        user, error = authenticate_admin(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    else:
        return jsonify({'status': 'error', 'message': 'Invalid role for product deletion.'}), 403

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    if role == 'vendor' and product['vendorEmail'].lower() != user['email'].lower():
        return jsonify({'status': 'error', 'message': 'You may only delete your own products.'}), 403

    # Admins can delete any product, no ownership check needed

    PRODUCTS.remove(product)
    return jsonify({'status': 'success', 'message': 'Product deleted.'})


@app.route('/api/products/<int:product_id>/gallery', methods=['POST'])
def api_add_gallery_image(product_id):
    """Add an image URL to a product's gallery."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    role = data.get('role', '').strip().lower()
    if role == 'vendor':
        user, error = authenticate_vendor(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    elif role == 'admin':
        user, error = authenticate_admin(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    else:
        return jsonify({'status': 'error', 'message': 'Invalid role for gallery management.'}), 403

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    if role == 'vendor' and product['vendorEmail'].lower() != user['email'].lower():
        return jsonify({'status': 'error', 'message': 'You may only update your own products.'}), 403

    image_url = data.get('imageUrl', '').strip()
    if not image_url:
        return jsonify({'status': 'error', 'message': 'Image URL is required.'}), 400

    if 'gallery' not in product:
        product['gallery'] = []

    product['gallery'].append(image_url)
    return jsonify({'status': 'success', 'message': 'Image added to gallery.', 'gallery': product['gallery']}), 201


@app.route('/api/products/<int:product_id>/gallery/<int:image_index>', methods=['DELETE'])
def api_remove_gallery_image(product_id, image_index):
    """Remove an image from a product's gallery."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    role = data.get('role', '').strip().lower()
    if role == 'vendor':
        user, error = authenticate_vendor(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    elif role == 'admin':
        user, error = authenticate_admin(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    else:
        return jsonify({'status': 'error', 'message': 'Invalid role for gallery management.'}), 403

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    if role == 'vendor' and product['vendorEmail'].lower() != user['email'].lower():
        return jsonify({'status': 'error', 'message': 'You may only update your own products.'}), 403

    if 'gallery' not in product or image_index < 0 or image_index >= len(product['gallery']):
        return jsonify({'status': 'error', 'message': 'Invalid image index.'}), 400

    product['gallery'].pop(image_index)
    return jsonify({'status': 'success', 'message': 'Image removed from gallery.', 'gallery': product['gallery']})


def get_or_create_cart(email):
    """Get or create a cart for a customer."""
    if email not in CARTS:
        CARTS[email] = {'items': []}
    return CARTS[email]


def find_cart_item(cart, product_id, size, color):
    """Find a cart item by product_id, size, and color."""
    return next((item for item in cart['items']
                 if item['product_id'] == product_id and
                 item['size'] == size and item['color'] == color), None)


@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    """Get cart items for the authenticated customer."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    cart = get_or_create_cart(email)
    return jsonify({'status': 'success', 'items': cart['items']})


@app.route('/api/cart', methods=['POST'])
def api_add_to_cart():
    """Add a product to cart with size and color variants."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()
    product_id = data.get('productId')
    quantity = data.get('quantity', 1)
    size = data.get('size', '').strip()
    color = data.get('color', '').strip()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    if product_id is None:
        return jsonify({'status': 'error', 'message': 'Product ID is required.'}), 400

    try:
        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({'status': 'error', 'message': 'Quantity must be greater than 0.'}), 400
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Quantity must be a valid number.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    product = find_product(product_id)
    if product is None:
        return jsonify({'status': 'error', 'message': 'Product not found.'}), 404

    cart = get_or_create_cart(email)

    # Check if item with same product, size, and color exists
    existing_item = find_cart_item(cart, product_id, size, color)

    if existing_item:
        # Update quantity if item already exists
        existing_item['quantity'] += quantity
        return jsonify({'status': 'success', 'message': 'Item quantity updated.', 'item': existing_item})
    else:
        # Add new item
        new_item = {
            'id': len(cart['items']) + 1,
            'product_id': product_id,
            'product_name': product['name'],
            'quantity': quantity,
            'size': size,
            'color': color,
            'price': product['price'],
            'vendorEmail': product['vendorEmail']
        }
        cart['items'].append(new_item)
        return jsonify({'status': 'success', 'message': 'Item added to cart.', 'item': new_item}), 201


@app.route('/api/cart/<int:item_id>', methods=['PUT'])
def api_update_cart_item(item_id):
    """Update quantity of an item in cart."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()
    quantity = data.get('quantity')

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    if quantity is None:
        return jsonify({'status': 'error', 'message': 'Quantity is required.'}), 400

    try:
        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({'status': 'error', 'message': 'Quantity must be greater than 0.'}), 400
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Quantity must be a valid number.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    cart = get_or_create_cart(email)
    item = next((i for i in cart['items'] if i['id'] == item_id), None)

    if item is None:
        return jsonify({'status': 'error', 'message': 'Cart item not found.'}), 404

    item['quantity'] = quantity
    return jsonify({'status': 'success', 'message': 'Item quantity updated.', 'item': item})


@app.route('/api/cart/<int:item_id>', methods=['DELETE'])
def api_remove_from_cart(item_id):
    """Remove an item from cart."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    cart = get_or_create_cart(email)
    item = next((i for i in cart['items'] if i['id'] == item_id), None)

    if item is None:
        return jsonify({'status': 'error', 'message': 'Cart item not found.'}), 404

    cart['items'].remove(item)
    return jsonify({'status': 'success', 'message': 'Item removed from cart.'})


@app.route('/api/cart', methods=['DELETE'])
def api_clear_cart():
    """Clear entire cart for a customer."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    if email in CARTS:
        CARTS[email]['items'] = []

    return jsonify({'status': 'success', 'message': 'Cart cleared.'})


@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    """Checkout cart and create an order. Order starts as 'pending' and must be confirmed by vendor."""
    global NEXT_ORDER_ID
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    cart = get_or_create_cart(email)
    if not cart['items']:
        return jsonify({'status': 'error', 'message': 'Cart is empty.'}), 400

    # Calculate total price
    total_price = sum(item['price'] * item['quantity'] for item in cart['items'])

    # Create order with status and vendor confirmation
    from datetime import datetime
    order = {
        'id': NEXT_ORDER_ID,
        'email': email,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'items': cart['items'].copy(),
        'totalPrice': round(total_price, 2),
        'status': 'pending',  # pending -> confirmed -> handed to delivery partner -> shipped
        'vendorConfirmed': False
    }
    NEXT_ORDER_ID += 1
    ORDERS.append(order)

    # Clear cart
    CARTS[email]['items'] = []

    return jsonify({'status': 'success', 'message': 'Order placed successfully.', 'order': order})


@app.route('/api/orders', methods=['GET'])
def api_get_orders():
    """Get all orders for a customer."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required.'}), 400

    user = find_user(email, 'customer')
    if user is None:
        return jsonify({'status': 'error', 'message': 'Customer not found.'}), 404

    customer_orders = [o for o in ORDERS if o['email'] == email]
    return jsonify({'status': 'success', 'orders': customer_orders})


# New endpoint: Vendor confirms an order (status: pending -> confirmed)
@app.route('/api/orders/<int:order_id>/confirm', methods=['POST'])
def api_confirm_order(order_id):
    """Vendor confirms an order (pending -> confirmed)."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    # Vendor authentication
    user, error = authenticate_vendor(data)
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    # Find order
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if order is None:
        return jsonify({'status': 'error', 'message': 'Order not found.'}), 404

    # Vendor must be the vendor for at least one item in the order
    vendor_email = user['email'].lower()
    if not any(item['vendorEmail'].lower() == vendor_email for item in order['items']):
        return jsonify({'status': 'error', 'message': 'You may only confirm orders for your products.'}), 403

    if order['status'] != 'pending':
        return jsonify({'status': 'error', 'message': 'Order is not pending.'}), 400

    order['status'] = 'confirmed'
    order['vendorConfirmed'] = True
    return jsonify({'status': 'success', 'message': 'Order confirmed by vendor.', 'order': order})


# New endpoint: Update order status (confirmed -> handed to delivery partner -> shipped)
@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    """Update order status: confirmed -> handed to delivery partner -> shipped. Only vendor or admin can update."""
    data, error = get_request_json()
    if error:
        return jsonify({'status': 'error', 'message': error[0]}), error[1]

    role = data.get('role', '').strip().lower()
    if role == 'vendor':
        user, error = authenticate_vendor(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    elif role == 'admin':
        user, error = authenticate_admin(data)
        if error:
            return jsonify({'status': 'error', 'message': error[0]}), error[1]
    else:
        return jsonify({'status': 'error', 'message': 'Only vendor or admin may update order status.'}), 403

    # Find order
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if order is None:
        return jsonify({'status': 'error', 'message': 'Order not found.'}), 404

    # Vendor must be the vendor for at least one item in the order
    if role == 'vendor':
        vendor_email = user['email'].lower()
        if not any(item['vendorEmail'].lower() == vendor_email for item in order['items']):
            return jsonify({'status': 'error', 'message': 'You may only update status for your orders.'}), 403

    # Status progression
    current_status = order.get('status', 'pending')
    next_status = None
    if current_status == 'confirmed':
        next_status = 'handed to delivery partner'
    elif current_status == 'handed to delivery partner':
        next_status = 'shipped'
    else:
        return jsonify({'status': 'error', 'message': 'Order status cannot be updated from current state.'}), 400

    order['status'] = next_status
    return jsonify({'status': 'success', 'message': f'Order status updated to {next_status}.', 'order': order})


if __name__ == '__main__':
    app.run(debug=True, port=5000)

