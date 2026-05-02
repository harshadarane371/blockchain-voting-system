from flask import Flask, render_template,request,redirect,session,flash
from blockchain import blockchain
from datetime import datetime
from database import create_tables
import sqlite3
import csv
import os


app=Flask(__name__)
app.secret_key="secret123"
blockchain=blockchain()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_voters', methods=['GET','POST'])
def upload_voters():
    if not session.get('admin'):
        return redirect('/admin_login')
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            return "No file uploaded!"
        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                voter_id = row[0].strip()
                aadhar = row[1].strip()
                dob = row[2].strip()
                cursor.execute(""" INSERT INTO voters (voter_id, aadhar, dob) VALUES (?, ?, ?) ON CONFLICT(voter_id) DO UPDATE SET aadhar=excluded.aadhar, dob=excluded.dob """, (voter_id, aadhar, dob))

        conn.commit()
        conn.close()

        flash("Voters uploaded successfully!", "success")
        return redirect('/upload_voters') 
    return render_template("upload_voters.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        name = request.form['name']
        password = request.form['password']
        aadhar = request.form['aadhar']
        dob = request.form['dob']
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT aadhar, dob, password FROM voters WHERE voter_id=?", (voter_id,))
        voter = cursor.fetchone()
        if not voter:
            conn.close()
            return render_template('register.html', error="You are not an authorized voter!")
        if voter[0] != aadhar or voter[1] != dob:
            print(f"DB Aadhar: '{voter[0]}' | Form Aadhar: '{aadhar}'") # ADD THIS
            print(f"DB DOB: '{voter[1]}' | Form DOB: '{dob}'")
            conn.close()
            return render_template('register.html', error="Verification failed! Check Aadhaar or DOB.")
        if voter[2] is not None:
            conn.close()
            return render_template('register.html', error="Already registered! Please login.")
        cursor.execute(""" UPDATE voters SET name=?, password=? WHERE voter_id=? """, (name, password, voter_id))
        conn.commit()
        conn.close()
        flash("Voters registered successfully!", "success")
        return redirect('/register') 
    return render_template('register.html')

    
@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username=? AND password=?", (username, password))
        admin =cursor.fetchone()
        conn.close()
        if admin:
            session['admin']=True
            return redirect('/admin_dashboard')
        else:
            return render_template('admin_login.html', error="Invalid credentials !")
    return render_template('admin_login.html')

@app.route('/voter_login', methods=['GET','POST'])
def voter_login():
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        password = request.form['password']
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM voters WHERE voter_id=? AND password=?", (voter_id, password))
        voter = cursor.fetchone()
        conn.close()
        if voter:
            session['voter'] = voter_id
            return redirect('/vote')
        else:
            return render_template('voter_login.html', error="Invalid credentials!")

    return render_template('voter_login.html')


@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if not session.get('voter'):
        return redirect('/voter_login')
    voter_id = session['voter']
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()
    cursor.execute("SELECT phase, start_time, end_time FROM election_settings")
    settings = cursor.fetchone()
    phase, start_t, end_t = settings if settings else ("Setup", "", "")    
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M")
    if phase != "Active":
        conn.close()
        flash(f"Voting is currently disabled (Phase: {phase}).", "danger")
        return redirect('/')
    if start_t and current_time < start_t:
        conn.close()
        flash(f"Voting starts at {start_t.replace('T', ' ')}", "warning")
        return redirect('/')
    if end_t and current_time > end_t:
        conn.close()
        flash("The election has ended.", "danger")
        return redirect('/')
    cursor.execute("SELECT has_voted FROM voters WHERE voter_id=?", (voter_id,))
    voter_record = cursor.fetchone()
    has_voted = voter_record[0] if voter_record else 0
    if request.method == 'POST':
        if has_voted == 1 or blockchain.is_voter_voted(voter_id):
            conn.close()
            flash("You have already cast your vote!", "warning")
            return redirect('/vote')
        candidate = request.form.get('candidate')
        blockchain.add_block({"voter_id": voter_id, "candidate": candidate})
        cursor.execute("UPDATE voters SET has_voted=1 WHERE voter_id=?", (voter_id,))
        conn.commit()
        conn.close()
        return render_template('vote.html', success=True, candidate=candidate)
    cursor.execute("SELECT candidate_name FROM candidates")
    candidates = [row[0] for row in cursor.fetchall()]
    conn.close()    
    return render_template('vote.html', candidates=candidates, has_voted=has_voted)


@app.route('/manage_candidates', methods=['GET', 'POST'])
def manage_candidates():
    if not session.get('admin'):
        return redirect('/admin_login')
    
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        new_candidate = request.form.get('candidate_name')
        if new_candidate:
            cursor.execute("INSERT INTO candidates (candidate_name) VALUES (?)", (new_candidate,))
            conn.commit()
            flash(f"Candidate '{new_candidate}' added successfully!", "success")
        return redirect('/manage_candidates')

    # Fetch all candidates to display in a list
    cursor.execute("SELECT * FROM candidates")
    candidates = cursor.fetchall()
    conn.close()
    return render_template('manage_candidates.html', candidates=candidates)

@app.route('/delete_candidate/<int:id>')
def delete_candidate(id):
    if not session.get('admin'):
        return redirect('/admin_login')
    
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates WHERE candidate_id=?", (id,))
    conn.commit()
    conn.close()
    flash("Candidate removed successfully!", "danger")
    return redirect('/manage_candidates')

@app.route('/analytics')
def analytics():
    if not session.get('admin'):
        return redirect('/admin_login')
    
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()
    
    # 1. Get Total Voters vs Total Votes cast
    cursor.execute("SELECT COUNT(*) FROM voters")
    total_voters = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM voters WHERE has_voted=1")
    voted_count = cursor.fetchone()[0]
    
    # 2. Get Blockchain Vote Distribution
    results = blockchain.count_votes() # {'Candidate A': 5, 'Candidate B': 3}
    labels = list(results.keys())
    values = list(results.values())
    
    conn.close()
    return render_template('analytics.html', 
                           total_voters=total_voters, 
                           voted_count=voted_count, 
                           labels=labels, 
                           values=values)


@app.route('/manage_election', methods=['GET', 'POST'])
def manage_election():
    if not session.get('admin'): 
        return redirect('/admin_login')
    
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        phase = request.form.get('phase')
        start = request.form.get('start_time')
        end = request.form.get('end_time')
        cursor.execute("UPDATE election_settings SET phase=?, start_time=?, end_time=?", (phase, start, end))
        conn.commit()
        flash(f"Election updated to {phase} phase!", "success")
    cursor.execute("SELECT phase, start_time, end_time FROM election_settings")
    settings = cursor.fetchone()
    conn.close()
    return render_template('manage_election.html', settings=settings)


@app.route('/results')
def results():
    results=blockchain.count_votes()
    return render_template('results.html', results=results)

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin_login')
    return render_template('admin_dashboard.html')

@app.route('/validate')
def validate():
    is_valid, messages = blockchain.validate_chain()
    return render_template("validate.html", valid=is_valid, messages=messages, chain=blockchain.chain)

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/voter_logout')
def voter_logout():
    session.pop('voter', None)
    return redirect('/')

if __name__ =='__main__':
    create_tables()
    blockchain.load_chain_from_db()
    app.run(debug=True)