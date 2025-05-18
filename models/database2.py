import psycopg2
from psycopg2 import sql
import bcrypt
from configparser import ConfigParser

class Database:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        try:
            config = ConfigParser()
            config.read('database.ini')
            
            self.conn = psycopg2.connect(
                host=config.get('postgresql', 'host'),
                database=config.get('postgresql', 'database'),
                user=config.get('postgresql', 'user'),
                password=config.get('postgresql', 'password'),
                port=config.get('postgresql', 'port')
            )
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            raise

    def execute_query(self, query, params=None):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    return cursor.fetchall()
                self.conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Database error: {e}")
            self.conn.rollback()
            return False

    def close(self):
        if self.conn:
            self.conn.close()

class UserModel(Database):
    def verify_user(self, username, password):
        query = sql.SQL("""
            SELECT user_id, password_hash, postgres_role, role_id 
            FROM users 
            WHERE username = %s AND is_active = TRUE
        """)
        result = self.execute_query(query, (username,))
        
        if result and bcrypt.checkpw(password.encode('utf-8'), result[0][1].encode('utf-8')):
            return {
                'user_id': result[0][0],
                'role': result[0][2],
                'role_id': result[0][3]
            }
        return None

    def get_user_permissions(self, role_id):
        query = sql.SQL("""
            SELECT p.permission_name 
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.permission_id
            WHERE rp.role_id = %s
        """)
        result = self.execute_query(query, (role_id,))
        return [row[0] for row in result] if result else []