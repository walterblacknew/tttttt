from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from extentions import db, login_manager
from models import (
    User, Route, RoutePoint, RouteAssignment,
    Store, EvaluationParameter, StoreEvaluation, StoreEvaluationDetail, QuotaCategory,
    CustomerReport, RouteReport, GradeMapping, CustomerEvaluation, DescriptiveCriterion,
    CSVEvaluationRecord, Province, ProvinceTarget
)
from forms import (
    LoginForm, UserForm, RouteForm, RoutePointForm,
    StoreForm, EvaluationParameterForm, StoreEvaluationForm, QuotaCategoryForm,
    GradeMappingForm, CustomerEvaluationForm, TargetSettingForm
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, desc, text
from datetime import datetime, timezone
import csv
import io
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
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
        # Use Session.get() instead of Query.get()
        return db.session.get(User, int(user_id))

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
                    created_at=datetime.now(timezone.utc)
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
        province = request.form.get('province')

        if not file:
            flash('هیچ فایلی انتخاب نشده است.', 'danger')
            return redirect(url_for('admin_customers_csv'))

        if not province:
            flash('لطفاً استان را انتخاب کنید.', 'danger')
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
                    province=province,  # Add the province
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(report)

            db.session.commit()
            flash(f'فایل CSV اطلاعات مشتریان برای استان {province} با موفقیت بارگذاری و ذخیره شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در پردازش فایل CSV: {e}', 'danger')
        return redirect(url_for('admin_customers_csv'))

    @app.route('/admin/customers-csv/preview/<province>')
    @login_required
    def preview_province_customers(province):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of records per page

        customers = CustomerReport.query.filter_by(province=province) \
            .order_by(CustomerReport.created_at.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

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
            'Province': c.province,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customers.items]

        return jsonify({
            'data': customer_data,
            'total': customers.total,
            'pages': customers.pages,
            'current_page': customers.page
        })

    @app.route('/admin/customers-csv/province/<province>/delete', methods=['POST'])
    @login_required
    def delete_province_customers(province):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        try:
            CustomerReport.query.filter_by(province=province).delete()
            db.session.commit()
            flash(f'تمام رکوردهای استان {province} با موفقیت حذف شدند.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف رکوردها: {e}', 'danger')

        return redirect(url_for('admin_customers_csv'))

    def upgrade_customer_report():
        """Add province column to customer_report table"""
        with app.app_context():
            # Add the province column if it doesn't exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('customer_report')]

            if 'province' not in columns:
                # Create the province column
                db.engine.execute('ALTER TABLE customer_report ADD COLUMN province VARCHAR(100)')

                # Set default province for existing records
                db.engine.execute("UPDATE customer_report SET province = 'نامشخص' WHERE province IS NULL")

                db.session.commit()

    @app.route('/admin/customers-csv/province/<province>')
    @login_required
    def get_province_customers(province):
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        customers = CustomerReport.query.filter_by(province=province).all()
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
            'Province': c.province,
            'تاریخ_ایجاد': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for c in customers]

        return jsonify(customer_data)



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

        try:
            # Create provinces if they don't exist
            if Province.query.count() == 0:
                provinces_data = [
                    ("تهران", 13267637),
                    ("خراسان رضوی", 6434501),
                    ("اصفهان", 5120850),
                    ("فارس", 4851274),
                    ("خوزستان", 4710509),
                    ("آذربایجان شرقی", 3909652),
                    ("مازندران", 3283582),
                    ("آذربایجان غربی", 3265219),
                    ("کرمان", 3164718),
                    ("سیستان و بلوچستان", 2775014),
                    ("البرز", 2712400),
                    ("گیلان", 2530696),
                    ("کرمانشاه", 1952434),
                    ("لرستان", 1760649),
                    ("همدان", 1738234),
                    ("گلستان", 1777014),
                    ("کردستان", 1603011),
                    ("هرمزگان", 1578183),
                    ("مرکزی", 1429475),
                    ("اردبیل", 1270420),
                    ("قزوین", 1201565),
                    ("قم", 1151672),
                    ("یزد", 1074428),
                    ("زنجان", 1015734),
                    ("بوشهر", 1032949),
                    ("چهارمحال و بختیاری", 895263),
                    ("خراسان شمالی", 867727),
                    ("کهگیلویه و بویراحمد", 658629),
                    ("خراسان جنوبی", 622534),
                    ("سمنان", 631218),
                    ("ایلام", 557599)
                ]

                for name, population in provinces_data:
                    province = Province(name=name, population=population)
                    db.session.add(province)

                try:
                    db.session.commit()
                    print("Provinces initialized successfully")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error initializing provinces: {e}")
                    flash('خطا در ایجاد استان‌ها', 'danger')

            # Get all provinces for the dropdown
            provinces = Province.query.order_by(Province.name).all()
            print(f"Found {len(provinces)} provinces")
            for p in provinces:
                print(f"Province: {p.name}")

            # Get all customer reports
            all_customers = CustomerReport.query.all()
            print(f"Found {len(all_customers)} customers")

            # Group data by province
            customer_data_by_province = {}
            column_headers = []

            if all_customers:
                # Get headers from first record
                sample_data = {
                    'Textbox29': all_customers[0].textbox29,
                    'Caption': all_customers[0].caption,
                    'bname': all_customers[0].bname,
                    'Number': all_customers[0].number,
                    'Name': all_customers[0].name,
                    'Textbox16': all_customers[0].textbox16,
                    'Textbox12': all_customers[0].textbox12,
                    'Longitude': all_customers[0].longitude,
                    'Latitude': all_customers[0].latitude,
                    'Textbox4': all_customers[0].textbox4,
                    'Textbox10': all_customers[0].textbox10,
                    'Province': all_customers[0].province,
                    'تاریخ_ایجاد': all_customers[0].created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                column_headers = list(sample_data.keys())

                # Group by province
                for customer in all_customers:
                    province_name = customer.province or 'نامشخص'

                    if province_name not in customer_data_by_province:
                        customer_data_by_province[province_name] = []

                    customer_data = {
                        'Textbox29': customer.textbox29,
                        'Caption': customer.caption,
                        'bname': customer.bname,
                        'Number': customer.number,
                        'Name': customer.name,
                        'Textbox16': customer.textbox16,
                        'Textbox12': customer.textbox12,
                        'Longitude': customer.longitude,
                        'Latitude': customer.latitude,
                        'Textbox4': customer.textbox4,
                        'Textbox10': customer.textbox10,
                        'Province': customer.province,
                        'تاریخ_ایجاد': customer.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    customer_data_by_province[province_name].append(customer_data)

            return render_template(
                'admin/customers_csv.html',
                provinces=provinces,
                customer_data_by_province=customer_data_by_province,
                column_headers=column_headers
            )
        except Exception as e:
            print(f"Error in admin_customers_csv: {str(e)}")
            flash(f'خطا در بارگذاری صفحه: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
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
        
        # Form for grade mapping
        gradeForm = GradeMappingForm()
        
        # Form for target setting
        targetForm = TargetSettingForm()
        
        # Get customer list
        customers = CustomerReport.query.order_by(CustomerReport.number).all()
        
        # Get grade mappings
        grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()
        
        # Get individual evaluations (manual evaluations, limited to 100)
        evaluations = CustomerEvaluation.query.filter(
            CustomerEvaluation.evaluation_method == 'manual'
        ).order_by(CustomerEvaluation.evaluated_at.desc()).limit(100).all()
        
        # SIMPLIFIED APPROACH: Get all distinct batch IDs from CSVEvaluationRecord
        batch_ids_query = text("SELECT DISTINCT batch_id FROM csv_evaluation_record WHERE batch_id IS NOT NULL")
        result = db.session.execute(batch_ids_query)
        batch_ids = [row[0] for row in result if row[0]]
        
        print(f"Found {len(batch_ids)} distinct batch IDs in CSVEvaluationRecord")
        
        # If no batches found in CSVEvaluationRecord, try looking in CustomerEvaluation as fallback
        if not batch_ids:
            batch_ids_query = text("SELECT DISTINCT batch_id FROM customer_evaluation WHERE batch_id IS NOT NULL")
            result = db.session.execute(batch_ids_query)
            batch_ids = [row[0] for row in result if row[0]]
            print(f"Fallback: Found {len(batch_ids)} distinct batch IDs in CustomerEvaluation")
        
        # Process each batch
        batch_evaluations = []
        batch_statistics = {}
        
        for batch_id in batch_ids:
            # Get count of evaluations in batch from CSVEvaluationRecord
            count_query = text("SELECT COUNT(*) FROM csv_evaluation_record WHERE batch_id = :batch_id")
            count = db.session.execute(count_query, {"batch_id": batch_id}).scalar() or 0
            
            # If count is 0, try CustomerEvaluation as fallback
            if count == 0:
                count_query = text("SELECT COUNT(*) FROM customer_evaluation WHERE batch_id = :batch_id")
                count = db.session.execute(count_query, {"batch_id": batch_id}).scalar() or 0
            
            # Get latest evaluation date
            date_query = text("SELECT MAX(evaluated_at) FROM csv_evaluation_record WHERE batch_id = :batch_id")
            latest_date = db.session.execute(date_query, {"batch_id": batch_id}).scalar()
            
            # If no date found, try CustomerEvaluation as fallback
            if not latest_date:
                date_query = text("SELECT MAX(evaluated_at) FROM customer_evaluation WHERE batch_id = :batch_id")
                latest_date = db.session.execute(date_query, {"batch_id": batch_id}).scalar()
            
            # Create batch info object
            if count > 0 and latest_date:
                batch_info = {
                    'batch_id': batch_id,
                    'count': count,
                    'evaluated_at': latest_date if isinstance(latest_date, datetime) else str(latest_date)
                }
                batch_evaluations.append(batch_info)
                
                # Get grade distribution
                grade_query = text("""
                    SELECT assigned_grade, COUNT(*) as count 
                    FROM csv_evaluation_record 
                    WHERE batch_id = :batch_id 
                    GROUP BY assigned_grade
                """)
                grade_dist = db.session.execute(grade_query, {"batch_id": batch_id}).fetchall()
                grade_counts = {grade[0]: grade[1] for grade in grade_dist}
                
                # If no grades found, try CustomerEvaluation as fallback
                if not grade_counts:
                    grade_query = text("""
                        SELECT assigned_grade, COUNT(*) as count 
                        FROM customer_evaluation 
                        WHERE batch_id = :batch_id 
                        GROUP BY assigned_grade
                    """)
                    grade_dist = db.session.execute(grade_query, {"batch_id": batch_id}).fetchall()
                    grade_counts = {grade[0]: grade[1] for grade in grade_dist}
                
                # Calculate average score
                avg_query = text("SELECT AVG(total_score) FROM csv_evaluation_record WHERE batch_id = :batch_id")
                avg_score = db.session.execute(avg_query, {"batch_id": batch_id}).scalar() or 0
                
                # If no average found, try CustomerEvaluation as fallback
                if avg_score == 0:
                    avg_query = text("SELECT AVG(total_score) FROM customer_evaluation WHERE batch_id = :batch_id")
                    avg_score = db.session.execute(avg_query, {"batch_id": batch_id}).scalar() or 0
                
                # Store statistics
                batch_statistics[batch_id] = {
                    'grades': grade_counts,
                    'avg_score': round(avg_score, 2),
                    'count': count,
                    'date': latest_date if isinstance(latest_date, datetime) else str(latest_date)
                }
        
        # Sort batches by evaluation date (newest first)
        batch_evaluations = sorted(batch_evaluations, key=lambda x: x.get('evaluated_at', datetime.min), reverse=True)
        
        # Get provinces and targets for the target setting section
        provinces = Province.query.order_by(Province.name).all()
        
        # Get province targets if they exist
        province_targets = {}
        targets = ProvinceTarget.query.order_by(ProvinceTarget.id.desc()).limit(31).all()
        
        # Create a mapping of province ID to target
        for target in targets:
            if target.province_id not in province_targets:
                province_targets[target.province_id] = target
        
        # Process POST request for target setting
        if 'submit_target' in request.form:
            liter_enabled = 'liter_enabled' in request.form
            shrink_enabled = 'shrink_enabled' in request.form
            
            if not liter_enabled and not shrink_enabled:
                flash('لطفاً حداقل یکی از ظرفیت‌ها را انتخاب کنید.', 'warning')
                return redirect(url_for('admin_quotas'))
            
            liter_capacity = float(request.form.get('liter_capacity', 0)) if liter_enabled else 0
            shrink_capacity = float(request.form.get('shrink_capacity', 0)) if shrink_enabled else 0
            
            # Calculate total population to compute percentages
            total_population = sum(province.population for province in provinces)
            
            # Clear previous targets
            ProvinceTarget.query.delete()
            
            # Create new targets for each province
            for province in provinces:
                percentage = province.population / total_population
                
                target = ProvinceTarget(
                    province_id=province.id,
                    liter_capacity=liter_capacity * percentage if liter_enabled else None,
                    shrink_capacity=shrink_capacity * percentage if shrink_enabled else None,
                    liter_percentage=percentage * 100 if liter_enabled else None,
                    shrink_percentage=percentage * 100 if shrink_enabled else None
                )
                db.session.add(target)
            
            try:
                db.session.commit()
                flash('تارگت‌ها با موفقیت محاسبه و ذخیره شدند.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در ذخیره تارگت‌ها: {str(e)}', 'danger')
            
            return redirect(url_for('admin_quotas'))
        
        # Process POST request for new grade mapping
        if request.method == 'POST' and 'grade_letter' in request.form:
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
                            target_form=targetForm,
                            customers=customers,
                            grade_mappings=grade_mappings,
                            evaluations=evaluations,
                            batch_evaluations=batch_evaluations,
                            batch_statistics=batch_statistics,
                            provinces=provinces,
                            province_targets=province_targets)

    # --------------------- ADMIN: PROVINCE TARGETS MANAGEMENT ---------------------
    @app.route('/admin/init_provinces')
    @login_required
    def init_provinces():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Check if provinces already exist
        if Province.query.count() > 0:
            flash('استان‌ها قبلاً اضافه شده‌اند.', 'info')
            return redirect(url_for('admin_customers_csv'))

        # Province data (name, population)
        provinces_data = [
            ("تهران", 13267637),
            ("خراسان رضوی", 6434501),
            ("اصفهان", 5120850),
            ("فارس", 4851274),
            ("خوزستان", 4710509),
            ("آذربایجان شرقی", 3909652),
            ("مازندران", 3283582),
            ("آذربایجان غربی", 3265219),
            ("کرمان", 3164718),
            ("سیستان و بلوچستان", 2775014),
            ("البرز", 2712400),
            ("گیلان", 2530696),
            ("کرمانشاه", 1952434),
            ("لرستان", 1760649),
            ("همدان", 1738234),
            ("گلستان", 1777014),
            ("کردستان", 1603011),
            ("هرمزگان", 1578183),
            ("مرکزی", 1429475),
            ("اردبیل", 1270420),
            ("قزوین", 1201565),
            ("قم", 1151672),
            ("یزد", 1074428),
            ("زنجان", 1015734),
            ("بوشهر", 1032949),
            ("چهارمحال و بختیاری", 895263),
            ("خراسان شمالی", 867727),
            ("کهگیلویه و بویراحمد", 658629),
            ("خراسان جنوبی", 622534),
            ("سمنان", 631218),
            ("ایلام", 557599)
        ]

        for name, population in provinces_data:
            province = Province(name=name, population=population)
            db.session.add(province)

        try:
            db.session.commit()
            flash('استان‌ها با موفقیت اضافه شدند.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در اضافه کردن استان‌ها: {str(e)}', 'danger')

        return redirect(url_for('admin_customers_csv'))

    @app.route('/admin/province_targets')
    @login_required
    def admin_province_targets():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))

        # Get provinces and targets
        provinces = Province.query.order_by(Province.name).all()

        # Get the latest target for each province
        province_targets = {}
        for province in provinces:
            target = ProvinceTarget.query.filter_by(province_id=province.id).order_by(ProvinceTarget.id.desc()).first()
            if target:
                province_targets[province.id] = target

        # Get customers by province
        customers_by_province = {}
        for province in provinces:
            customers = CustomerReport.query.filter_by(province=province.name).all()
            customers_by_province[province.id] = customers

        # Get all grade mappings for allocation by grade
        grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()

        # Count customers by grade for each province
        customer_grades_by_province = {}
        for province_id, customers in customers_by_province.items():
            grade_counts = {}
            for grade_mapping in grade_mappings:
                grade_counts[grade_mapping.grade_letter] = 0

            # Count ungraded customers too
            grade_counts['بدون درجه'] = 0

            for customer in customers:
                if customer.grade in grade_counts:
                    grade_counts[customer.grade] += 1
                else:
                    grade_counts['بدون درجه'] += 1

            customer_grades_by_province[province_id] = grade_counts

        # Get grade weights from session or set defaults
        grade_weights = session.get('grade_weights', {})

        # If no weights in session, set defaults based on min_score
        if not grade_weights:
            for grade_mapping in grade_mappings:
                # Set weights based on min_score (higher score = higher weight)
                grade_weights[grade_mapping.grade_letter] = grade_mapping.min_score / 100

            # Default weight for ungraded customers
            grade_weights['بدون درجه'] = 0.5

        # Check what capacities were set (for table headers)
        has_liter = any(t.liter_capacity is not None for t in province_targets.values()) if province_targets else False
        has_shrink = any(
            t.shrink_capacity is not None for t in province_targets.values()) if province_targets else False

        # Calculate per-customer allocation by grade
        allocation_by_province_and_grade = {}

        for province_id, target in province_targets.items():
            if province_id not in customer_grades_by_province:
                continue

            grade_counts = customer_grades_by_province[province_id]
            allocation_by_grade = {}

            # Calculate total weighted count
            total_weighted_count = 0
            for grade, count in grade_counts.items():
                weight = grade_weights.get(grade, 0.5)  # Default weight if grade not found
                total_weighted_count += count * weight

            # Calculate allocation per customer by grade
            for grade, count in grade_counts.items():
                if count == 0 or total_weighted_count == 0:
                    allocation_by_grade[grade] = {
                        'liter': None,
                        'shrink': None,
                        'count': count
                    }
                    continue

                weight = grade_weights.get(grade, 0.5)

                # Calculate total allocation for this grade group
                if has_liter and target.liter_capacity is not None:
                    liter_per_customer = (
                                                     target.liter_capacity * weight * count / total_weighted_count) / count if count > 0 else 0
                else:
                    liter_per_customer = None

                if has_shrink and target.shrink_capacity is not None:
                    shrink_per_customer = (
                                                      target.shrink_capacity * weight * count / total_weighted_count) / count if count > 0 else 0
                else:
                    shrink_per_customer = None

                allocation_by_grade[grade] = {
                    'liter': liter_per_customer,
                    'shrink': shrink_per_customer,
                    'count': count
                }

            allocation_by_province_and_grade[province_id] = allocation_by_grade

        return render_template('admin/province_targets.html',
                               provinces=provinces,
                               province_targets=province_targets,
                               has_liter=has_liter,
                               has_shrink=has_shrink,
                               customers_by_province=customers_by_province,
                               customer_grades_by_province=customer_grades_by_province,
                               grade_mappings=grade_mappings,
                               grade_weights=grade_weights,
                               allocation_by_province_and_grade=allocation_by_province_and_grade)

    @app.route('/admin/update_grade_weights', methods=['POST'])
    @login_required
    def update_grade_weights():
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        # Get data from the form
        weights = {}
        for key, value in request.form.items():
            if key.startswith('weight_'):
                grade = key[7:]  # Remove 'weight_' prefix
                try:
                    weights[grade] = float(value)
                except ValueError:
                    pass

        # Store weights in session for persistence
        session['grade_weights'] = weights

        flash('وزن‌های درجه‌بندی با موفقیت به‌روزرسانی شدند.', 'success')
        return redirect(url_for('admin_province_targets'))
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
                    evaluated_at=datetime.now(timezone.utc),
                    evaluation_method="manual"
                )
                
                # Update customer's grade
                customer.grade = assigned_grade
                
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

    # --------------------- ADMIN: EVALUATE WITH CSV/EXCEL (Enhanced) ---------------------
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
                
                # Get all defined descriptive criteria for dropdown options
                descriptive_criteria = DescriptiveCriterion.query.all()
                criteria_by_param = {}
                for crit in descriptive_criteria:
                    if crit.parameter_name not in criteria_by_param:
                        criteria_by_param[crit.parameter_name] = []
                    criteria_by_param[crit.parameter_name].append({
                        'criterion': crit.criterion,
                        'score': crit.score
                    })

                # Get all grade mappings for debugging/display
                grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()
                    
                return render_template('admin/evaluate_csv_configure.html', 
                                      columns=columns, 
                                      file_content=file_content,
                                      criteria_by_param=criteria_by_param,
                                      grade_mappings=grade_mappings)
                                      
            elif action == 'configure':
                file_content = request.form.get('file_content')
                if not file_content:
                    flash('مشکل در بازیابی فایل آپلود شده.', 'danger')
                    return redirect(url_for('admin_evaluate_csv'))
                    
                config = {}
                criteria_config = {}
                
                # Build configuration for each column from checkboxes, weights, and types
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
                            
                            # For descriptive parameters, collect the criteria data
                            if var_type == 'descriptive':
                                criteria_config[col] = []
                                
                                # Get new criteria added in the form
                                criteria_values = request.form.getlist(f'criteria_{col}[]')
                                criteria_scores = request.form.getlist(f'score_{col}[]')
                                
                                for i in range(len(criteria_values)):
                                    if i < len(criteria_scores):
                                        try:
                                            score = float(criteria_scores[i])
                                            criteria_config[col].append({
                                                'criterion': criteria_values[i],
                                                'score': score
                                            })
                                        except (ValueError, IndexError):
                                            continue
                                            
                                # Get existing criteria (that may have been edited)
                                existing_criteria = request.form.getlist(f'existing_criteria_{col}[]')
                                existing_scores = request.form.getlist(f'existing_score_{col}[]')
                                
                                for i in range(len(existing_criteria)):
                                    if i < len(existing_scores):
                                        try:
                                            score = float(existing_scores[i])
                                            criteria_config[col].append({
                                                'criterion': existing_criteria[i],
                                                'score': score
                                            })
                                        except (ValueError, IndexError):
                                            continue
                                    
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
                
                # Get all grade mappings for scoring
                all_grade_mappings = GradeMapping.query.order_by(GradeMapping.min_score.desc()).all()
                
                # Create a batch identifier for this evaluation session
                evaluation_batch_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
                print(f"Created batch ID: {evaluation_batch_id}")
                
                # Process each row
                successful_evaluations = 0
                
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
                    parameter_scores = {}
                    
                    for col, params in config.items():
                        val = row.get(col, 0)
                        if pd.isnull(val):
                            val = 0
                            
                        # Handle different parameter types
                        if params['type'] == 'numeric':
                            try:
                                numeric_val = float(val)
                            except:
                                numeric_val = 0
                            param_score = params['weight'] * numeric_val
                            
                        else:
                            # For descriptive parameters, look up the corresponding criterion
                            val_str = str(val).strip()
                            param_score = 0
                            
                            # First check if we have specific criteria defined in the form
                            if col in criteria_config:
                                found_match = False
                                for criterion_data in criteria_config[col]:
                                    if criterion_data['criterion'].lower() == val_str.lower():
                                        # Multiply by weight here
                                        param_score = params['weight'] * criterion_data['score']
                                        found_match = True
                                        break
                                
                                # If no match was found in the form criteria, check database
                                if not found_match:
                                    # Otherwise use existing criteria from database
                                    crit = DescriptiveCriterion.query.filter(
                                        DescriptiveCriterion.parameter_name.ilike(col),
                                        DescriptiveCriterion.criterion.ilike(val_str)
                                    ).first()
                                    if crit:
                                        param_score = params['weight'] * crit.score
                                    
                        # Add to total score and track individual parameter score
                        score += param_score
                        parameter_scores[col] = param_score
                    
                    # Round score to 2 decimal places for consistency
                    score = round(score, 2)
                    total_scores.append(score)
                    
                    # Find the appropriate grade based on the score
                    mapping_obj = GradeMapping.query.filter(GradeMapping.min_score <= score)\
                                .order_by(GradeMapping.min_score.desc()).first()
                                
                    if mapping_obj:
                        assigned_grade = mapping_obj.grade_letter
                    else:
                        assigned_grade = "بدون درجه"
                        
                    grades.append(assigned_grade)
                    
                    row_dict = row.to_dict()
                    row_dict["نمره کل"] = f"{score:.2f}"
                    row_dict["درجه"] = assigned_grade
                    row_dict["batch_id"] = evaluation_batch_id
                    
                    # Add parameter scores to row data
                    for param, param_score in parameter_scores.items():
                        row_dict[f"نمره {param}"] = f"{param_score:.2f}"
                        
                    valid_rows.append(row_dict)
                    
                    # Always create a CSV evaluation record regardless of customer match
                    try:
                        # Create a new CSVEvaluationRecord
                        csv_record = CSVEvaluationRecord(
                            row_data=row_dict,
                            total_score=score,
                            assigned_grade=assigned_grade,
                            evaluated_at=datetime.now(timezone.utc),
                            batch_id=evaluation_batch_id
                        )
                        
                        # Associate with customer if found
                        cust_number = row.get("Number")
                        if cust_number:
                            customer = CustomerReport.query.filter_by(number=str(cust_number)).first()
                            if customer:
                                print(f"Found customer with ID: {customer.id} for number: {cust_number}")
                                
                                # Link to customer and update customer's grade
                                csv_record.customer_id = customer.id
                                customer.grade = assigned_grade
                                
                                # Also create a CustomerEvaluation record for backward compatibility
                                try:
                                    new_evaluation = CustomerEvaluation(
                                        customer_id=customer.id,
                                        total_score=score,
                                        assigned_grade=assigned_grade,
                                        evaluated_at=datetime.now(timezone.utc),
                                        evaluation_method="csv",
                                        batch_id=evaluation_batch_id
                                    )
                                    db.session.add(new_evaluation)
                                except Exception as e:
                                    print(f"Error creating CustomerEvaluation for {cust_number}: {e}")
                        
                        # Add and commit the CSV record
                        db.session.add(csv_record)
                        db.session.commit()
                        successful_evaluations += 1
                        print(f"Saved evaluation record for row {index} with grade {assigned_grade}")
                    except Exception as e:
                        db.session.rollback()
                        print(f"Error saving evaluation record for row {index}: {e}")
                        
                # Get list of descriptive parameters for the template
                descriptive_params = [col for col, params in config.items() if params['type'] == 'descriptive']
                
                # Save the criteria to database if they don't exist yet
                try:
                    for col, criteria_list in criteria_config.items():
                        for criteria_data in criteria_list:
                            existing = DescriptiveCriterion.query.filter_by(
                                parameter_name=col,
                                criterion=criteria_data['criterion']
                            ).first()
                            
                            if not existing:
                                new_criterion = DescriptiveCriterion(
                                    parameter_name=col,
                                    criterion=criteria_data['criterion'],
                                    score=criteria_data['score']
                                )
                                db.session.add(new_criterion)
                            elif existing.score != criteria_data['score']:
                                # Update score if it's different
                                existing.score = criteria_data['score']
                    
                    db.session.commit()
                    print("Successfully saved all criteria")
                    flash(f'ارزیابی با موفقیت انجام شد. {successful_evaluations} مشتری ارزیابی شدند.', 'success')
                except Exception as e:
                    db.session.rollback()
                    print(f"Error saving criteria: {e}")
                    flash(f'خطا در ذخیره‌سازی معیارها: {e}', 'danger')
                    
                return render_template('admin/evaluate_csv.html',
                                      valid_rows=valid_rows,
                                      missing_rows=missing_rows,
                                      descriptive_params=descriptive_params,
                                      config=config,
                                      grades=grades,
                                      grade_mappings=all_grade_mappings,
                                      batch_id=evaluation_batch_id)
            else:
                flash('عملیات نامشخص.', 'danger')
                return redirect(url_for('admin_evaluate_csv'))

    # --------------------- NEW ROUTES FOR BATCH EVALUATION MANAGEMENT ---------------------
    @app.route('/admin/batch_evaluations/<batch_id>')
    @login_required
    def view_batch_evaluations(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        
        # First try CSVEvaluationRecord
        csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).order_by(
            CSVEvaluationRecord.total_score.desc()
        ).all()
        
        # If no CSV records found, fallback to CustomerEvaluation
        if not csv_evals:
            customer_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).order_by(
                desc(CustomerEvaluation.total_score)
            ).all()
            
            if not customer_evals:
                flash('دسته ارزیابی یافت نشد.', 'warning')
                return redirect(url_for('admin_quotas'))
            
            # Get statistics for customer_evals
            grade_dist = db.session.query(
                CustomerEvaluation.assigned_grade,
                db.func.count(CustomerEvaluation.id).label('count')
            ).filter(CustomerEvaluation.batch_id == batch_id).\
            group_by(CustomerEvaluation.assigned_grade).all()
            
            # Format as dictionary for easy access in template
            grade_counts = {grade.assigned_grade: grade.count for grade in grade_dist}
            
            # Calculate average score
            avg_score = db.session.query(
                db.func.avg(CustomerEvaluation.total_score)
            ).filter(CustomerEvaluation.batch_id == batch_id).scalar() or 0
            
            return render_template('admin/batch_evaluations.html', 
                                batch_id=batch_id,
                                evaluations=customer_evals,
                                grade_counts=grade_counts,
                                avg_score=round(avg_score, 2),
                                date=customer_evals[0].evaluated_at if customer_evals else None,
                                is_csv_record=False)
        else:
            # Get grade distribution for CSVEvaluationRecord
            grade_query = text("""
                SELECT assigned_grade, COUNT(*) as count 
                FROM csv_evaluation_record 
                WHERE batch_id = :batch_id 
                GROUP BY assigned_grade
            """)
            grade_dist = db.session.execute(grade_query, {"batch_id": batch_id}).fetchall()
            grade_counts = {grade[0]: grade[1] for grade in grade_dist}
            
            # Calculate average score
            avg_query = text("SELECT AVG(total_score) FROM csv_evaluation_record WHERE batch_id = :batch_id")
            avg_score = db.session.execute(avg_query, {"batch_id": batch_id}).scalar() or 0
            
            return render_template('admin/batch_evaluations.html', 
                                batch_id=batch_id,
                                evaluations=csv_evals,
                                grade_counts=grade_counts,
                                avg_score=round(avg_score, 2),
                                date=csv_evals[0].evaluated_at if csv_evals else None,
                                is_csv_record=True)

    @app.route('/admin/batch_evaluations/delete/<batch_id>', methods=['POST'])
    @login_required
    def delete_batch_evaluations(batch_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
            
        try:
            # Delete from CSVEvaluationRecord
            csv_evals = CSVEvaluationRecord.query.filter_by(batch_id=batch_id).all()
            for eval in csv_evals:
                db.session.delete(eval)
            
            # Also delete from CustomerEvaluation for compatibility
            customer_evals = CustomerEvaluation.query.filter_by(batch_id=batch_id).all()
            for eval in customer_evals:
                db.session.delete(eval)
                
            db.session.commit()
            flash(f'دسته ارزیابی با موفقیت حذف شد.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف دسته ارزیابی: {e}', 'danger')
            
        return redirect(url_for('admin_quotas'))
        
    @app.route('/admin/evaluations/delete/<int:eval_id>', methods=['POST'])
    @login_required
    def delete_evaluation(eval_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
            
        try:
            # First try CSVEvaluationRecord
            evaluation = CSVEvaluationRecord.query.get(eval_id)
            
            # If not found, try CustomerEvaluation
            if not evaluation:
                evaluation = CustomerEvaluation.query.get_or_404(eval_id)
            
            # Save batch_id for redirect
            batch_id = evaluation.batch_id
            
            db.session.delete(evaluation)
            db.session.commit()
            flash('ارزیابی با موفقیت حذف شد.', 'success')
            
            # Redirect based on where the delete was initiated
            if batch_id:
                return redirect(url_for('view_batch_evaluations', batch_id=batch_id))
            else:
                return redirect(url_for('admin_quotas'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در حذف ارزیابی: {e}', 'danger')
            
        return redirect(url_for('admin_quotas'))

    # Edit individual evaluation
    @app.route('/admin/evaluations/edit/<int:eval_id>', methods=['GET', 'POST'])
    @login_required
    def edit_evaluation(eval_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        
        # First try to find in CSVEvaluationRecord
        evaluation = CSVEvaluationRecord.query.get(eval_id)
        is_csv_record = True
        
        # If not found, try CustomerEvaluation
        if not evaluation:
            evaluation = CustomerEvaluation.query.get_or_404(eval_id)
            is_csv_record = False
        
        if request.method == 'POST':
            try:
                new_score = float(request.form.get('total_score'))
                
                # Get appropriate grade based on the score
                mapping_obj = GradeMapping.query.filter(GradeMapping.min_score <= new_score)\
                            .order_by(GradeMapping.min_score.desc()).first()
                
                if mapping_obj:
                    new_grade = mapping_obj.grade_letter
                else:
                    new_grade = "بدون درجه"
                
                # Update evaluation record
                evaluation.total_score = new_score
                evaluation.assigned_grade = new_grade
                
                # If it's a CSVEvaluationRecord, also update the row_data
                if is_csv_record and evaluation.row_data:
                    evaluation.row_data["نمره کل"] = f"{new_score:.2f}"
                    evaluation.row_data["درجه"] = new_grade
                
                # If associated with a customer, update customer's grade
                if hasattr(evaluation, 'customer_id') and evaluation.customer_id:
                    customer = None
                    if is_csv_record:
                        customer = CustomerReport.query.get(evaluation.customer_id)
                    else:
                        customer = evaluation.customer
                    
                    if customer:
                        customer.grade = new_grade
                
                db.session.commit()
                flash('ارزیابی با موفقیت ویرایش شد.', 'success')
                
                # Redirect based on where the edit was initiated (batch view or main quotas page)
                if evaluation.batch_id:
                    return redirect(url_for('view_batch_evaluations', batch_id=evaluation.batch_id))
                else:
                    return redirect(url_for('admin_quotas'))
            
            except ValueError:
                flash('نمره باید عددی باشد.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'خطا در ویرایش ارزیابی: {e}', 'danger')
        
        # Modify the template to handle both types
        return render_template('admin/edit_evaluation.html', 
                            evaluation=evaluation, 
                            grade_mappings=GradeMapping.query.order_by(GradeMapping.min_score.desc()).all(),
                            is_csv_record=is_csv_record)

    # --------------------- ADMIN: QUOTA CATEGORIES MANAGEMENT ---------------------
    @app.route('/admin/quota_categories', methods=['GET', 'POST'])
    @login_required
    def admin_quota_categories():
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        form = QuotaCategoryForm()
        quota_list = QuotaCategory.query.all()
        
        if form.validate_on_submit():
            category = form.category.data.strip()
            monthly_quota = form.monthly_quota.data
            
            new_category = QuotaCategory(
                category=category,
                monthly_quota=monthly_quota
            )
            
            try:
                db.session.add(new_category)
                db.session.commit()
                flash(f'سهمیه برای دسته {category} با موفقیت تعریف شد.', 'success')
                return redirect(url_for('admin_quota_categories'))
            except IntegrityError:
                db.session.rollback()
                flash('خطا در ذخیره سهمیه. احتمالاً این دسته قبلاً تعریف شده است.', 'danger')
        
        return render_template('admin/quota_categories.html', form=form, quota_list=quota_list)

    @app.route('/admin/quota_categories/delete/<int:qc_id>', methods=['POST'])
    @login_required
    def delete_quota_category(qc_id):
        if current_user.role != 'admin':
            flash('دسترسی غیرمجاز!', 'danger')
            return redirect(url_for('dashboard'))
        
        quota_category = QuotaCategory.query.get_or_404(qc_id)
        db.session.delete(quota_category)
        db.session.commit()
        flash('سهمیه با موفقیت حذف شد.', 'info')
        return redirect(url_for('admin_quota_categories'))

    # --------------------- API ENDPOINTS ---------------------
    @app.route('/api/observer/marketer-locations')
    @login_required
    def api_marketer_locations():
        if current_user.role not in ['admin', 'observer']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        marketers = User.query.filter_by(role='marketer').all()
        result = []
        
        for marketer in marketers:
            location_data = {
                'id': marketer.id,
                'name': marketer.fullname or marketer.username,
                'lat': marketer.current_lat,
                'lng': marketer.current_lng,
                'last_update': marketer.last_location_update.strftime('%Y-%m-%d %H:%M:%S') if marketer.last_location_update else None
            }
            result.append(location_data)
        
        return jsonify(result)

    # Add API endpoint for marketer to update location
    @app.route('/api/marketer/update-location', methods=['POST'])
    @login_required
    def api_update_location():
        if current_user.role != 'marketer':
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.json
        if not data or 'lat' not in data or 'lng' not in data:
            return jsonify({'error': 'Invalid data'}), 400
        
        try:
            current_user.current_lat = float(data['lat'])
            current_user.current_lng = float(data['lng'])
            current_user.last_location_update = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Location updated'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    return app

if __name__ == '__main__':
   application = create_app()
   application.run(debug=True, port=5000)