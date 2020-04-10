from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class ExamForm(FlaskForm):
    user_answers = StringField('user_answers', validators=[DataRequired()])
