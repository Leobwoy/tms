# app/fleet/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.fleet.models import Vehicle, Driver

fleet_bp = Blueprint('fleet', __name__, url_prefix='/fleet')

# ----------------------------
# Fleet Home / Dashboard
@fleet_bp.route('/')
@login_required
def index():
    # Anyone logged in can view fleet data
    vehicles = Vehicle.query.all()
    drivers = Driver.query.all()
    return render_template('fleet/index.html', vehicles=vehicles, drivers=drivers)

# ----------------------------
# Vehicle Routes

@fleet_bp.route('/vehicles')
@login_required
def list_vehicles():
    vehicles = Vehicle.query.all()
    return render_template('fleet/vehicles.html', vehicles=vehicles)

@fleet_bp.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if current_user.role != 'admin':
        flash('Access denied. Only admins can add vehicles.', 'error')
        return redirect(url_for('fleet.list_vehicles'))
    if request.method == 'POST':
        license_plate = request.form.get('license_plate')
        make = request.form.get('make')
        model = request.form.get('model')
        year = request.form.get('year', type=int)
        capacity = request.form.get('capacity', type=float)
        status = request.form.get('status', 'available')
        # Basic validation could be added here
        new_vehicle = Vehicle(
            license_plate=license_plate,
            make=make,
            model=model,
            year=year,
            capacity=capacity,
            status=status
        )
        db.session.add(new_vehicle)
        db.session.commit()
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('fleet.list_vehicles'))
    return render_template('fleet/add_vehicle.html')

@fleet_bp.route('/vehicles/edit/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can edit vehicles.', 'error')
        return redirect(url_for('fleet.list_vehicles'))
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if request.method == 'POST':
        vehicle.license_plate = request.form.get('license_plate')
        vehicle.make = request.form.get('make')
        vehicle.model = request.form.get('model')
        vehicle.year = request.form.get('year', type=int)
        vehicle.capacity = request.form.get('capacity', type=float)
        vehicle.status = request.form.get('status')
        db.session.commit()
        flash('Vehicle updated successfully!', 'success')
        return redirect(url_for('fleet.list_vehicles'))
    return render_template('fleet/edit_vehicle.html', vehicle=vehicle)

@fleet_bp.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can delete vehicles.', 'error')
        return redirect(url_for('fleet.list_vehicles'))
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle deleted successfully!', 'success')
    return redirect(url_for('fleet.list_vehicles'))

# ----------------------------
# Driver Routes

@fleet_bp.route('/drivers')
@login_required
def list_drivers():
    drivers = Driver.query.all()
    return render_template('fleet/drivers.html', drivers=drivers)

@fleet_bp.route('/drivers/add', methods=['GET', 'POST'])
@login_required
def add_driver():
    if current_user.role != 'admin':
        flash('Access denied. Only admins can add drivers.', 'error')
        return redirect(url_for('fleet.list_drivers'))
    if request.method == 'POST':
        name = request.form.get('name')
        license_number = request.form.get('license_number')
        phone = request.form.get('phone')
        status = request.form.get('status', 'available')
        new_driver = Driver(
            name=name,
            license_number=license_number,
            phone=phone,
            status=status
        )
        db.session.add(new_driver)
        db.session.commit()
        flash('Driver added successfully!', 'success')
        return redirect(url_for('fleet.list_drivers'))
    return render_template('fleet/add_driver.html')

@fleet_bp.route('/drivers/edit/<int:driver_id>', methods=['GET', 'POST'])
@login_required
def edit_driver(driver_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can edit drivers.', 'error')
        return redirect(url_for('fleet.list_drivers'))
    driver = Driver.query.get_or_404(driver_id)
    if request.method == 'POST':
        driver.name = request.form.get('name')
        driver.license_number = request.form.get('license_number')
        driver.phone = request.form.get('phone')
        driver.status = request.form.get('status')
        db.session.commit()
        flash('Driver updated successfully!', 'success')
        return redirect(url_for('fleet.list_drivers'))
    return render_template('fleet/edit_driver.html', driver=driver)

@fleet_bp.route('/drivers/delete/<int:driver_id>', methods=['POST'])
@login_required
def delete_driver(driver_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admins can delete drivers.', 'error')
        return redirect(url_for('fleet.list_drivers'))
    driver = Driver.query.get_or_404(driver_id)
    db.session.delete(driver)
    db.session.commit()
    flash('Driver deleted successfully!', 'success')
    return redirect(url_for('fleet.list_drivers'))
