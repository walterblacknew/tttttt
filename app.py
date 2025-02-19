from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extentions import db, login_manager
from models import (
    User, Route, RoutePoint, RouteAssignment,
    Store, EvaluationParameter, StoreEvaluation, StoreEvaluationDetail, QuotaCategory,
    CustomerReport, RouteReport, GradeMapping, CustomerEvaluation, DescriptiveCriterion
)
from forms import (
    LoginForm, UserForm, RouteForm, RoutePointForm,
    StoreForm, EvaluationParameterForm, StoreEvaluationForm, QuotaCategoryForm,
    GradeMappingForm, CustomerEvaluationForm
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from datetime import datetime
import csv
import io
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

def create_admin_user():
    """Ensure an admin user named 'admin' exists."""
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        new_admin = User(
            username='admin',
            password=generate_password_hash('adminpassword'),
            role='admin',
            email='admin@example.com',
            fullname='مدیر سیستم',
            is_active=True
        )
        db.session.add(new_admin)
        db.session.commit()

def safe_float(val):
    """Convert a value to float safely; return None if conversion fails."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

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

    # --------------------- LOGIN / LOGOUT ---------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and check_password_hash(user.password, form.password.data):
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

    # --------------------- DASHBOARD ---------------------
    @app.route('/')
    @login_required
    def dashboard():
        if current_user.role == 'admin':
            return redirect(url_for('admin_index'))
        elif current_user.role == 'observer':
            return redirect(url_for('observer_index'))
        else:
            return redirect(url_for('marketer_index'))

    # --------------------- ADMIN SECTION ---------------------
    @app.route('/admin', methods=['GET'])
    @login_required
    def admin_index():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        route_reports = RouteReport.query.all()
        route_data = [{
            'شماره_مسیر': r.route_number,
            'نام_مسیر': r.route_name,
            'تعداد_مشتری': r.number_of_customers,
            'واسط_کارمند': r.employee_intermediary,
            'مرکز_فروش': r.sales_center,
            'تاریخ_ایجاد': r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for r in route_reports]
        customer_reports = CustomerReport.query.all()
        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customer_reports]
        return render_template('admin/index.html', route_data=route_data, customer_data=customer_data)

    @app.route('/admin/data')
    @login_required
    def admin_data():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('admin/data.html')

    # --------------------- CSV UPLOAD (Existing) ---------------------
    @app.route('/admin/upload_route_csv', methods=['POST'])
    @login_required
    def admin_upload_route_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('admin_routes_csv'))
        file = request.files.get('route_csv')
        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_routes_csv'))
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                report = RouteReport(
                    route_number=row.get('شماره_مسیر'),
                    route_name=row.get('نام_مسیر'),
                    number_of_customers=int(row.get('تعداد_مشتری')) if row.get('تعداد_مشتری') else None,
                    employee_intermediary=row.get('واسط_کارمند'),
                    sales_center=row.get('مرکز_فروش'),
                    created_at=datetime.utcnow()
                )
                db.session.add(report)
            db.session.commit()
            flash('فایل CSV اطلاعات مسیر با موفقیت بارگذاری و ذخیره شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')
        return redirect(url_for('admin_routes_csv'))

    @app.route('/admin/upload_customer_csv', methods=['POST'])
    @login_required
    def admin_upload_customer_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('admin_customers_csv'))
        file = request.files.get('customer_csv')
        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_customers_csv'))
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                report = CustomerReport(
                    textbox29=row.get('Textbox29'),
                    caption=row.get('Caption'),
                    bname=row.get('bname'),
                    number=row.get('Number'),
                    name=row.get('Name'),
                    textbox16=row.get('Textbox16'),
                    textbox12=row.get('Textbox12'),
                    longitude=safe_float(row.get('Longitude')),
                    latitude=safe_float(row.get('Latitude')),
                    textbox4=row.get('Textbox4'),
                    textbox10=row.get('Textbox10'),
                    created_at=datetime.utcnow()
                )
                db.session.add(report)
            db.session.commit()
            flash('فایل CSV اطلاعات مشتریان با موفقیت بارگذاری و ذخیره شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')
        return redirect(url_for('admin_customers_csv'))

    # --------------------- FULL-SCREEN CSV PAGES (Existing) ---------------------
    @app.route('/admin/routes-csv', methods=['GET'])
    @login_required
    def admin_routes_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        route_reports = RouteReport.query.all()
        route_data = [{
            'شماره_مسیر': r.route_number,
            'نام_مسیر': r.route_name,
            'تعداد_مشتری': r.number_of_customers,
            'واسط_کارمند': r.employee_intermediary,
            'مرکز_فروش': r.sales_center,
            'تاریخ_ایجاد': r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for r in route_reports]
        return render_template('admin/routes_csv.html', route_data=route_data)

    @app.route('/admin/customers-csv', methods=['GET'])
    @login_required
    def admin_customers_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        customer_reports = CustomerReport.query.all()
        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customer_reports]
        return render_template('admin/customers_csv.html', customer_data=customer_data)

    @app.route('/admin/customers-csv/map')
    @login_required
    def admin_customers_csv_map():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        customer_reports = CustomerReport.query.all()
        customer_data = [{
            'Textbox29': c.textbox29,
            'Caption': c.caption,
            'bname': c.bname,
            'Number': c.number,
            'Name': c.name,
            'Textbox16': c.textbox16,
            'Textbox12': c.textbox12,
            'Longitude': c.longitude,
            'Latitude': c.latitude,
            'Textbox4': c.textbox4,
            'Textbox10': c.textbox10,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customer_reports]
        return render_template('admin/customers_map.html', customer_data=customer_data)

    # --------------------- ADMIN: QUOTAS (Grade Mapping, Customer List & Evaluations) ---------------------
    @app.route('/admin/quotas', methods=['GET', 'POST'])
    @login_required
    def admin_quotas():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        gradeForm = GradeMappingForm()
        customers = CustomerReport.query.order_by(CustomerReport.number).all()
        grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()
        evaluations = CustomerEvaluation.query.order_by(CustomerEvaluation.evaluated_at.desc()).all()
        
        if request.method == 'POST':
            if gradeForm.validate_on_submit():
                grade_letter = gradeForm.grade_letter.data.strip()
                min_score = gradeForm.min_score.data
                new_mapping = GradeMapping(
                    grade_letter=grade_letter,
                    min_score=min_score
                )
                db.session.add(new_mapping)
                try:
                    db.session.commit()
                    flash(f'درجه {grade_letter} با حداقل نمره {min_score} ذخیره شد.', 'success')
                except IntegrityError:
                    db.session.rollback()
                    flash('خطا در ذخیره درجه. ممکن است این درجه تکراری باشد.', 'danger')
                return redirect(url_for('admin_quotas'))
            else:
                flash('خطا در اعتبارسنجی فرم.', 'danger')
                return redirect(url_for('admin_quotas'))
        
        return render_template('admin/quotas.html',
                               form=gradeForm,
                               customers=customers,
                               grade_mappings=grade_mappings,
                               evaluations=evaluations)

    # --------------------- ADMIN: EVALUATE CUSTOMER (Single Evaluation) ---------------------
    @app.route('/admin/evaluate_customer/<int:customer_id>', methods=['GET', 'POST'], endpoint='evaluate_customer')
    @login_required
    def evaluate_customer_view(customer_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        customer = CustomerReport.query.get_or_404(customer_id)
        form = CustomerEvaluationForm()
        form.customer_id.choices = [(customer.id, f"{customer.number} - {customer.name}")]
        form.customer_id.data = customer.id

        if request.method == 'POST':
            if form.validate_on_submit():
                total_score = (
                    form.sales_volume_weight.data * form.sales_volume_score.data +
                    form.sales_revenue_weight.data * form.sales_revenue_score.data +
                    form.sales_diversity_weight.data * form.sales_diversity_score.data +
                    form.store_dimensions_weight.data * form.store_dimensions_score.data +
                    form.street_visibility_weight.data * form.street_visibility_score.data +
                    form.location_city_weight.data * form.location_city_score.data +
                    form.location_zone_weight.data * form.location_zone_score.data +
                    form.ownership_owner_weight.data * form.ownership_owner_score.data +
                    form.ownership_rented_weight.data * form.ownership_rented_score.data +
                    form.ownership_owned_weight.data * form.ownership_owned_score.data +
                    form.cleanliness_weight.data * form.cleanliness_score.data +
                    form.equipment_weight.data * form.equipment_score.data +
                    form.luxury_weight.data * form.luxury_score.data +
                    form.brand_weight.data * form.brand_score.data
                )
                mapping_obj = GradeMapping.query.filter(GradeMapping.min_score <= total_score)\
                            .order_by(GradeMapping.min_score.desc()).first()
                if mapping_obj:
                    assigned_grade = mapping_obj.grade_letter
                else:
                    assigned_grade = "بدون درجه"
                flash(f'ارزیابی انجام شد. نمره کل: {total_score:.2f}, درجه: {assigned_grade}', 'success')
                evaluation = CustomerEvaluation(
                    customer_id=customer.id,
                    total_score=total_score,
                    assigned_grade=assigned_grade,
                    evaluated_at=datetime.utcnow()
                )
                db.session.add(evaluation)
                db.session.commit()
                return redirect(url_for('admin_quotas'))
            else:
                print("Evaluation form errors:", form.errors)
                flash('خطا در اعتبارسنجی فرم. لطفاً تمامی فیلدها را به درستی پر کنید.', 'danger')
        return render_template('admin/evaluate_customer.html', form=form, customer=customer)

    # --------------------- ADMIN: GRADE MAPPING EDIT ---------------------
    @app.route('/admin/quotas/edit/<int:mapping_id>', methods=['GET', 'POST'])
    @login_required
    def edit_grade_mapping(mapping_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        mapping = GradeMapping.query.get_or_404(mapping_id)
        form = GradeMappingForm(obj=mapping)
        if form.validate_on_submit():
            mapping.grade_letter = form.grade_letter.data.strip()
            mapping.min_score = form.min_score.data
            try:
                db.session.commit()
                flash('درجه با موفقیت ویرایش شد.', 'success')
                return redirect(url_for('admin_quotas'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ویرایش درجه.', 'danger')
        return render_template('admin/edit_grade_mapping.html', form=form, mapping=mapping)

    # --------------------- ADMIN: GRADE MAPPING DELETE ---------------------
    @app.route('/admin/quotas/delete/<int:mapping_id>', methods=['GET', 'POST'])
    @login_required
    def delete_grade_mapping(mapping_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        mapping = GradeMapping.query.get_or_404(mapping_id)
        db.session.delete(mapping)
        db.session.commit()
        flash('درجه حذف شد.', 'info')
        return redirect(url_for('admin_quotas'))

    # --------------------- ADMIN: USER MANAGEMENT ---------------------
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
                form.email.data = user_to_edit.email or ''
                form.fullname.data = user_to_edit.fullname
                form.is_active.data = user_to_edit.is_active
                form.role.data = user_to_edit.role
                edit_mode = True
        if form.validate_on_submit():
            email_value = form.email.data.strip() if form.email.data else None
            hashed_password = generate_password_hash(form.password.data)
            if edit_mode and user_to_edit:
                user_to_edit.username = form.username.data
                user_to_edit.password = hashed_password
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
                                        password=generate_password_hash(form.password.data),
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
        return render_template('admin/users.html',
                               users=users,
                               form=form,
                               edit_mode=edit_mode,
                               search_query=search_query,
                               count_admin=count_admin,
                               count_marketer=count_marketer,
                               count_observer=count_observer)

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

    # --------------------- ADMIN: ROUTE MANAGEMENT ---------------------
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

    # --------------------- ADMIN: DESCRIPTIVE CRITERIA MANAGEMENT ---------------------
    @app.route('/admin/descriptive_criteria', methods=['GET', 'POST'])
    @login_required
    def descriptive_criteria():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        criteria = DescriptiveCriterion.query.all()
        if request.method == 'POST':
            parameter = request.form.get('parameter')
            criterion = request.form.get('criterion')
            score = request.form.get('score')
            try:
                score = float(score)
            except:
                flash('نمره باید عددی باشد.', 'danger')
                return redirect(url_for('descriptive_criteria'))
            new_crit = DescriptiveCriterion(parameter_name=parameter, criterion=criterion, score=score)
            db.session.add(new_crit)
            try:
                db.session.commit()
                flash('معیار اضافه شد.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ذخیره معیار.', 'danger')
            return redirect(url_for('descriptive_criteria'))
        return render_template('admin/descriptive_criteria.html', criteria=criteria)

    @app.route('/admin/descriptive_criteria/edit/<int:crit_id>', methods=['GET', 'POST'])
    @login_required
    def edit_descriptive_criteria(crit_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        crit = DescriptiveCriterion.query.get_or_404(crit_id)
        if request.method == 'POST':
            crit.parameter_name = request.form.get('parameter')
            crit.criterion = request.form.get('criterion')
            try:
                crit.score = float(request.form.get('score'))
            except:
                flash('نمره باید عددی باشد.', 'danger')
                return redirect(url_for('edit_descriptive_criteria', crit_id=crit_id))
            try:
                db.session.commit()
                flash('معیار ویرایش شد.', 'success')
                return redirect(url_for('descriptive_criteria'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ویرایش معیار.', 'danger')
        return render_template('admin/edit_descriptive_criteria.html', crit=crit)

    @app.route('/admin/descriptive_criteria/delete/<int:crit_id>', methods=['POST'])
    @login_required
    def delete_descriptive_criteria(crit_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        crit = DescriptiveCriterion.query.get_or_404(crit_id)
        db.session.delete(crit)
        db.session.commit()
        flash('معیار حذف شد.', 'info')
        return redirect(url_for('descriptive_criteria'))

    # --------------------- ADMIN: EVALUATE WITH CSV/EXCEL ---------------------
    @app.route('/admin/evaluate_csv', methods=['GET', 'POST'])
    @login_required
    def admin_evaluate_csv():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        if request.method == 'GET':
            return render_template('admin/evaluate_csv_upload.html')
        else:
            action = request.form.get('action')
            if action == 'upload_file':
                file = request.files.get('file')
                if not file:
                    flash('هیچ فایلی انتخاب نشده است.', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                filename = file.filename.lower()
                try:
                    if filename.endswith('.csv'):
                        df = pd.read_csv(file)
                    elif filename.endswith(('.xls', '.xlsx')):
                        df = pd.read_excel(file)
                    else:
                        flash('فایل پشتیبانی نمی‌شود. لطفاً CSV یا Excel آپلود کنید.', 'danger')
                        return redirect(url_for('admin_evaluate_csv'))
                except Exception as e:
                    flash(f'خطا در خواندن فایل: {e}', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                columns = list(df.columns)
                file_content = df.to_csv(index=False)
                return render_template('admin/evaluate_csv_configure.html', columns=columns, file_content=file_content)
            elif action == 'configure':
                file_content = request.form.get('file_content')
                if not file_content:
                    flash('مشکل در بازیابی فایل آپلود شده.', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                config = {}
                # Build configuration for each column from checkboxes, weights, and types.
                for key in request.form:
                    if key.startswith('use_'):
                        col = key[4:]
                        if request.form.get(key) == 'on':
                            try:
                                weight = float(request.form.get(f'weight_{col}', 1))
                            except ValueError:
                                weight = 1
                            var_type = request.form.get(f'type_{col}', 'numeric')
                            config[col] = {'weight': weight, 'type': var_type}
                if not config:
                    flash('هیچ ستونی انتخاب نشده است.', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                try:
                    df = pd.read_csv(io.StringIO(file_content))
                except Exception as e:
                    flash(f'خطا در بازیابی فایل: {e}', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                valid_rows = []
                missing_rows = []
                total_scores = []
                grades = []
                # Process each row
                for index, row in df.iterrows():
                    missing = False
                    # Check for missing numeric values for selected numeric parameters
                    for col, params in config.items():
                        if params['type'] == 'numeric' and pd.isnull(row.get(col)):
                            missing = True
                            break
                    if missing:
                        missing_rows.append(row.to_dict())
                        continue
                    score = 0
                    for col, params in config.items():
                        val = row.get(col, 0)
                        if pd.isnull(val):
                            val = 0
                        if params['type'] == 'numeric':
                            try:
                                numeric_val = float(val)
                            except:
                                numeric_val = 0
                            score += params['weight'] * numeric_val
                        else:
                            # For descriptive parameters, look up the corresponding criterion.
                            # Here we assume that the cell value exactly matches one of the defined criteria (case-insensitive)
                            crit = DescriptiveCriterion.query.filter(
                                DescriptiveCriterion.parameter_name.ilike(col),
                                DescriptiveCriterion.criterion.ilike(str(val).strip())
                            ).first()
                            if crit:
                                numeric_val = crit.score
                            else:
                                numeric_val = 0
                            score += params['weight'] * numeric_val
                    total_scores.append(score)
                    grade_obj = GradeMapping.query.filter(GradeMapping.min_score <= score)\
                                    .order_by(GradeMapping.min_score.desc()).first()
                    if grade_obj:
                        assigned_grade = grade_obj.grade_letter
                    else:
                        assigned_grade = "بدون درجه"
                    grades.append(assigned_grade)
                    row_dict = row.to_dict()
                    row_dict["نمره کل"] = f"{score:.2f}"
                    row_dict["درجه"] = assigned_grade
                    valid_rows.append(row_dict)
                    # Update customer record if "Number" column exists
                    cust_number = row.get("Number")
                    if cust_number:
                        customer = CustomerReport.query.filter_by(number=str(cust_number)).first()
                        if customer:
                            customer.grade = assigned_grade
                            db.session.commit()
                # (Optionally, you can pass the list of descriptive parameters as well)
                descriptive_params = [col for col, params in config.items() if params['type'] == 'descriptive']
                return render_template('admin/evaluate_csv.html',
                                       valid_rows=valid_rows,
                                       missing_rows=missing_rows,
                                       descriptive_params=descriptive_params)
            else:
                flash('عملیات نامشخص.', 'danger')
                return redirect(url_for('admin_evaluate_csv'))

    return app

if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, port=5000)

                   
