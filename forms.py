from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, SelectField, SelectMultipleField
from wtforms import SelectMultipleField, widgets
from wtforms.validators import DataRequired, ValidationError
from datetime import datetime

class EventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired()])
    start_time = DateTimeLocalField('Start Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeLocalField('End Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    description = TextAreaField('Description')
    
    def validate_end_time(self, field):
        if field.data and self.start_time.data:
            if field.data <= self.start_time.data:
                raise ValidationError('End time must be after start time.')

class ResourceForm(FlaskForm):
    resource_name = StringField('Resource Name', validators=[DataRequired()])
    resource_type = SelectField('Resource Type', choices=[
        ('Room', 'Room'),
        ('Instructor', 'Instructor'),
        ('Equipment', 'Equipment'),
        ('Other', 'Other')
    ], validators=[DataRequired()])

class AllocationForm(FlaskForm):
    event_id = SelectField('Event', coerce=int, validators=[DataRequired()])
    resource_ids = SelectMultipleField(
        'Resources',
        coerce=int,
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
        validators=[DataRequired()]
    )

class UtilizationReportForm(FlaskForm):
    start_date = DateTimeLocalField('Start Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeLocalField('End Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    
    def validate_end_date(self, field):
        if field.data and self.start_date.data:
            if field.data <= self.start_date.data:
                raise ValidationError('End date must be after start date.')
