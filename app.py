from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from forms import EventForm, ResourceForm, AllocationForm, UtilizationReportForm
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'


# LOGIN REQUIRED DECORATOR
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated



# DATABASE CONNECTION
def get_db():
    return pymysql.connect(
        host="localhost",
        port=3305,
        user="root",
        password="agnees2004@",
        database="event",
        cursorclass=pymysql.cursors.DictCursor
    )


# AUTH:SIGNUP

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

       
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("signup"))

        conn = get_db()
        cur = conn.cursor()

        try:
            hashed = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                        (username, email, hashed))
            conn.commit()

            flash("Account created successfully!", "success")
            return redirect(url_for("login"))
        
        except:
            flash("Email already exists!", "danger")

        finally:
            conn.close()

    return render_template("signup.html")

# AUTH: LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            return redirect(url_for("index"))
        else:
            flash("Invalid Email or Password!", "danger")

    return render_template("login.html")


# AUTH: LOGOUT

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# CHECK RESOURCE CONFLICT

def check_resource_conflict(resource_id, start_time, end_time, exclude_event_id=None):
    conn = get_db()
    cur = conn.cursor()

    sql = """
        SELECT e.* FROM event_resource_allocations a
        JOIN events e ON a.event_id = e.event_id
        WHERE a.resource_id=%s
    """

    cur.execute(sql, (resource_id,))
    allocations = cur.fetchall()

    for event in allocations:
        if exclude_event_id and event["event_id"] == exclude_event_id:
            continue
        if start_time < event["end_time"] and end_time > event["start_time"]:
            return True, event

    conn.close()
    return False, None



# HOME PAGE

@app.route('/')
@login_required
def index():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM events ORDER BY start_time DESC LIMIT 5")
    events = cur.fetchall()

    cur.execute("SELECT COUNT(*) as total FROM resources")
    resource_count = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM events")
    event_count = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM event_resource_allocations")
    allocation_count = cur.fetchone()["total"]

    cur.execute("""
        SELECT 
            a.event_id,
            r.resource_name
        FROM event_resource_allocations a
        JOIN resources r ON a.resource_id = r.resource_id
    """)
    allocations = cur.fetchall()

    conn.close()

    resources_by_event = {}
    for row in allocations:
        eid = row["event_id"]
        if eid not in resources_by_event:
            resources_by_event[eid] = []
        resources_by_event[eid].append(row["resource_name"])

    final_events = []
    for e in events:
        final_events.append({
            **e,
            "resources": resources_by_event.get(e["event_id"], [])
        })

    return render_template(
        "index.html",
        events=final_events,
        resource_count=resource_count,
        event_count=event_count,
        allocation_count=allocation_count
    )



# EVENTS LIST
@app.route('/events')
@login_required
def events():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM events ORDER BY start_time DESC")
    events = cur.fetchall()

    for event in events:
        cur.execute("""
            SELECT a.allocation_id, r.resource_id, r.resource_name, r.resource_type
            FROM event_resource_allocations a
            JOIN resources r ON r.resource_id = a.resource_id
            WHERE a.event_id = %s
        """, (event["event_id"],))

        allocations = cur.fetchall()

        event["allocations"] = [
            {
                "allocation_id": alloc["allocation_id"],
                "resource": {
                    "resource_id": alloc["resource_id"],
                    "resource_name": alloc["resource_name"],
                    "resource_type": alloc["resource_type"]
                }
            }
            for alloc in allocations
        ]

    conn.close()
    return render_template('events.html', events=events)



