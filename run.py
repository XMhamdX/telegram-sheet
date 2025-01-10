import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import os

# إعداد التسجيل
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

class BotRunner:
    def __init__(self):
        self.process = None
        self.restart_bot()

    def restart_bot(self):
        # إيقاف العملية القديمة إذا كانت موجودة
        if self.process:
            self.process.terminate()
            self.process.wait()

        # بدء عملية جديدة
        logging.info("جاري تشغيل البوت...")
        self.process = subprocess.Popen([sys.executable, 'main.py'])

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, bot_runner):
        self.bot_runner = bot_runner
        self.last_modified = time.time()
        self.cooldown = 2  # ثانيتين للتأخير بين إعادة التشغيل

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            current_time = time.time()
            if current_time - self.last_modified > self.cooldown:
                self.last_modified = current_time
                logging.info(f"تم اكتشاف تغيير في {event.src_path}")
                self.bot_runner.restart_bot()

def main():
    bot_runner = BotRunner()
    event_handler = ChangeHandler(bot_runner)
    observer = Observer()
    
    # مراقبة المجلد الحالي
    path = os.path.dirname(os.path.abspath(__file__))
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    logging.info("بدأت مراقبة التغييرات في الملفات...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if bot_runner.process:
            bot_runner.process.terminate()
        logging.info("تم إيقاف البوت والمراقبة")
    
    observer.join()

if __name__ == "__main__":
    main()
