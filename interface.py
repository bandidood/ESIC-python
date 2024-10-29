# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète'  # À changer en production


# Fonction pour vérifier si l'utilisateur est connecté
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def get_db_connection():
    conn = sqlite3.connect('db_school.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Connexion réussie!', 'success')
            return redirect(url_for('dashboard'))
        flash('Identifiants invalides', 'error')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    conn = get_db_connection()

    # Dans la route dashboard
    if role == 'enseignant':
        courses = conn.execute('''
            SELECT courses.*, 
                COUNT(DISTINCT notes.student_id) as noted_students,
                COUNT(DISTINCT users.id) as total_students
            FROM courses 
            LEFT JOIN notes ON courses.id = notes.course_id
            LEFT JOIN users ON users.role = 'étudiant'
            WHERE courses.teacher_id = ?
            GROUP BY courses.id
        ''', (session['user_id'],)).fetchall()

    if role == 'étudiant':
        # Récupérer les notes de l'étudiant
        notes = conn.execute('''
            SELECT notes.*, courses.title as course_title 
            FROM notes 
            JOIN courses ON notes.course_id = courses.id 
            WHERE student_id = ?
        ''', (session['user_id'],)).fetchall()

        courses = conn.execute('SELECT * FROM courses').fetchall()
        return render_template('student_dashboard.html', notes=notes, courses=courses)

    elif role == 'enseignant':
        # Récupérer les cours de l'enseignant
        courses = conn.execute('SELECT * FROM courses WHERE teacher_id = ?',
                               (session['user_id'],)).fetchall()
        return render_template('teacher_dashboard.html', courses=courses)

    elif role == 'directeur':
        # Récupérer tous les utilisateurs et cours
        users = conn.execute('SELECT * FROM users').fetchall()
        courses = conn.execute('SELECT * FROM courses').fetchall()
        return render_template('admin_dashboard.html', users=users, courses=courses)

    conn.close()
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))


# Décorateur pour vérifier si l'utilisateur est admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'directeur':
            flash('Accès réservé aux administrateurs', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        # Validation des données
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères', 'error')
            return render_template('register.html')

        if role not in ['étudiant', 'enseignant', 'directeur']:
            flash('Rôle invalide', 'error')
            return render_template('register.html')

        try:
            conn = get_db_connection()
            # Vérifier si l'utilisateur existe déjà
            user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                                (username, email)).fetchone()

            if user:
                flash('Nom d\'utilisateur ou email déjà utilisé', 'error')
                return render_template('register.html')

            # Créer le nouvel utilisateur
            hashed_password = generate_password_hash(password)
            conn.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                         (username, email, hashed_password, role))
            conn.commit()
            flash(f'Utilisateur {username} créé avec succès', 'success')
            return redirect(url_for('admin_dashboard'))

        except sqlite3.Error as e:
            flash(f'Erreur lors de la création: {str(e)}', 'error')
            return render_template('register.html')

        finally:
            conn.close()

    return render_template('register.html')


@app.route('/course/<int:course_id>/grades', methods=['GET'])
@login_required
def view_course_grades(course_id):
    conn = get_db_connection()
    role = session.get('role')
    user_id = session.get('user_id')

    # Récupérer les informations du cours
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()

    if not course:
        flash('Cours non trouvé', 'error')
        return redirect(url_for('dashboard'))

    if role == 'étudiant':
        # Les étudiants ne voient que leurs propres notes
        grades = conn.execute('''
            SELECT notes.*, courses.title as course_title
            FROM notes 
            JOIN courses ON notes.course_id = courses.id
            WHERE student_id = ? AND course_id = ?
        ''', (user_id, course_id)).fetchall()

        conn.close()
        return render_template('student_grades.html', grades=grades, course=course)

    elif role == 'enseignant':
        # Vérifier si l'enseignant est responsable de ce cours
        if course['teacher_id'] != user_id and role != 'directeur':
            flash('Vous n\'êtes pas autorisé à voir ces notes', 'error')
            return redirect(url_for('dashboard'))

        # Récupérer tous les étudiants et leurs notes pour ce cours
        students_grades = conn.execute('''
            SELECT users.id as student_id, users.username, notes.grade, notes.comments, notes.id as note_id
            FROM users 
            LEFT JOIN notes ON users.id = notes.student_id AND notes.course_id = ?
            WHERE users.role = 'étudiant'
            ORDER BY users.username
        ''', (course_id,)).fetchall()

        conn.close()
        return render_template('manage_grades.html', students=students_grades, course=course)

    elif role == 'directeur':
        # Les administrateurs voient toutes les notes
        all_grades = conn.execute('''
            SELECT notes.*, users.username as student_name
            FROM notes 
            JOIN users ON notes.student_id = users.id
            WHERE course_id = ?
        ''', (course_id,)).fetchall()

        conn.close()
        return render_template('admin_grades.html', grades=all_grades, course=course)


@app.route('/course/<int:course_id>/grade/<int:student_id>', methods=['POST'])
@login_required
def add_or_update_grade(course_id, student_id):
    if session.get('role') not in ['enseignant', 'directeur']:
        flash('Non autorisé', 'error')
        return redirect(url_for('dashboard'))

    grade = request.form.get('grade')
    comments = request.form.get('comments', '')

    try:
        grade = float(grade)
        if not 0 <= grade <= 20:
            raise ValueError("La note doit être entre 0 et 20")
    except ValueError:
        flash('Note invalide', 'error')
        return redirect(url_for('view_course_grades', course_id=course_id))

    conn = get_db_connection()

    # Vérifier si une note existe déjà
    existing_grade = conn.execute('''
        SELECT id FROM notes 
        WHERE course_id = ? AND student_id = ?
    ''', (course_id, student_id)).fetchone()

    if existing_grade:
        # Mettre à jour la note existante
        conn.execute('''
            UPDATE notes 
            SET grade = ?, comments = ? 
            WHERE course_id = ? AND student_id = ?
        ''', (grade, comments, course_id, student_id))
    else:
        # Créer une nouvelle note
        conn.execute('''
            INSERT INTO notes (student_id, course_id, grade, comments) 
            VALUES (?, ?, ?, ?)
        ''', (student_id, course_id, grade, comments))

    conn.commit()
    conn.close()

    flash('Note enregistrée avec succès', 'success')
    return redirect(url_for('view_course_grades', course_id=course_id))

if __name__ == '__main__':
    app.run(debug=True)