# ADD EVENT
@app.route('/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    form = EventForm()

    if form.validate_on_submit():
        conn = get_db()
        cur = conn.cursor()

        sql = "INSERT INTO events(title, start_time, end_time, description) VALUES (%s, %s, %s, %s)"

        cur.execute(sql, (
            form.title.data,
            form.start_time.data,
            form.end_time.data,
            form.description.data
        ))
        conn.commit()
        conn.close()

        flash("Event created!", "success")
        return redirect(url_for("events"))

    return render_template("event_form.html", form=form, title="Add Event")



# EDIT EVENT
@app.route('/events/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM events WHERE event_id=%s", (event_id,))
    event = cur.fetchone()

    if not event:
        flash("Event not found!", "danger")
        return redirect(url_for("events"))

    form = EventForm(data=event)

    if form.validate_on_submit():
        cur.execute("SELECT resource_id FROM event_resource_allocations WHERE event_id=%s", (event_id,))
        allocated_resources = [row["resource_id"] for row in cur.fetchall()]

        conflicts = []
        for resource_id in allocated_resources:
            has_conflict, conflicting_event = check_resource_conflict(
                resource_id, form.start_time.data, form.end_time.data, event_id
            )
            if has_conflict:
                conflicts.append(
                    f"{resource_id} is allocated to '{conflicting_event['title']}'"
                )

        if conflicts:
            for c in conflicts:
                flash(c, "danger")
        else:
            sql = """
                UPDATE events SET title=%s, start_time=%s, end_time=%s, description=%s
                WHERE event_id=%s
            """
            cur.execute(sql, (
                form.title.data,
                form.start_time.data,
                form.end_time.data,
                form.description.data,
                event_id
            ))
            conn.commit()
            flash("Event updated!", "success")
            conn.close()
            return redirect(url_for("events"))

    conn.close()
    return render_template("event_form.html", form=form, title="Edit Event", event=event)



# DELETE EVENT

@app.route('/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE event_id=%s", (event_id,))
    conn.commit()
    conn.close()

    flash("Event deleted!", "success")
    return redirect(url_for("events"))



# RESOURCES LIST
@app.route('/resources')
@login_required
def resources():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM resources ORDER BY resource_id DESC")
    resources = cur.fetchall()

    cur.execute("""
        SELECT resource_id, COUNT(*) AS allocation_count
        FROM event_resource_allocations
        GROUP BY resource_id
    """)
    allocation_data = cur.fetchall()

    conn.close()

    allocation_map = {row["resource_id"]: row["allocation_count"] for row in allocation_data}

    final_resources = []
    for r in resources:
        final_resources.append({
            "resource_id": r["resource_id"],
            "resource_name": r["resource_name"],
            "resource_type": r["resource_type"],
            "allocation_count": allocation_map.get(r["resource_id"], 0)
        })

    return render_template("resources.html", resources=final_resources)

# ADD RESOURCE

@app.route('/resources/add', methods=['GET', 'POST'])
@login_required
def add_resource():
    form = ResourceForm()

    if form.validate_on_submit():
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO resources(resource_name, resource_type) VALUES(%s, %s)",
            (form.resource_name.data, form.resource_type.data)
        )

        conn.commit()
        conn.close()

        flash("Resource added!", "success")
        return redirect(url_for("resources"))

    return render_template("resource_form.html", form=form, title="Add Resource")


# EDIT RESOURCE

@app.route('/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
@login_required
def edit_resource(resource_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM resources WHERE resource_id=%s", (resource_id,))
    resource = cur.fetchone()

    if not resource:
        flash("Resource not found!", "danger")
        conn.close()
        return redirect(url_for("resources"))

    form = ResourceForm(data=resource)

    if form.validate_on_submit():
        sql = """
            UPDATE resources
            SET resource_name=%s, resource_type=%s
            WHERE resource_id=%s
        """
        cur.execute(sql, (
            form.resource_name.data,
            form.resource_type.data,
            resource_id
        ))
        conn.commit()
        conn.close()

        flash("Resource updated successfully!", "success")
        return redirect(url_for("resources"))

    conn.close()
    return render_template("resource_form.html", form=form, title="Edit Resource", resource=resource)


# DELETE RESOURCE

@app.route('/resources/delete/<int:resource_id>', methods=['POST'])
@login_required
def delete_resource(resource_id):
    conn = get_db()
    cur = conn.cursor()

    # Check if resource is allocated
    cur.execute(
        "SELECT COUNT(*) AS total FROM event_resource_allocations WHERE resource_id = %s",
        (resource_id,)
    )
    row = cur.fetchone()
    allocated_count = row["total"]  

    if allocated_count > 0:
        conn.close()
        flash("Cannot delete this resource because it is allocated to an event!", "danger")
        return redirect(url_for("resources"))

    cur.execute("DELETE FROM resources WHERE resource_id = %s", (resource_id,))
    conn.commit()
    conn.close()

    flash("Resource deleted successfully!", "success")
    return redirect(url_for("resources"))


# ALLOCATIONS LIST

@app.route('/allocations')
@login_required
def allocations():
    conn = get_db()
    cur = conn.cursor()

    sql = """
        SELECT 
            a.allocation_id,
            e.title AS event_title,
            e.start_time,
            e.end_time,
            r.resource_name,
            r.resource_type
        FROM event_resource_allocations a
        JOIN events e ON a.event_id = e.event_id
        JOIN resources r ON a.resource_id = r.resource_id
        ORDER BY a.allocation_id DESC
    """

    cur.execute(sql)
    data = cur.fetchall()
    conn.close()

    allocations = []
    for row in data:
        allocations.append({
            "allocation_id": row["allocation_id"],
            "event_title": row["event_title"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "resource_name": row["resource_name"],
            "resource_type": row["resource_type"]
        })

    return render_template("allocations.html", allocations=allocations)


# ADD ALLOCATION

@app.route('/allocations/add', methods=['GET', 'POST'])
@login_required
def add_allocation():
    conn = get_db()
    cur = conn.cursor()

    form = AllocationForm()

    cur.execute("SELECT event_id, title, start_time, end_time FROM events")
    events = cur.fetchall()
    form.event_id.choices = [
        (e["event_id"], f"{e['title']} ({e['start_time']} - {e['end_time']})")
        for e in events
    ]

    cur.execute("SELECT resource_id, resource_name, resource_type FROM resources")
    resources = cur.fetchall()
    form.resource_ids.choices = [
        (r["resource_id"], f"{r['resource_name']} ({r['resource_type']})")
        for r in resources
    ]

    if form.validate_on_submit():
        event_id = form.event_id.data

        cur.execute("SELECT * FROM events WHERE event_id=%s", (event_id,))
        event = cur.fetchone()

        conflicts = []

        for resource_id in form.resource_ids.data:

            sql = """
                SELECT e.* FROM event_resource_allocations a
                JOIN events e ON a.event_id = e.event_id
                WHERE a.resource_id = %s
                  AND e.start_time < %s
                  AND e.end_time > %s
            """
            cur.execute(sql, (resource_id, event["end_time"], event["start_time"]))
            conflict_event = cur.fetchone()

            if conflict_event:
                conflicts.append(
                    f"Resource already allocated to '{conflict_event['title']}' "
                    f"({conflict_event['start_time']} - {conflict_event['end_time']})"
                )

        if conflicts:
            for c in conflicts:
                flash(c, "danger")
            return redirect(url_for("add_allocation"))

        for resource_id in form.resource_ids.data:
            cur.execute(
                "INSERT INTO event_resource_allocations (event_id, resource_id) VALUES (%s, %s)",
                (event_id, resource_id)
            )

        conn.commit()
        conn.close()

        flash("Resources allocated successfully!", "success")
        return redirect(url_for("allocations"))

    conn.close()
    return render_template("allocation_form.html", form=form, title="Allocate Resources")



# DELETE ALLOCATION

@app.route('/allocations/delete/<int:allocation_id>', methods=['POST'])
@login_required
def delete_allocation(allocation_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM event_resource_allocations WHERE allocation_id=%s", (allocation_id,))
    conn.commit()
    conn.close()

    flash("Allocation removed successfully!", "success")
    return redirect(url_for("allocations"))



# UTILIZATION REPORT

@app.route('/reports/utilization', methods=['GET', 'POST'])
@login_required
def utilization_report():
    form = UtilizationReportForm()
    report_data = []

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'GET':
        form.start_date.data = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        form.end_date.data = (datetime.now() + timedelta(days=30)).replace(hour=23, minute=59, second=59, microsecond=0)

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data

        cur.execute("SELECT * FROM resources ORDER BY resource_name")
        resources = cur.fetchall()

        for resource in resources:

            sql_overlap = """
                SELECT e.event_id, e.title, e.start_time, e.end_time
                FROM event_resource_allocations a
                JOIN events e ON a.event_id = e.event_id
                WHERE a.resource_id = %s
                  AND e.start_time < %s
                  AND e.end_time > %s
            """
            cur.execute(sql_overlap, (resource["resource_id"], end_date, start_date))
            overlapping = cur.fetchall()

            total_hours = 0
            for ev in overlapping:
                overlap_start = max(ev["start_time"], start_date)
                overlap_end = min(ev["end_time"], end_date)
                if overlap_start < overlap_end:
                    hours = (overlap_end - overlap_start).total_seconds() / 3600
                    total_hours += hours

            sql_upcoming = """
                SELECT e.event_id, e.title, e.start_time, e.end_time
                FROM event_resource_allocations a
                JOIN events e ON a.event_id = e.event_id
                WHERE a.resource_id = %s
                  AND e.start_time >= NOW()
                ORDER BY e.start_time
                LIMIT 5
            """
            cur.execute(sql_upcoming, (resource["resource_id"],))
            upcoming = cur.fetchall()

            report_data.append({
                "resource": resource,
                "total_hours": round(total_hours, 2),
                "upcoming_bookings": upcoming
            })

    conn.close()
    return render_template("utilization_report.html", form=form, report_data=report_data)



# RUN APP
if __name__ == '__main__':
    app.run(debug=True)
