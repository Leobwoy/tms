# app/routes.py
import csv
import io
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import User, Carrier, Shipment, ActivityLog
from flask_login import login_user, logout_user, current_user, login_required
from flask import Response
from app.notifications import send_email, send_sms

bp = Blueprint('routes', __name__)

# In app/routes.py (or app/utils.py)
def log_activity(user, action, model, model_id, description=''):
    log_entry = ActivityLog(
        user_id=user.id,
        action=action,
        model=model,
        model_id=model_id,
        description=description
    )
    db.session.add(log_entry)
    db.session.commit()

# This helper function now allows all files by always returning True.
def allowed_file(filename):
    return True    

# Landing page: shows welcome and login/register links if not authenticated.
@bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    return render_template('landing.html')

@bp.route('/index')
def index():
    # Get statistics for the dashboard
    shipment_count = Shipment.query.count()
    carrier_count = Carrier.query.count()
    avg_cost_factor = db.session.query(db.func.avg(Carrier.cost_factor)).scalar() or 0

    # Render index.html with these stats
    return render_template('index.html', 
        carrier_count=carrier_count,                    
        shipment_count=shipment_count, 
        avg_cost_factor=avg_cost_factor
    )

# Registration Route
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('routes.register'))
        
    # Check if any users exist; if none, assign admin role
        if User.query.count() == 0:
            role = 'admin'
        else:
            role = 'user'


        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'error')
            return redirect(url_for('routes.register'))
        user = User(username=username, email=email)
        user.set_password(password)
        # For testing, you can manually set role to 'admin' for a particular user if needed.
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('routes.login'))
    return render_template('register.html')

# Login Route
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'error')
            return redirect(url_for('routes.login'))
        login_user(user)
        flash('Logged in successfully.', 'success')
        return redirect(url_for('routes.index'))
    return render_template('login.html')

# Logout Route
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('routes.index'))

#Carriers Route
@bp.route('/carriers')
@login_required
def carriers():
    carriers = Carrier.query.all()
    return render_template('carriers.html', carriers=carriers)

#Shipments Route
@bp.route('/shipments')
@login_required
def shipments():
    # Get the current page number, search query, and sorting parameters from the URL
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '')
    sort_by = request.args.get('sort', 'id')  # Default sort column is 'id'
    order = request.args.get('order', 'asc')   # Default sort order is ascending

    # Get the sort column from the Shipment model, defaulting to id if not found
    sort_column = getattr(Shipment, sort_by, Shipment.id)
    if order == 'desc':
        sort_column = sort_column.desc()
    else:
        sort_column = sort_column.asc()

    if query:
        shipments_pagination = Shipment.query.filter(
            (Shipment.origin.ilike(f'%{query}%')) |
            (Shipment.destination.ilike(f'%{query}%'))
        ).order_by(sort_column).paginate(page=page, per_page=5, error_out=False)
    else:
        shipments_pagination = Shipment.query.order_by(sort_column).paginate(page=page, per_page=5, error_out=False)

    return render_template(
        'shipments.html',
        shipments=shipments_pagination.items,
        pagination=shipments_pagination,
        query=query,
        sort_by=sort_by,
        order=order
    )

#Optimize Route
@bp.route('/optimize', methods=['GET', 'POST'])
@login_required
def optimize():
    # Default weight multiplier is 1.0
    weight = 1.0
    carriers = Carrier.query.all()
    sorted_carriers = None
    best_carrier = None

    if request.method == 'POST':
        # Retrieve the weight factor from the form
        weight = request.form.get('weight', 1.0, type=float)

        # Compute a score for each carrier (for example, score = cost_factor * weight)
        carrier_scores = []
        for c in carriers:
            score = c.cost_factor * weight
            carrier_scores.append({'carrier': c, 'score': score})

        # Sort the carriers by score in ascending order (lower is better)
        sorted_carriers = sorted(carrier_scores, key=lambda x: x['score'])

        # The best carrier is the one with the lowest score
        best_carrier = sorted_carriers[0]['carrier'] if sorted_carriers else None

    return render_template(
        'optimize.html',
        best_carrier=best_carrier,
        sorted_carriers=sorted_carriers,
        weight=weight
    )

#Add_Shipment Route
@bp.route('/add_shipment', methods=['GET', 'POST'])
@login_required
def add_shipment():
     # Only allow admins to add shipments
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.shipments'))
    if request.method == 'POST':
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        weight = request.form.get('weight', type=float)
        carrier_id = request.form.get('carrier_id', type=int)
        status = request.form.get('status', 'Pending')  # Get the status
        if not (origin and destination and weight and carrier_id):
            flash("All fields are required.", "error")
            return redirect(url_for('routes.add_shipment'))
        new_shipment = Shipment(origin=origin, destination=destination, weight=weight,
                                carrier_id=carrier_id, status=status)
        db.session.add(new_shipment)
        db.session.commit()

          # Log the creation activity
        log_activity(current_user, 'create', 'Shipment', new_shipment.id,
                     f"Created shipment from {origin} to {destination}.")
        
        flash("Shipment added successfully!", "success")
        return redirect(url_for('routes.shipments'))
    carriers = Carrier.query.all()
    return render_template('add_shipment.html', carriers=carriers)

