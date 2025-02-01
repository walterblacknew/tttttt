# forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, 
    SelectField, SelectMultipleField, TextAreaField, FloatField, 
    IntegerField, DateField
)
from wtforms.validators import DataRequired, Length, Optional, Email, NumberRange

class LoginForm(FlaskForm):
    username = StringField('نام کاربری', validators=[DataRequired()])
    password = PasswordField('رمز عبور', validators=[DataRequired()])
    submit = SubmitField('ورود')


class UserForm(FlaskForm):
    username = StringField('نام کاربری', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('رمز عبور', validators=[DataRequired(), Length(min=4, max=50)])
    email = StringField('ایمیل', validators=[Optional(), Email(), Length(max=120)])
    fullname = StringField('نام و نام خانوادگی', validators=[Optional(), Length(max=120)])
    is_active = BooleanField('فعال')
    role = SelectField('نقش کاربر', choices=[
        ('admin', 'مدیر'),
        ('marketer', 'بازاریاب'),
        ('observer', 'ناظر')
    ])
    submit = SubmitField('ذخیره')


class RouteForm(FlaskForm):
    name = StringField('نام مسیر', validators=[DataRequired()])
    description = TextAreaField('توضیحات', validators=[Optional()])
    marketer_ids = SelectMultipleField('بازاریاب‌ها', coerce=int)
    submit = SubmitField('ذخیره مسیر')


class RoutePointForm(FlaskForm):
    name = StringField('نام نقطه', validators=[DataRequired()])
    latitude = FloatField('عرض جغرافیایی', validators=[
        DataRequired(),
        NumberRange(min=-90, max=90)
    ])
    longitude = FloatField('طول جغرافیایی', validators=[
        DataRequired(),
        NumberRange(min=-180, max=180)
    ])
    address = TextAreaField('آدرس', validators=[Optional()])
    order = IntegerField('ترتیب', validators=[DataRequired()])
    submit = SubmitField('افزودن نقطه')


class StoreForm(FlaskForm):
    name = StringField('نام فروشگاه', validators=[DataRequired(), Length(max=150)])
    lat = FloatField('عرض جغرافیایی', validators=[Optional()])
    lng = FloatField('طول جغرافیایی', validators=[Optional()])
    submit = SubmitField('ایجاد فروشگاه')


class EvaluationParameterForm(FlaskForm):
    name = StringField('نام پارامتر', validators=[DataRequired(), Length(max=150)])
    weight = FloatField('وزن', validators=[Optional()])
    submit = SubmitField('ذخیره')


class StoreEvaluationForm(FlaskForm):
    store_id = SelectField('فروشگاه', coerce=int, validators=[DataRequired()])
    start_date = DateField('تاریخ شروع', validators=[Optional()])
    end_date = DateField('تاریخ پایان', validators=[Optional()])
    submit = SubmitField('ایجاد ارزیابی')


class QuotaCategoryForm(FlaskForm):
    category = StringField('دسته‌بندی', validators=[DataRequired(), Length(max=50)])
    monthly_quota = IntegerField('سهمیه ماهانه', validators=[DataRequired()])
    submit = SubmitField('ذخیره سهمیه')
