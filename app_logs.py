#!/usr/bin/env python3
import psycopg2
import io
from flask import Flask, render_template_string, send_file, render_template

app = Flask(__name__)

# Adjust these to point to the same DB as your main app
DB_CONFIG = {
    'dbname': 'sleep-posture-dashboard',
    'user': 'postgres',
    'password': 'shishir',
    'host': 'localhost',
    'port': '5432'
}

# HTML template using Flask's render_template_string for convenience
LOGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Audit Logs Viewer</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
      body { padding: 20px; background-color: #f8f9fa; }
      h1 { margin-bottom: 20px; }
      table { background-color: #fff; border-radius: 5px; }
      th, td { font-size: 0.9rem; }
      .container { max-width: 1000px; margin: 0 auto; }
    </style>
</head>
<body>
<div class="container">
    <h1>Audit Logs</h1>
    <a href="/download" class="btn btn-primary mb-3">Download as .txt</a>
    
    <table class="table table-bordered table-striped">
      <thead class="table-dark">
        <tr>
          <th>ID</th>
          <th>User ID</th>
          <th>Action</th>
          <th>Resource Type</th>
          <th>Resource ID</th>
          <th>Detail</th>
          <th>Event Time</th>
        </tr>
      </thead>
      <tbody>
      {% for log in logs %}
        <tr>
          <td>{{ log.id }}</td>
          <td>{{ log.user_id }}</td>
          <td>{{ log.action }}</td>
          <td>{{ log.resource_type }}</td>
          <td>{{ log.resource_id }}</td>
          <td>{{ log.detail }}</td>
          <td>{{ log.event_time }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
</div>
</body>
</html>
"""

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route("/")
def show_logs():
    """Display the logs in a table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, action, resource_type, resource_id, detail, event_time FROM audit_logs ORDER BY event_time DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    logs = []
    for row in rows:
        logs.append({
            'id': row[0],
            'user_id': row[1],
            'action': row[2],
            'resource_type': row[3],
            'resource_id': row[4],
            'detail': row[5],
            'event_time': row[6]
        })

    return render_template('logs.html', logs=logs)


@app.route("/download")
def download_txt():
    """Download logs as a .txt file."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, action, resource_type, resource_id, detail, event_time FROM audit_logs ORDER BY event_time DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Create an in-memory text buffer
    output = io.StringIO()
    output.write("ID | USER_ID | ACTION | RESOURCE_TYPE | RESOURCE_ID | DETAIL | EVENT_TIME\n")
    output.write("-------------------------------------------------------------------------------\n")

    for row in rows:
        row_text = f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5] or ''} | {row[6]}\n"
        output.write(row_text)

    output.seek(0)  # reset cursor to the beginning

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype="text/plain",
        as_attachment=True,
        attachment_filename="audit_logs.txt"
    )

if __name__ == "__main__":
    # Run on a different port so it won't collide with your main app
    app.run(debug=True, port=5001)
