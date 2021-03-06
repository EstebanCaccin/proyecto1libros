import os, json, requests

from flask import Flask, session, request, render_template, redirect, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Configurar la sesión para usar el sistema de archivos
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configurar base de datos
engine = create_engine(Aqui tienes que escribir tu URL de tu base de datos ya sea en tu localhost(tu propia computadora) o ya sea en heroku como en mi caso tu URI )
db = scoped_session(sessionmaker(bind=engine))



@app.route("/")
def index():
	return render_template("registration.html")

@app.route("/temp")
def temp():
	return render_template("search.html")

#login page
@app.route("/login", methods=["GET", "POST"])
def login():

	session.clear()

	#si el método es post (enviando el formulario)
	if request.method =="POST":
		lu = request.form.get("login-username")
		lp = request.form.get("login-password")

		#si el campo de nombre de usuario está vacío
		if not lu:
			return render_template("error.html", message="¡Ingrese su usuario!")

		#si el campo de contraseña está vacío
		if not lp:
			return render_template("error.html", message="¡Ingrese su contraseña!")

		

		#Consulta db para nombre de usuario
		rows = db.execute("SELECT * FROM users WHERE username = :a", {"a": lu})
		result = rows.fetchone()

		if result:
			if result.username == lu and result.password == lp:
				session["username"] = lu
				return redirect("temp")

		return render_template("error.html", message="Usuario / Contraseña incorrecta")


	else:
		return render_template("login.html")

#logout page
@app.route("/logout")
def logout():
	session.clear()

	#redirect user to the login page
	return redirect("/login")

#registration page
@app.route("/registration", methods=["GET", "POST"])
def registration():

	session.clear()

	#si el usuario envía el formulario (a través de POST)
	if request.method == "POST":
		u = request.form.get("username")
		p = request.form.get("password")

		#Asegúrese de que se envió el nombre de usuario

		if not u:
			return render_template("error.html", message="Por favor ingrese un nombre de usuario válido")

		
                #Consulta databse para nombre de usuario
		userCheck = db.execute("SELECT username from users").fetchall()

		#Comprobar si el nombre de usuario ya existe
		for i in range(len(userCheck)):
			if userCheck[i]["username"] == u:
				return render_template("error.html", message="Usuario ya existente!")

		#Comprobar si se proporciona la contraseña
		if not p:
			return render_template("error.html", message="¡DEBE proporcionar contraseña!")

		
                #asegúrese de que la contraseña tenga seis caracteres
		if len(p) < 6:
			return render_template("error.html", message="Las contraseñas DEBEN tener seis caracteres")

		
                #asegúrese de que se envió la confirmación
		if not request.form.get("confirmation"):
			return render_template("error.html", message="¡DEBE confirmar la contraseña!")

		#asegúrese de que las contraseñas proporcionadas sean las mismas
		if not request.form.get("password") == request.form.get("confirmation"):
			return render_template("error.html", message="¡La contraseña no es la misma!")

		#insertar usuario en la base de datos
		db.execute("INSERT into users (username, password) values (:username, :password)",
			{"username":request.form.get("username"), "password":request.form.get("password")})

		session["username"] = u
		#cambios a la base de datos
		db.commit()



		#redirigir a la página de inicio de sesión
		return render_template("login.html")

	#si el usuario alcanzó la ruta a través de GET
	else:
		return render_template("registration.html")



@app.route("/search", methods=["GET"])
def search():
	if request.method == "GET":
		u = session["username"]
		if not u:
			return render_template("error.html", message="¡Necesitas iniciar sesión!")
		sb = request.args.get("text")
		if not sb:
			return render_template("error.html", message="Proporcione el nombre del libro.")

		#para usar la palabra clave 'LIKE'
		query = ("%" + sb + "%").title()

		#selecciona todos los libros que tengan un nombre similar al ingresado
		rows = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query LIMIT 15",{"query": query})
		
                #comprobar si el libro existe
		if rows.rowcount==0:
			return render_template("error.html", message="¡No existe ningún libro!")

		#buscar todos los resultados
		books = rows.fetchall()
		return render_template("results.html", books=books,sb=sb)

@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):
	username = session['username']
	session["reviews"] = []

	rows_rev = db.execute("SELECT * from reviews WHERE isbn=:isbn AND username=:username", {"isbn":isbn, "username":username}).fetchall()
	if not rows_rev and request.method == "POST":

		review = request.form.get("comment")
		rating = request.form.get("rating")

		db.execute("INSERT into reviews (isbn,review, rating, username) Values (:isbn, :review, :rating,:username)",{"isbn": isbn, "review": review, "rating":rating, "username":username})
		db.commit()

	if rows_rev and request.method == "POST":
		return render_template("error.html", message="Ya ha enviado una reseña")

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "XjytnMTBuDsGMM2lWu33w", "isbns": isbn})
	res = res.json()
	avg_rating= res['books'][0]['average_rating']
	rate_count = res['books'][0]['work_ratings_count']
	reviews = db.execute("SELECT * from reviews WHERE isbn=:isbn", {"isbn" :isbn}).fetchall()

	for y in reviews:
		session["reviews"].append(y)


	data = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn": isbn})
	data = data.fetchone()
	return render_template("info.html", data=data,avg_rating=avg_rating, rate_count=rate_count,reviews=session["reviews"],username=username)

@app.route("/api/<isbn>",methods=["GET"])
def api(isbn):
	data = db.execute("SELECT * from books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
	if not data:
		return jsonify({"Error": "Invalid ISBN"}),422
	result = dict(data.items())
	return jsonify(result)
