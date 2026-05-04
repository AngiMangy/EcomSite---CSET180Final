# import flask. If you don't have flask installed,
# hover your mouse over the yellow line in import statement
from flask import Flask, render_template, request
from sqlalchemy import create_engine, text

# Flask uses this argument to determine the root path of
# the application so that it later can find resource files
# relative to the location of the application.
app = Flask(__name__)

conn_str = "mysql://root:cset155@localhost/boatdb"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()


# Defining routes. We are telling Flask what to do when
# a request is made at '/' route. In this case, it is
# localhost:5000/

@app.route('/')

@app.route('/boats')
def boats():
    boats = conn.execute(text("select * from boats")).all()
    print(boats)
    return render_template('boats.html', boats= boats[:10])

@app.route('/boat_create' , methods = ["GET"])
def boat_create():
    return render_template('boat_create.html')

@app.route('/boat_create' , methods = ["POST"])
def boat_create_post():
    conn.execute(text("insert into boats values (:id, :name, :type, :owner_id,:rental_price)"), request.form)
    conn.commit()
    return render_template('boat_create.html') 

@app.route('/boat_delete' , methods = ["GET"])
def boat_delete():
    return render_template('delete.html')

@app.route('/boat_delete' , methods = ["POST"])
def boat_delete_post():
    conn.execute(text("delete from boats where id = :id"), request.form)
    conn.commit()
    return render_template('delete.html') 

@app.route('/boats_edit', methods = ['GET'])
def boats_edit():
    return render_template('edit.html')

@app.route('/boats_edit', methods = ['POST'])
def boats_edit_post():
    conn.execute(text("update boats set name = :name,"
    "type = :type, rental_price = :rental_price where id = :id "), request.form)
    conn.commit()
    return render_template('edit.html')



@app.route('/base')
def base():
    return render_template('base.html')
    

if __name__ == '__main__':  # When this file is run...
    # ... start the app in debug mode. In debug mode,
    # server is automatically restarted when you make changes to the code
    app.run(debug=True)