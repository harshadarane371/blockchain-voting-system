from flask import Flask, render_template,request,redirect,session
from blockchain import blockchain

app=Flask(__name__)
app.secret_key="secret123"
blockchain=blockchain()
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        if username=="admin" and password=="admin123":
            session['admin']=True
            return redirect('/admin_dashboard')
        else:
            return render_template('admin_login.html', error="Invalid credentials !")
    return render_template('admin_login.html')

@app.route('/vote', methods=['GET','POST'])
def vote():
    if request.method == 'POST':
        voter_id=request.form['voter_id']
        candidate=request.form['candidate']
        print("VOTER:",voter_id)
        print("CANDIDATE :",candidate)

        if blockchain.is_voter_voted(voter_id):
            return "You have already voted !"

        vote_data=f"{voter_id} voted for {candidate}"
        blockchain.add_block(vote_data)
        return "Vote successfully recorded !"
    return render_template('vote.html')
@app.route('/results')
def results():
    vote_results=blockchain.count_votes()
    return render_template('results.html', results=vote_results)

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin_login')
    return render_template('admin_dashboard.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

if __name__ =='__main__':
    app.run(debug=True)