from flask import Flask, render_template,request,redirect,session,flash
from blockchain import blockchain
from datetime import datetime
from database import create_tables
import sqlite3
from werkzeug.utils import secure_filename
import csv
import os


app=Flask(__name__)
app.secret_key="secret123"
blockchain=blockchain()


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

# This makes 'election_phase' available in every HTML file automatically
@app.context_processor
def inject_status():
    try:
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT phase FROM election_settings")
        res = cursor.fetchone()
        conn.close()
        return dict(election_phase=res[0] if res else "Setup")
    except:
        return dict(election_phase="Setup")
    
@app.context_processor
def inject_user_details():
    voter_id = session.get('voter')
    user_name = None
    if voter_id:
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM voters WHERE voter_id=?", (voter_id,))
        res = cursor.fetchone()
        user_name = res[0] if res else None
        conn.close()
    return dict(current_user_name=user_name, current_voter_id=voter_id)

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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        aadhar = request.form['aadhar']
        dob = request.form['dob']
        new_password = request.form['new_password']

        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        
        # Check if Voter ID, Aadhaar, and DOB match
        cursor.execute("SELECT * FROM voters WHERE voter_id=? AND aadhar=? AND dob=?", (voter_id, aadhar, dob))
        voter = cursor.fetchone()

        if voter:
            # If match found, update the password
            cursor.execute("UPDATE voters SET password=? WHERE voter_id=?", (new_password, voter_id))
            conn.commit()
            conn.close()
            return render_template('voter_login.html', alert_msg="Password reset successful! Please login.")
        else:
            conn.close()
            return render_template('forgot_password.html', alert_msg="Identity verification failed! Details do not match.")

    return render_template('forgot_password.html')

@app.route('/voter_login', methods=['GET','POST'])
def voter_login():
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()
    cursor.execute("SELECT phase FROM election_settings")
    result= cursor.fetchone()
    phase = result[0] if result else "Setup"
    conn.close()
    if request.method == 'POST':
        voter_id = request.form['voter_id']
        password = request.form['password']        
        conn = sqlite3.connect("evoting.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM voters WHERE voter_id=?", (voter_id,))
        result = cursor.fetchone()        
        conn.close()
        if not result:
            return render_template('voter_login.html', alert_msg="Voter ID not found!", next_url="/")
        if result[0] is None:
            return render_template('voter_login.html', alert_msg="Authorized but not registered. Please register first!", next_url="/register")
        if result[0] == password:
            session['voter'] = voter_id
            return redirect('/vote')
        else:
            return render_template('voter_login.html', alert_msg="Incorrect password!")
        pass
    return render_template('voter_login.html')

    
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if not session.get('voter'):
        return redirect('/voter_login')
    voter_id = session['voter']
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM voters WHERE voter_id=?", (voter_id,))
    voter_record = cursor.fetchone()
    voter_name = voter_record[0] if voter_record else "Voter"
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
        return render_template('vote.html', success=True, candidate=candidate, 
                               voter_name=voter_name, voter_id=voter_id)
    cursor.execute("SELECT candidate_name, candidate_sign FROM candidates")
    candidates = cursor.fetchall()
    conn.close()
    return render_template('vote.html', candidates=candidates, has_voted=has_voted, 
                           voter_name=voter_name, voter_id=voter_id)
   
# Define where to save images
UPLOAD_FOLDER = 'uploads/symbols/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/manage_candidates', methods=['GET', 'POST'])
def manage_candidates():
    if not session.get('admin'):
        return redirect('/admin_login')
    
    conn = sqlite3.connect("evoting.db")
    cursor = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('candidate_name')
        file = request.files.get('candidate_sign')
        
        if name and file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            cursor.execute("INSERT INTO candidates (candidate_name, candidate_sign) VALUES (?, ?)", (name, filename))
            conn.commit()
            flash("Candidate and Sign added!", "success")
        return redirect('/manage_candidates')

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
    session.clear()
    return redirect('/')

if __name__ =='__main__':
    create_tables()
    blockchain.load_chain_from_db()
    app.run(debug=True)