from extentions import db
from flask_login import UserMixin
from datetime import datetime, timezone


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='marketer')
    email = db.Column(db.String(120), unique=True, nullable=True)
    fullname = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    # Fields for live location updates
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    assigned_routes = db.relationship('RouteAssignment', backref='marketer', lazy=True)

    def __repr__(self):
        return f'<User {self.username}, role={self.role}>'


class Route(db.Model):
    __tablename__ = 'route'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field
    points = db.relationship('RoutePoint', backref='route', lazy=True, order_by='RoutePoint.order')
    assignments = db.relationship('RouteAssignment', backref='route', lazy=True)

    def __repr__(self):
        return f'<Route {self.name}>'


class RoutePoint(db.Model):
    __tablename__ = 'route_point'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<RoutePoint {self.name} ({self.latitude}, {self.longitude})>'


class RouteAssignment(db.Model):
    __tablename__ = 'route_assignment'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    marketer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<RouteAssignment route={self.route_id}, marketer={self.marketer_id}>'


class Store(db.Model):
    __tablename__ = 'store'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field

    def __repr__(self):
        return f'<Store {self.name} lat={self.lat} lng={self.lng}>'


class EvaluationParameter(db.Model):
    __tablename__ = 'evaluation_parameter'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<EvaluationParameter {self.name} (weight={self.weight})>'


class StoreEvaluation(db.Model):
    __tablename__ = 'store_evaluation'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    total_score = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    province = db.Column(db.String(100), nullable=True)  # Added province field

    store = db.relationship('Store', backref='evaluations', lazy=True)
    details = db.relationship('StoreEvaluationDetail', backref='evaluation', lazy=True)

    def __repr__(self):
        return f'<StoreEvaluation store={self.store_id}, total_score={self.total_score}>'


class StoreEvaluationDetail(db.Model):
    __tablename__ = 'store_evaluation_detail'
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('store_evaluation.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('evaluation_parameter.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)

    parameter = db.relationship('EvaluationParameter', backref='evaluation_details', lazy=True)

    def __repr__(self):
        return f'<StoreEvaluationDetail eval={self.evaluation_id}, param={self.parameter_id}, score={self.score}>'


class QuotaCategory(db.Model):
    __tablename__ = 'quota_category'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False, unique=True)
    monthly_quota = db.Column(db.Integer, default=100)

    def __repr__(self):
        return f'<QuotaCategory {self.category} quota={self.monthly_quota}>'


class CustomerReport(db.Model):
    __tablename__ = 'customer_report'
    id = db.Column(db.Integer, primary_key=True)
    textbox29 = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.String(255), nullable=True)
    bname = db.Column(db.String(255), nullable=True)
    number = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    textbox16 = db.Column(db.String(255), nullable=True)
    textbox12 = db.Column(db.String(255), nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    textbox4 = db.Column(db.String(255), nullable=True)
    textbox10 = db.Column(db.String(255), nullable=True)
    grade = db.Column(db.String(10), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Province field
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    evaluations = db.relationship('CustomerEvaluation', backref='customer', lazy=True)
    csv_evaluations = db.relationship('CSVEvaluationRecord', backref='customer', lazy=True)

    def __repr__(self):
        return f'<CustomerReport {self.name}>'


class RouteReport(db.Model):
    __tablename__ = 'route_report'
    id = db.Column(db.Integer, primary_key=True)
    route_number = db.Column(db.String(50), nullable=True)
    route_name = db.Column(db.String(255), nullable=True)
    number_of_customers = db.Column(db.Integer, nullable=True)
    employee_intermediary = db.Column(db.String(255), nullable=True)
    sales_center = db.Column(db.String(255), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<RouteReport {self.route_name}>'


class GradeMapping(db.Model):
    __tablename__ = 'grade_mapping'
    id = db.Column(db.Integer, primary_key=True)
    grade_letter = db.Column(db.String(10), unique=True, nullable=False)
    min_score = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<GradeMapping {self.grade_letter}: {self.min_score}>'


class CustomerEvaluation(db.Model):
    __tablename__ = 'customer_evaluation'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_report.id'), nullable=False)
    total_score = db.Column(db.Float, nullable=False)
    assigned_grade = db.Column(db.String(10), nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    evaluation_method = db.Column(db.String(20), default='manual')
    batch_id = db.Column(db.String(50), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field

    def __repr__(self):
        return f'<CustomerEvaluation customer={self.customer_id}, grade={self.assigned_grade}, score={self.total_score}>'


class DescriptiveCriterion(db.Model):
    __tablename__ = 'descriptive_criterion'
    id = db.Column(db.Integer, primary_key=True)
    parameter_name = db.Column(db.String(255), nullable=False)
    criterion = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<DescriptiveCriterion {self.parameter_name}: {self.criterion}={self.score}>'


class CSVEvaluationRecord(db.Model):
    __tablename__ = 'csv_evaluation_record'
    id = db.Column(db.Integer, primary_key=True)
    row_data = db.Column(db.JSON)
    total_score = db.Column(db.Float, nullable=False)
    assigned_grade = db.Column(db.String(10), nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    batch_id = db.Column(db.String(50), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_report.id'), nullable=True)
    province = db.Column(db.String(100), nullable=True)  # Added province field

    def __repr__(self):
        return f'<CSVEvaluationRecord grade={self.assigned_grade}, score={self.total_score}>'


class Province(db.Model):
    __tablename__ = 'province'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    population = db.Column(db.Integer, nullable=False)

    targets = db.relationship('ProvinceTarget', backref='province', lazy=True)

    def __repr__(self):
        return f'<Province {self.name}, population={self.population}>'


class ProvinceTarget(db.Model):
    __tablename__ = 'province_target'
    id = db.Column(db.Integer, primary_key=True)
    province_id = db.Column(db.Integer, db.ForeignKey('province.id'), nullable=False)
    liter_capacity = db.Column(db.Float, nullable=True)
    shrink_capacity = db.Column(db.Float, nullable=True)
    liter_percentage = db.Column(db.Float, nullable=True)
    shrink_percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ProvinceTarget for {self.province.name if self.province else "Unknown"}>'