#Add_Carrier Route
@bp.route('/add_carrier', methods=['GET', 'POST'])
@login_required
def add_carrier():
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.carriers'))
    if request.method == 'POST':
        name = request.form.get('name')
        cost_factor = request.form.get('cost_factor', type=float)
        if not (name and cost_factor is not None):
            flash("All fields are required.", "error")
            return redirect(url_for('routes.add_carrier'))
        new_carrier = Carrier(name=name, cost_factor=cost_factor)
        db.session.add(new_carrier)
        db.session.commit()
        log_activity(
            current_user,
            'create',
            'Carrier',
            new_carrier.id,
            f"Created carrier '{name}' with cost factor {cost_factor}."
        )
        flash("Carrier added successfully!", "success")
        return redirect(url_for('routes.carriers'))
    return render_template('add_carrier.html')

#Edit_Carrier Route
@bp.route('/edit_carrier/<int:carrier_id>', methods=['GET', 'POST'])
@login_required
def edit_carrier(carrier_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.carriers'))
    carrier = Carrier.query.get_or_404(carrier_id)
    if request.method == 'POST':
        original_data = f"{carrier.name}, {carrier.cost_factor}"
        carrier.name = request.form.get('name')
        carrier.cost_factor = request.form.get('cost_factor', type=float)
        if not (carrier.name and carrier.cost_factor is not None):
            flash("All fields are required.", "error")
            return redirect(url_for('routes.edit_carrier', carrier_id=carrier_id))
        db.session.commit()
        new_data = f"{carrier.name}, {carrier.cost_factor}"
        log_activity(
            current_user,
            'update',
            'Carrier',
            carrier.id,
            f"Updated carrier. Before: [{original_data}]. After: [{new_data}]."
        )
        flash("Carrier updated successfully!", "success")
        return redirect(url_for('routes.carriers'))
    return render_template('edit_carrier.html', carrier=carrier)


#Delete_Carrier Route
@bp.route('/delete_carrier/<int:carrier_id>', methods=['POST'])
@login_required
def delete_carrier(carrier_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.carriers'))
    carrier = Carrier.query.get_or_404(carrier_id)
    log_activity(
        current_user,
        'delete',
        'Carrier',
        carrier.id,
        f"Deleted carrier '{carrier.name}' with cost factor {carrier.cost_factor}."
    )
    db.session.delete(carrier)
    db.session.commit()
    flash("Carrier deleted successfully!", "success")
    return redirect(url_for('routes.carriers'))


#Edit Shipment Route
@bp.route('/edit_shipment/<int:shipment_id>', methods=['GET', 'POST'])
@login_required
def edit_shipment(shipment_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.shipments'))
    shipment = Shipment.query.get_or_404(shipment_id)
    if request.method == 'POST':
        # Capture original data for logging
        original_data = f"{shipment.origin}, {shipment.destination}, {shipment.weight}, {shipment.carrier_id}, {shipment.status}"
        
        # Update the shipment with new values
        shipment.origin = request.form.get('origin')
        shipment.destination = request.form.get('destination')
        shipment.weight = request.form.get('weight', type=float)
        shipment.carrier_id = request.form.get('carrier_id', type=int)
        shipment.status = request.form.get('status', shipment.status)
        if not (shipment.origin and shipment.destination and shipment.weight and shipment.carrier_id):
            flash("All fields are required.", "error")
            return redirect(url_for('routes.edit_shipment', shipment_id=shipment_id))
        db.session.commit()
        
        # Capture new data and log the update
        new_data = f"{shipment.origin}, {shipment.destination}, {shipment.weight}, {shipment.carrier_id}, {shipment.status}"
        log_activity(
            current_user, 
            'update', 
            'Shipment', 
            shipment.id,
            f"Updated shipment. Before: [{original_data}]. After: [{new_data}]."
        )

        # Send email notification
        #subject = "Shipment Updated"
        #recipients = ["admin@gmail.com"]  # Replace with actual admin email(s)
        #text_body = f"Shipment {shipment.id} updated.\nBefore: [{original_data}]\nAfter: [{new_data}]"
        #send_email(subject, recipients, text_body)
        
        # Send SMS notification
        #sms_body = f"Shipment {shipment.id} updated. New status: {shipment.status}."
        #admin_phone = "+19876543210"  # Replace with actual admin phone number
        #send_sms(sms_body, admin_phone)

        #flash("Shipment updated successfully!", "success")
        #return redirect(url_for('routes.shipments'))
    
    carriers = Carrier.query.all()
    return render_template('edit_shipment.html', shipment=shipment, carriers=carriers)

#Delete_Shipment Route
@bp.route('/delete_shipment/<int:shipment_id>', methods=['POST'])
@login_required
def delete_shipment(shipment_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.shipments'))
    shipment = Shipment.query.get_or_404(shipment_id)
    # Log deletion before removing the record
    log_activity(
        current_user, 
        'delete', 
        'Shipment', 
        shipment.id,
        f"Deleted shipment from {shipment.origin} to {shipment.destination} (Weight: {shipment.weight}, Status: {shipment.status})."
    )
    db.session.delete(shipment)
    db.session.commit()
    flash("Shipment deleted successfully!", "success")
    return redirect(url_for('routes.shipments'))


@bp.route('/export_shipments')
@login_required
def export_shipments():
    # Query all shipments
    shipments = Shipment.query.all()

    # Create an in-memory file-like string buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the CSV header row
    writer.writerow(['ID', 'Origin', 'Destination', 'Weight', 'Carrier ID'])

    # Write a row for each shipment
    for shipment in shipments:
        writer.writerow([shipment.id, shipment.origin, shipment.destination, shipment.weight, shipment.carrier_id])

    # Reset the buffer's position to the beginning
    output.seek(0)

    # Return the CSV as a downloadable file
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=shipments.csv"}
    )

@bp.route('/track_shipments')
@login_required
def track_shipments():
    # Optional: Allow filtering by status via query parameter
    status_filter = request.args.get('status')
    if status_filter:
        shipments = Shipment.query.filter_by(status=status_filter).all()
    else:
        shipments = Shipment.query.all()
    return render_template('track_shipments.html', shipments=shipments, status_filter=status_filter)

@bp.route('/activity_logs')
@login_required
def activity_logs():
    if current_user.role != 'admin':
        flash("Access denied.", "error")
        return redirect(url_for('routes.index'))
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    return render_template('activity_logs.html', logs=logs)


#Upload_Shipment Route
@bp.route('/upload_shipments', methods=['GET', 'POST'])
@login_required
def upload_shipments():
    if current_user.role != 'admin':
        flash('Access denied. Only admins can perform this action.', 'error')
        return redirect(url_for('routes.shipments'))
    
    if request.method == 'POST':
        # Check that a file is present in the request.
        if 'file' not in request.files:
            flash('No file part in the request.', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        # Since allowed_file always returns True, we process any file.
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Read the file into memory and decode as UTF-8.
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            header = next(csv_input)  # Skip header row if present.
            
            # Optional: Validate the CSV header. Adjust expected_columns as needed.
            expected_columns = ['origin', 'destination', 'weight', 'carrier_id', 'status']
            if header and any(col.lower() not in expected_columns for col in header):
                flash('CSV header does not match expected columns.', 'error')
                return redirect(request.url)
            
            count = 0
            errors = []
            for row in csv_input:
                try:
                    # Assume CSV columns: origin, destination, weight, carrier_id, status (optional)
                    origin = row[0].strip()
                    destination = row[1].strip()
                    weight = float(row[2])
                    carrier_id = int(row[3])
                    status = row[4].strip() if len(row) > 4 else 'Pending'
                    
                    # Basic validation: ensure required fields are present.
                    if not (origin and destination and weight and carrier_id):
                        raise ValueError("Missing required fields.")
                    
                    shipment = Shipment(
                        origin=origin,
                        destination=destination,
                        weight=weight,
                        carrier_id=carrier_id,
                        status=status
                    )
                    db.session.add(shipment)
                    db.session.flush()  # Flush to assign an ID before logging.
                    
                    # Log the creation of the shipment.
                    log_activity(
                        current_user,
                        'create',
                        'Shipment',
                        shipment.id,
                        f"Bulk uploaded shipment: {origin} to {destination}, weight {weight}, status {status}."
                    )
                    count += 1
                except Exception as e:
                    errors.append(f"Error processing row {csv_input.line_num}: {str(e)}")
            db.session.commit()
            flash(f'Successfully uploaded {count} shipments.', 'success')
            if errors:
                flash('Some errors occurred: ' + '; '.join(errors), 'error')
            return redirect(url_for('routes.shipments'))
        else:
            flash('File upload failed.', 'error')
            return redirect(request.url)
    
    return render_template('bulk_upload.html')

#Admin Promotion Route
@bp.route('/promote_to_admin', methods=['GET','POST'])
@login_required
def promote_to_admin():
    # Only allow promotion if the current user is not already an admin
    # and if no other admin exists.
    if current_user.role == 'admin':
        flash('You are already an admin.', 'info')
        return redirect(url_for('routes.index'))
    
    admin_exists = User.query.filter_by(role='admin').first()
    if admin_exists:
        flash('An admin already exists. You cannot be promoted automatically.', 'error')
    else:
        current_user.role = 'admin'
        db.session.commit()
        flash('You have been promoted to admin!', 'success')
    return redirect(url_for('routes.index'))
