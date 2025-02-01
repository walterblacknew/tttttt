# models.py
from extentions import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'user'  # optional table name
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='marketer')
    email = db.Column(db.String(120), unique=True, nullable=True)
    fullname = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship to assigned routes
    assigned_routes = db.relationship('RouteAssignment', backref='marketer', lazy=True)

    def __repr__(self):
        return f'<User {self.username}, role={self.role}>'


class Route(db.Model):
    __tablename__ = 'route'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RoutePoint {self.name} ({self.latitude},{self.longitude})>'


class RouteAssignment(db.Model):
    __tablename__ = 'route_assignment'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    marketer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
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

    def __repr__(self):
        return f'<Store {self.name} lat={self.lat} lng={self.lng}>'


class EvaluationParameter(db.Model):
    __tablename__ = 'evaluation_parameter'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
