import os

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '154.61.74.229'),
    'user': os.environ.get('DB_USER', 'remote_user2'),
    'password': os.environ.get('DB_PASSWORD', 'Cadabraa2024'),
    'database': os.environ.get('DB_NAME', 'tenderalert'),
    'cursorclass': __import__('pymysql').cursors.DictCursor,
}


'''
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'admin'),
    'database': os.environ.get('DB_NAME', 'tenderalert'),
    'cursorclass': __import__('pymysql').cursors.DictCursor,
}
'''