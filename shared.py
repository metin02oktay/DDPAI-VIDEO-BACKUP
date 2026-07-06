from queue import Queue
from database_video import DatabaseManager
from config import DB_NAME

db = DatabaseManager(DB_NAME)

q_download: Queue = Queue()
q_upload: Queue = Queue()