import bcrypt
from flask import Flask, request, jsonify, render_template, session, Response
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from db_school.db import role_privileges
import json

app = Flask(__name__)
app.secret_key = 'clé_secrete_unique'  # Clé secrète pour sécuriser les sessions

# Fonction pour établir une connexion à la base de données
def get_db_connection():
    conn = sqlite3.connect('db_school.db')
    conn.row_factory = sqlite3.Row
    return conn

# Route pour enregistrer un utilisateur
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Format JSON invalide ou vide'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not all([username, email, password, role]):
        return jsonify({'message': 'Données utilisateur manquantes'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
    existing_user = cursor.fetchone()

    if existing_user:
        return jsonify({'message': 'Username ou email déjà existant'}), 400

    hashed_password = generate_password_hash(password)
    cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                   (username, email, hashed_password, role))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Utilisateur enregistré avec succès'}), 201

# Vérification des privilèges
def check_privilege(required_privilege):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session:
                return jsonify({'message': 'Utilisateur non connecté'}), 401

            user_role = session['user_role']
            if required_privilege not in role_privileges.get(user_role, []):
                return jsonify({'message': 'Accès non autorisé'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Route de connexion
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Format JSON invalide ou vide'}), 400

    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'message': 'Nom d’utilisateur invalide'}), 404

    if check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        return jsonify({'message': 'Connexion réussie', 'username': username, 'role': user['role']}), 200
    else:
        return jsonify({'message': 'Mot de passe incorrect'}), 401

# Route pour consulter les cours (étudiants et enseignants)
@app.route('/courses', methods=['GET'])
@check_privilege('view_courses')
def view_courses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()
    conn.close()
    return jsonify([dict(course) for course in courses]), 200

# Route pour consulter les notes (étudiants)
@app.route('/notes', methods=['GET'])
@check_privilege('view_notes')
def view_notes():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE student_id = ?", (user_id,))
    notes = cursor.fetchall()
    conn.close()
    return jsonify([dict(note) for note in notes]), 200

# Route pour créer un cours (enseignants)
@app.route('/courses', methods=['POST'])
@check_privilege('edit_courses')
def create_course():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Format JSON invalide ou vide'}), 400

    title = data.get('title')
    description = data.get('description')
    teacher_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO courses (title, description, teacher_id) VALUES (?, ?, ?)",
                   (title, description, teacher_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Cours créé avec succès'}), 201

# Route pour ajouter une note (enseignants)
@app.route('/notes', methods=['POST'])
@check_privilege('edit_notes')
def add_note():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Format JSON invalide ou vide'}), 400

    student_id = data.get('student_id')
    course_id = data.get('course_id')
    grade = data.get('grade')
    comments = data.get('comments', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notes (student_id, course_id, grade, comments) VALUES (?, ?, ?, ?)",
                   (student_id, course_id, grade, comments))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Note ajoutée avec succès'}), 201

# Route pour gérer les utilisateurs (direction)
@app.route('/users', methods=['GET', 'POST', 'PUT', 'DELETE'])
@check_privilege('edit_users')
def manage_users():
    data = request.get_json() if request.method in ['POST', 'PUT', 'DELETE'] else None

    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users")
        users = cursor.fetchall()
        conn.close()
        return jsonify([dict(user) for user in users]), 200

    elif request.method == 'POST':
        if not data:
            return jsonify({'message': 'Format JSON invalide ou vide'}), 400

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')

        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                       (username, email, hashed_password, role))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Utilisateur créé avec succès'}), 201

    elif request.method == 'PUT':
        if not data:
            return jsonify({'message': 'Format JSON invalide ou vide'}), 400

        user_id = data.get('id')
        username = data.get('username')
        email = data.get('email')
        role = data.get('role')

        conn = get_db_connection()
        cursor = conn.cursor()

        update_fields = []
        update_values = []
        if username:
            update_fields.append("username = ?")
            update_values.append(username)
        if email:
            update_fields.append("email = ?")
            update_values.append(email)
        if role:
            update_fields.append("role = ?")
            update_values.append(role)

        if update_fields:
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)
            cursor.execute(query, tuple(update_values))
            conn.commit()
        conn.close()
        return jsonify({'message': 'Utilisateur mis à jour avec succès'}), 200

    elif request.method == 'DELETE':
        if not data:
            return jsonify({'message': 'Format JSON invalide ou vide'}), 400

        user_id = data.get('id')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Utilisateur supprimé avec succès'}), 200

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return jsonify({'message': 'Déconnexion réussie'}), 200

if __name__ == '__main__':
    app.run(debug=True)
