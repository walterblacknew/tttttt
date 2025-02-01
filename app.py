# app.py

from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extentions import db, login_manager
from models import (
    User, Route, RoutePoint, RouteAssignment,
    Store, EvaluationParameter, StoreEvaluation, StoreEvaluationDetail, QuotaCategory
)
from forms import (
    LoginForm, UserForm, RouteForm, RoutePointForm,
    StoreForm, EvaluationParameterForm, StoreEvaluationForm, QuotaCategoryForm
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from datetime import datetime
import csv
import io

# -------------------------------------------------------------------------
# In-memory CSV data (demo)
# -------------------------------------------------------------------------
route_csv_data = []
customer_csv_data = []


def create_admin_user():
    """Ensures an admin user named 'admin' exists."""
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        new_admin = User(
            username='admin',
            password='adminpassword',  # Should be hashed in production
            role='admin',
            email='admin@example.com',
            fullname='مدیر سیستم',
            is_active=True
        )
        db.session.add(new_admin)
        db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        create_admin_user()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # -------------------------------------------------------------------------
    # LOGIN / LOGOUT
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            # Compare hashed password in production
            if user and user.password == form.password.data:
                login_user(user)
                flash('خوش آمدید!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('با موفقیت خارج شدید.', 'info')
        return redirect(url_for('login'))

    # -------------------------------------------------------------------------
    # DASHBOARD
    @app.route('/')
    @login_required
    def dashboard():
        if current_user.role == 'admin':
            return redirect(url_for('admin_index'))
        elif current_user.role == 'observer':
            return redirect(url_for('observer_index'))
        else:
            return redirect(url_for('marketer_index'))

    # -------------------------------------------------------------------------
    # ADMIN SECTION

    @app.route('/admin', methods=['GET'])
    @login_required
    def admin_index():
        """Admin dashboard: partial previews of route_csv_data and customer_csv_data."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Pass CSV data for partial preview
        return render_template(
            'admin/index.html',
            route_data=route_csv_data,
            customer_data=customer_csv_data
        )

    @app.route('/admin/data')
    @login_required
    def admin_data():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/data.html')

    # ---------------- NEW ROUTES: UPLOAD CSV FILES ----------------
    @app.route('/admin/upload_route_csv', methods=['POST'])
    @login_required
    def admin_upload_route_csv():
        """Handles CSV upload for اطلاعات مسیر."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        file = request.files.get('route_csv')
        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_routes_csv'))

        try:
            # Parse CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)

            route_csv_data.clear()
            for row in csv_reader:
                route_csv_data.append(row)

            flash('فایل CSV اطلاعات مسیر با موفقیت بارگذاری شد.', 'success')
        except Exception as e:
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')

        return redirect(url_for('admin_routes_csv'))

    @app.route('/admin/upload_customer_csv', methods=['POST'])
    @login_required
    def admin_upload_customer_csv():
        """Handles CSV upload for اطلاعات مشتریان."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        file = request.files.get('customer_csv')
        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_customers_csv'))

        try:
            # Parse CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)

            customer_csv_data.clear()
            for row in csv_reader:
                customer_csv_data.append(row)

            flash('فایل CSV اطلاعات مشتریان با موفقیت بارگذاری شد.', 'success')
        except Exception as e:
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')

        return redirect(url_for('admin_customers_csv'))
    # ---------------------------------------------------------------

    # ---------------- FULL-SCREEN CSV PAGES (VIEW / EDIT / DELETE) ----------------
    @app.route('/admin/routes-csv', methods=['GET'])
    @login_required
    def admin_routes_csv():
        """Dedicated page for uploading & managing اطلاعات مسیر (CSV)."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        return render_template('admin/routes_csv.html', route_data=route_csv_data)

    @app.route('/admin/customers-csv', methods=['GET'])
    @login_required
    def admin_customers_csv():
        """Dedicated page for uploading & managing اطلاعات مشتریان (CSV)."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        return render_template('admin/customers_csv.html', customer_data=customer_csv_data)

    # ------------ ROUTE CSV Delete & Edit ------------
    @app.route('/admin/routes-csv/delete/<int:row_index>', methods=['POST'])
    @login_required
    def admin_delete_route_csv(row_index):
        """Delete a row from route_csv_data by index."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        if 0 <= row_index < len(route_csv_data):
            route_csv_data.pop(row_index)
            flash('سطر حذف شد.', 'success')
        else:
            flash('سطر یافت نشد.', 'danger')

        return redirect(url_for('admin_routes_csv'))

    @app.route('/admin/routes-csv/edit/<int:row_index>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_route_csv(row_index):
        """Edit a row in route_csv_data by index."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        if row_index < 0 or row_index >= len(route_csv_data):
            flash('سطر یافت نشد.', 'danger')
            return redirect(url_for('admin_routes_csv'))

        if request.method == 'POST':
            # Update row in memory
            new_data = {}
            old_keys = list(route_csv_data[row_index].keys())
            for key in old_keys:
                new_data[key] = request.form.get(key, '')
            route_csv_data[row_index] = new_data
            flash('سطر با موفقیت ویرایش شد.', 'success')
            return redirect(url_for('admin_routes_csv'))

        # GET: show edit form
        row = route_csv_data[row_index]
        return render_template('admin/edit_route_csv.html', row=row, row_index=row_index)

    # ------------ CUSTOMER CSV Delete & Edit ------------
    @app.route('/admin/customers-csv/delete/<int:row_index>', methods=['POST'])
    @login_required
    def admin_delete_customer_csv(row_index):
        """Delete a row from customer_csv_data by index."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        if 0 <= row_index < len(customer_csv_data):
            customer_csv_data.pop(row_index)
            flash('سطر حذف شد.', 'success')
        else:
            flash('سطر یافت نشد.', 'danger')

        return redirect(url_for('admin_customers_csv'))

    @app.route('/admin/customers-csv/edit/<int:row_index>', methods=['GET', 'POST'])
    @login_required
    def admin_edit_customer_csv(row_index):
        """Edit a row in customer_csv_data by index."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        if row_index < 0 or row_index >= len(customer_csv_data):
            flash('سطر یافت نشد.', 'danger')
            return redirect(url_for('admin_customers_csv'))

        if request.method == 'POST':
            new_data = {}
            old_keys = list(customer_csv_data[row_index].keys())
            for key in old_keys:
                new_data[key] = request.form.get(key, '')
            customer_csv_data[row_index] = new_data
            flash('سطر با موفقیت ویرایش شد.', 'success')
            return redirect(url_for('admin_customers_csv'))

        row = customer_csv_data[row_index]
        return render_template('admin/edit_customer_csv.html', row=row, row_index=row_index)

    # ------------ SHOWING CUSTOMER MAP (Purple Markers) ------------
    @app.route('/admin/customers-csv/map')
    @login_required
    def admin_customers_csv_map():
        """Displays a Leaflet map with purple markers for each customer row 
           having 'Latitude' and 'Longitude' columns."""
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        return render_template('admin/customers_map.html', customer_data=customer_csv_data)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # ADMIN: QUOTAS + EVALUATION + STORES
    @app.route('/admin/quotas', methods=['GET', 'POST'])
    @login_required
    def admin_quotas():
        """Single route to manage:
           - Creating new Store (with lat/lng)
           - Creating new EvaluationParameter
           - Creating new StoreEvaluation
           - Creating new QuotaCategory
           All displayed on the same 'quotas.html' page.
        """
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        storeForm = StoreForm()
        evaluationParameterForm = EvaluationParameterForm()
        storeEvaluationForm = StoreEvaluationForm()
        quotaCategoryForm = QuotaCategoryForm()

        stores = Store.query.all()
        evaluationParameters = EvaluationParameter.query.all()
        storeEvaluations = StoreEvaluation.query.order_by(StoreEvaluation.created_at.desc()).all()
        quota_list = QuotaCategory.query.all()

        if request.method == 'POST':
            # Distinguish which form was submitted by checking unique fields

            # A) If 'lat' and 'lng' => StoreForm
            if 'lat' in request.form and 'lng' in request.form:
                if storeForm.validate_on_submit():
                    new_store = Store(
                        name=storeForm.name.data.strip(),
                        lat=storeForm.lat.data,
                        lng=storeForm.lng.data
                    )
                    db.session.add(new_store)
                    try:
                        db.session.commit()
                        flash('فروشگاه جدید ایجاد شد.', 'success')
                    except IntegrityError:
                        db.session.rollback()
                        flash('خطا: فروشگاه تکراری یا نامعتبر.', 'danger')
                return redirect(url_for('admin_quotas'))

            # B) If 'name' and 'weight' => evaluationParameterForm
            elif 'name' in request.form and 'weight' in request.form:
                if evaluationParameterForm.validate_on_submit():
                    param = EvaluationParameter(
                        name=evaluationParameterForm.name.data,
                        weight=evaluationParameterForm.weight.data
                    )
                    db.session.add(param)
                    try:
                        db.session.commit()
                        flash('پارامتر جدید ایجاد شد.', 'success')
                    except IntegrityError:
                        db.session.rollback()
                        flash('خطا: پارامتر تکراری.', 'danger')
                return redirect(url_for('admin_quotas'))

            # C) If 'store_id' => storeEvaluationForm
            elif 'store_id' in request.form:
                if storeEvaluationForm.validate_on_submit():
                    new_eval = StoreEvaluation(
                        store_id=storeEvaluationForm.store_id.data,
                        start_date=storeEvaluationForm.start_date.data,
                        end_date=storeEvaluationForm.end_date.data,
                        total_score=0.0,
                        category=None
                    )
                    db.session.add(new_eval)
                    db.session.commit()
                    flash('ارزیابی جدید ایجاد شد.', 'success')
                return redirect(url_for('admin_quotas'))

            # D) If 'monthly_quota' => quotaCategoryForm
            elif 'monthly_quota' in request.form:
                if quotaCategoryForm.validate_on_submit():
                    qc = QuotaCategory(
                        category=quotaCategoryForm.category.data.strip(),
                        monthly_quota=quotaCategoryForm.monthly_quota.data
                    )
                    db.session.add(qc)
                    try:
                        db.session.commit()
                        flash('سهمیه جدید ثبت شد.', 'success')
                    except IntegrityError:
                        db.session.rollback()
                        flash('خطا: این دسته تکراری است.', 'danger')
                return redirect(url_for('admin_quotas'))

            return redirect(url_for('admin_quotas'))

        # GET
        return render_template(
            'admin/quotas.html',
            storeForm=storeForm,
            stores=stores,
            evaluationParameterForm=evaluationParameterForm,
            evaluationParameters=evaluationParameters,
            storeEvaluationForm=storeEvaluationForm,
            storeEvaluations=storeEvaluations,
            quotaCategoryForm=quotaCategoryForm,
            quota_list=quota_list
        )

    @app.route('/admin/quotas/delete/<int:qc_id>', methods=['POST'])
    @login_required
    def delete_quota_category(qc_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        qc = QuotaCategory.query.get_or_404(qc_id)
        db.session.delete(qc)
        db.session.commit()
        flash('سهمیه حذف شد.', 'info')
        return redirect(url_for('admin_quotas'))

    # -------------------------------------------------------------------------
    # ADMIN: USER MANAGEMENT
    @app.route('/admin/users', methods=['GET', 'POST'])
    @login_required
    def admin_users():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        count_admin = User.query.filter_by(role='admin').count()
        count_marketer = User.query.filter_by(role='marketer').count()
        count_observer = User.query.filter_by(role='observer').count()

        search_query = request.args.get('search', '').strip()
        if search_query:
            users = User.query.filter(
                or_(
                    User.username.ilike(f"%{search_query}%"),
                    User.email.ilike(f"%{search_query}%")
                )
            ).all()
        else:
            users = User.query.all()

        form = UserForm()
        edit_id = request.args.get('edit_id', type=int)
        edit_mode = False
        user_to_edit = None

        if edit_id:
            user_to_edit = User.query.get(edit_id)
            if user_to_edit:
                form.username.data = user_to_edit.username
                form.password.data = user_to_edit.password
                form.email.data = user_to_edit.email or ''
                form.fullname.data = user_to_edit.fullname
                form.is_active.data = user_to_edit.is_active
                form.role.data = user_to_edit.role
                edit_mode = True

        if form.validate_on_submit():
            email_value = form.email.data.strip() if form.email.data else None

            if edit_mode and user_to_edit:
                user_to_edit.username = form.username.data
                user_to_edit.password = form.password.data
                user_to_edit.email = email_value
                user_to_edit.fullname = form.fullname.data
                user_to_edit.is_active = form.is_active.data
                user_to_edit.role = form.role.data
                try:
                    db.session.commit()
                    flash('کاربر با موفقیت ویرایش شد.', 'success')
                    return redirect(url_for('admin_users'))
                except IntegrityError:
                    db.session.rollback()
                    flash('خطا: ایمیل تکراری یا نامعتبر است.', 'danger')
            else:
                new_user = User(
                    username=form.username.data,
                    password=form.password.data,
                    email=email_value,
                    fullname=form.fullname.data,
                    is_active=form.is_active.data,
                    role=form.role.data
                )
                try:
                    db.session.add(new_user)
                    db.session.commit()
                    flash('کاربر جدید ساخته شد.', 'success')
                    return redirect(url_for('admin_users'))
                except IntegrityError:
                    db.session.rollback()
                    flash('خطا: ایمیل تکراری یا نامعتبر است.', 'danger')

        return render_template(
            'admin/users.html',
            users=users,
            form=form,
            edit_mode=edit_mode,
            search_query=search_query,
            count_admin=count_admin,
            count_marketer=count_marketer,
            count_observer=count_observer
        )

    @app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
    @login_required
    def delete_user(user_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        user_to_delete = User.query.get_or_404(user_id)
        if user_to_delete.username == 'admin':
            flash('نمی‌توان ادمین اصلی را حذف کرد!', 'warning')
            return redirect(url_for('admin_users'))

        db.session.delete(user_to_delete)
        db.session.commit()
        flash('کاربر حذف شد.', 'info')
        return redirect(url_for('admin_users'))

    # -------------------------------------------------------------------------
    # ADMIN: ROUTE MANAGEMENT
    @app.route('/admin/routes', methods=['GET', 'POST'])
    @login_required
    def admin_routes():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        route_form = RouteForm()
        marketers = User.query.filter_by(role='marketer').all()
        route_form.marketer_ids.choices = [(m.id, m.fullname or m.username) for m in marketers]

        if route_form.validate_on_submit():
            route = Route(
                name=route_form.name.data,
                description=route_form.description.data
            )
            db.session.add(route)
            db.session.flush()

            for marketer_id in route_form.marketer_ids.data:
                assignment = RouteAssignment(route_id=route.id, marketer_id=marketer_id)
                db.session.add(assignment)

            try:
                db.session.commit()
                flash('مسیر جدید با موفقیت ایجاد شد.', 'success')
                return redirect(url_for('admin_routes'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ایجاد مسیر.', 'danger')

        routes = Route.query.all()
        return render_template('admin/routes.html', route_form=route_form, routes=routes)

    @app.route('/admin/routes/<int:route_id>', methods=['GET', 'POST'])
    @login_required
    def admin_route_detail(route_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        route = Route.query.get_or_404(route_id)
        point_form = RoutePointForm()

        if point_form.validate_on_submit():
            new_point = RoutePoint(
                route_id=route.id,
                name=point_form.name.data,
                latitude=point_form.latitude.data,
                longitude=point_form.longitude.data,
                address=point_form.address.data,
                order=point_form.order.data
            )
            db.session.add(new_point)
            try:
                db.session.commit()
                flash('نقطه جدید اضافه شد.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('خطا در افزودن نقطه.', 'danger')
            return redirect(url_for('admin_route_detail', route_id=route.id))

        return render_template('admin/route_detail.html', route=route, point_form=point_form)

    @app.route('/admin/routes/<int:route_id>/points/<int:point_id>', methods=['DELETE', 'POST'])
    @login_required
    def delete_route_point(route_id, point_id):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        point = RoutePoint.query.get_or_404(point_id)
        if point.route_id != route_id:
            return jsonify({'error': 'Not found'}), 404

        db.session.delete(point)
        db.session.commit()

        if request.method == 'DELETE':
            return jsonify({'message': 'Point deleted'})
        else:
            flash('نقطه حذف شد.', 'success')
            return redirect(url_for('admin_route_detail', route_id=route_id))

    @app.route('/admin/reports')
    @login_required
    def admin_reports():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/reports.html')

    @app.route('/admin/alerts')
    @login_required
    def admin_alerts():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/alerts.html')

    @app.route('/admin/settings')
    @login_required
    def admin_settings():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/settings.html')

    @app.route('/admin/marketer_locations')
    @login_required
    def admin_marketer_locations():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/marketer_locations.html')

    # -------------------------------------------------------------------------
    # MARKETER SECTION
    @app.route('/marketer')
    @login_required
    def marketer_index():
        if current_user.role != 'marketer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('marketer/index.html')

    @app.route('/marketer/map')
    @login_required
    def marketer_map():
        if current_user.role != 'marketer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('marketer/map.html')

    @app.route('/api/marketer/routes')
    @login_required
    def get_marketer_assigned_routes():
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403

        assignments = RouteAssignment.query.filter_by(marketer_id=current_user.id, is_active=True).all()
        routes_data = []
        for assignment in assignments:
            route = assignment.route
            if route.is_active:
                sorted_points = sorted(route.points, key=lambda p: p.order)
                points = [
                    {
                        'id': p.id,
                        'name': p.name,
                        'lat': p.latitude,
                        'lng': p.longitude,
                        'address': p.address,
                        'order': p.order
                    }
                    for p in sorted_points
                ]
                routes_data.append({
                    'id': route.id,
                    'name': route.name,
                    'description': route.description,
                    'points': points
                })

        return jsonify(routes_data)

    @app.route('/api/marketer/routes/<int:route_id>/complete', methods=['POST'])
    @login_required
    def complete_route(route_id):
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403

        assignment = RouteAssignment.query.filter_by(
            route_id=route_id,
            marketer_id=current_user.id,
            is_active=True
        ).first_or_404()

        assignment.completed = True
        assignment.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Route marked as completed'})

    @app.route('/api/marketer/location', methods=['POST'])
    @login_required
    def update_location():
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        try:
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            return jsonify({'message': 'Location updated', 'lat': latitude, 'lng': longitude})
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid coordinates'}), 400

    # -------------------------------------------------------------------------
    # OBSERVER SECTION
    @app.route('/observer')
    @login_required
    def observer_index():
        if current_user.role != 'observer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('observer/index.html')

    @app.route('/observer/gps')
    @login_required
    def observer_gps():
        if current_user.role != 'observer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('observer/gps.html')

    @app.route('/observer/performance')
    @login_required
    def observer_performance():
        if current_user.role != 'observer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('observer/performance.html')

    @app.route('/observer/reports')
    @login_required
    def observer_reports():
        if current_user.role != 'observer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('observer/reports.html')

    @app.route('/observer/alerts')
    @login_required
    def observer_alerts():
        if current_user.role != 'observer':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('observer/alerts.html')

    @app.route('/api/observer/marketer-locations')
    @login_required
    def get_marketer_locations():
        if current_user.role not in ['admin', 'observer']:
            return jsonify({'error': 'Unauthorized'}), 403

        marketers = User.query.filter_by(role='marketer', is_active=True).all()
        locations = []
        for marketer in marketers:
            # Demo lat/lng
            locations.append({
                'id': marketer.id,
                'name': marketer.fullname or marketer.username,
                'lat': 35.6892,
                'lng': 51.3890,
                'last_update': datetime.utcnow().isoformat()
            })
        return jsonify(locations)

    return app


if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, port=5000)
