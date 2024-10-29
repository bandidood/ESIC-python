import sqlite3
from werkzeug.security import generate_password_hash
import datetime

try:
    # Création de la connexion à la base de données
    connection = sqlite3.connect("db_school.db")
    cursor = connection.cursor()
    print("✅ Connexion à la base de données réussie")

    # Création de la table users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
    ''')
    print("✅ Table 'users' créée avec succès")

    # Création de la table courses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            teacher_id INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        )
    ''')
    print("✅ Table 'courses' créée avec succès")

    # Création de la table notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            grade REAL,
            comments TEXT,
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    print("✅ Table 'notes' créée avec succès")

    # Définition des privilèges pour chaque rôle
    role_privileges = {
        'étudiant': ['view_courses', 'view_notes'],
        'enseignant': ['view_courses', 'edit_courses', 'view_notes', 'edit_notes'],
        'directeur': ['view_users', 'edit_users', 'delete_users', 'add_users']
    }
    print("✅ Privilèges des rôles définis avec succès")

    # Vérification si des utilisateurs existent déjà
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        # Liste des utilisateurs à ajouter
        users_to_add = [
            # Directeurs (2)
            ("directeur1", "directeur1@school.com", "Dir123456", "directeur"),
            ("directeur2", "directeur2@school.com", "Dir123456", "directeur"),

            # Enseignants (5)
            ("prof_math", "prof.math@school.com", "Prof123456", "enseignant"),
            ("prof_francais", "prof.francais@school.com", "Prof123456", "enseignant"),
            ("prof_histoire", "prof.histoire@school.com", "Prof123456", "enseignant"),
            ("prof_science", "prof.science@school.com", "Prof123456", "enseignant"),
            ("prof_sport", "prof.sport@school.com", "Prof123456", "enseignant"),

            # Étudiants (8)
            ("etudiant1", "etudiant1@school.com", "Etu123456", "étudiant"),
            ("etudiant2", "etudiant2@school.com", "Etu123456", "étudiant"),
            ("etudiant3", "etudiant3@school.com", "Etu123456", "étudiant"),
            ("etudiant4", "etudiant4@school.com", "Etu123456", "étudiant"),
            ("etudiant5", "etudiant5@school.com", "Etu123456", "étudiant"),
            ("etudiant6", "etudiant6@school.com", "Etu123456", "étudiant"),
            ("etudiant7", "etudiant7@school.com", "Etu123456", "étudiant"),
            ("etudiant8", "etudiant8@school.com", "Etu123456", "étudiant")
        ]

        # Insertion des utilisateurs
        for username, email, password, role in users_to_add:
            try:
                cursor.execute("""
                    INSERT INTO users (username, email, password, role)
                    VALUES (?, ?, ?, ?)
                """, (username, email, generate_password_hash(password), role))
                print(f"✅ Utilisateur {username} ajouté avec succès")
            except sqlite3.IntegrityError as e:
                print(f"⚠️ Impossible d'ajouter l'utilisateur {username}: {e}")

        print(f"✅ {len(users_to_add)} utilisateurs ajoutés avec succès")
    else:
        print("ℹ️ Des utilisateurs existent déjà dans la base de données. Aucun ajout effectué.")

    # Validation des changements
    connection.commit()
    print("✅ Changements commités avec succès")

    # Vérification de la création des tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n📋 Tables présentes dans la base de données:")
    for table in tables:
        print(f"   - {table[0]}")

    # Affichage du nombre d'utilisateurs par rôle
    cursor.execute("""
        SELECT role, COUNT(*) as count 
        FROM users 
        GROUP BY role
    """)
    user_stats = cursor.fetchall()
    print("\n📊 Statistiques des utilisateurs par rôle:")
    for role, count in user_stats:
        print(f"   - {role}: {count} utilisateur(s)")

except sqlite3.Error as e:
    print(f"❌ Erreur lors de la création de la base de données: {e}")

finally:
    # Fermeture de la connexion
    if connection:
        connection.close()
        print("\n✅ Connexion à la base de données fermée")